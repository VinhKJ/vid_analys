"""Helper functions for reading subtitles and extracting text from media files.

This module contains utility functions for reading the contents of
subtitle or text files associated with videos. If no subtitle is
available, it can extract the audio track from the video and send it to
the Google AI Studio Generative Language API to obtain a transcript.
"""

from __future__ import annotations

import base64
import logging
import os
import tempfile

import requests  # type: ignore


def read_text_file(file_path: str) -> str:
    """Read and return the contents of a subtitle or text file.

    Parameters
    ----------
    file_path: str
        The full path to the .srt, .vtt or .txt file.

    Returns
    -------
    str
        The file's contents as a UTF‑8 string. If reading fails, an
        empty string is returned and an error is logged.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        logging.debug("Read %d characters from '%s'", len(content), file_path)
        return content
    except Exception as e:
        logging.error("Failed to read file '%s': %s", file_path, e)
        return ""


def extract_audio_and_transcribe(video_path: str, api_key: str) -> str:
    """Extract audio from a video file and transcribe it using Gemini.

    Parameters
    ----------
    video_path: str
        The full path to the ``.mp4`` file.
    api_key: str
        API key used to authenticate with the transcription service.

    Returns
    -------
    str
        The transcribed text. If an error occurs during extraction or
        transcription, an empty string is returned.
    """

    logging.info("Extracting and transcribing audio for '%s'", video_path)
    try:
        from moviepy import VideoFileClip  # Local import to avoid heavy dependency when unused

        with VideoFileClip(video_path) as clip:
            if clip.audio is None:
                logging.warning("No audio track found in '%s'", video_path)
                return ""
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
                clip.audio.write_audiofile(tmp_path, logger=None)

        with open(tmp_path, "rb") as audio_file:
            audio_b64 = base64.b64encode(audio_file.read()).decode("utf-8")
        os.unlink(tmp_path)

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-1.5-flash:generateContent?key=" + api_key
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": "Transcribe the provided audio."},
                        {"inline_data": {"mime_type": "audio/mp3", "data": audio_b64}},
                    ]
                }
            ]
        }

        response = requests.post(url, json=payload, timeout=300)
        if response.status_code in {401, 403}:
            raise PermissionError("Invalid API key for transcription")
        response.raise_for_status()
        result = (
            response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        )
        logging.debug("Transcription obtained with length %d", len(result))
        return result
    except requests.exceptions.RequestException as exc:
        logging.error("Transcription request failed: %s", exc)
    except Exception as exc:  # pragma: no cover - broad catch to log unexpected errors
        logging.error("Audio extraction/transcription failed for '%s': %s", video_path, exc)
    return ""
