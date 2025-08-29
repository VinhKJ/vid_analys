"""Functions for scanning course directories to find video and text files.

This module provides a utility to recursively scan a selected root
directory and build a structured representation of all course folders and
their media files. Each course folder may contain multiple videos, and
each video can have an associated subtitle or text file if a file with
the same base name exists but with a different extension (e.g. ``.srt``,
``.vtt``, or ``.txt``).

Usage example:

>>> from video_analyzer.directory_scanner import scan_course_folder
>>> structure = scan_course_folder('/path/to/course')
>>> print(structure)
{'Lesson 1': [
    {'video': '/path/to/course/Lesson 1/intro.mp4',
     'subtitle': '/path/to/course/Lesson 1/intro.srt',
     'text': None}
 ]}
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional


def _find_associated_text_files(folder: str, base_name: str) -> Dict[str, Optional[str]]:
    """Return a dictionary mapping keys 'subtitle' and 'text' to matching files.

    Parameters
    ----------
    folder: str
        The directory in which to search for associated files.
    base_name: str
        The filename without extension of the video (e.g. 'lesson1').

    Returns
    -------
    dict
        A mapping with keys ``'subtitle'`` and ``'text'`` whose values
        are the full paths to the corresponding files if found, or
        ``None`` otherwise.
    """
    subtitle_extensions = [".srt", ".vtt"]
    text_extensions = [".txt"]
    subtitle_path: Optional[str] = None
    text_path: Optional[str] = None

    # Look for subtitle files
    for ext in subtitle_extensions:
        candidate = os.path.join(folder, base_name + ext)
        if os.path.isfile(candidate):
            subtitle_path = candidate
            break

    # Look for text file if not already set; note .txt takes precedence
    for ext in text_extensions:
        candidate = os.path.join(folder, base_name + ext)
        if os.path.isfile(candidate):
            text_path = candidate
            break

    return {"subtitle": subtitle_path, "text": text_path}


def scan_course_folder(root_path: str) -> Dict[str, List[Dict[str, Optional[str]]]]:
    """Recursively scan a course directory to map videos to their associated files.

    Given a root directory, this function walks through all first-level
    subdirectories (representing individual course modules or chapters).
    Within each subdirectory it looks for files ending in ``.mp4`` (case
    insensitive). For each video found, it searches for an accompanying
    subtitle (``.srt`` or ``.vtt``) or text (``.txt``) file with the same
    basename. The results are returned as a dictionary keyed by the
    subdirectory name. Each value is a list of dictionaries containing
    absolute paths for the video and its associated files.

    Parameters
    ----------
    root_path: str
        The full path to the root course folder chosen by the user.

    Returns
    -------
    dict
        A nested mapping from folder names to lists of file records. Each
        record dictionary contains keys ``'video'``, ``'subtitle'``, and
        ``'text'``.
    """
    course_structure: Dict[str, List[Dict[str, Optional[str]]]] = {}

    if not os.path.isdir(root_path):
        raise FileNotFoundError(f"The provided path '{root_path}' is not a directory")

    # Iterate over the immediate children of the root directory
    for entry in sorted(os.listdir(root_path)):
        subdir_path = os.path.join(root_path, entry)
        if os.path.isdir(subdir_path):
            # Gather video files within this subdirectory
            videos: List[Dict[str, Optional[str]]] = []
            for filename in sorted(os.listdir(subdir_path)):
                if filename.lower().endswith(".mp4"):
                    base_name = os.path.splitext(filename)[0]
                    video_path = os.path.join(subdir_path, filename)
                    associated = _find_associated_text_files(subdir_path, base_name)
                    videos.append({
                        "video": video_path,
                        "subtitle": associated["subtitle"],
                        "text": associated["text"],
                    })
            if videos:
                course_structure[entry] = videos

    return course_structure
