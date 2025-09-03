"""Helper functions for reading subtitles and extracting text from media files.

This module contains utility functions for reading the contents of
subtitle or text files associated with videos. If no subtitle is
available, it can extract the audio track from the video and send it to
the Google AI Studio Generative Language API to obtain a transcript.
"""

from __future__ import annotations

import logging
import os
import tempfile


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
            audio_bytes = audio_file.read()
        os.unlink(tmp_path)

        try:
            from google import genai
            from google.genai import types
        except Exception as exc:  # pragma: no cover - handled at runtime
            raise RuntimeError("google-genai library is required") from exc

        client = genai.Client(api_key=api_key)
        audio_part = types.Part.from_bytes(audio_bytes, mime_type="audio/mp3")
        prompt_part = types.Part.from_text("Transcribe the provided audio.")

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[types.Content(role="user", parts=[prompt_part, audio_part])],
        )
        result = response.text.strip()
        logging.debug("Transcription obtained with length %d", len(result))
        return result
    except Exception as exc:  # pragma: no cover - network and other errors
        message = str(exc).lower()
        if "api key" in message and "invalid" in message:
            raise PermissionError("Invalid API key for transcription") from exc
        logging.error("Audio extraction/transcription failed for '%s': %s", video_path, exc)
        return ""
