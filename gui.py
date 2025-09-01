"""Graphical user interface for the AI Video Course Analyzer.

This module defines a `VideoAnalyzerApp` class that builds a simple
Tkinter interface. Users can enter high‑level instructions for the AI,
select a local directory containing video course materials, provide
optional extra prompts, input one or more API keys, and initiate the
analysis process. Progress messages are displayed in a scrolling log
area. The actual scanning of directories and calls to the AI service
take place in a background thread to keep the GUI responsive.
"""

from __future__ import annotations

import os
import threading
from typing import List

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import scrolledtext

try:  # Support running as a script or module
    from .directory_scanner import scan_course_folder
    from .file_processor import read_text_file, extract_audio_and_transcribe
    from .api_handler import ApiManager, call_api
except ImportError:  # pragma: no cover - fallback for direct execution
    from directory_scanner import scan_course_folder
    from file_processor import read_text_file, extract_audio_and_transcribe
    from api_handler import ApiManager, call_api


class VideoAnalyzerApp:
    """Main application class for the AI Video Course Analyzer GUI."""

    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        master.geometry("800x600")

        # Variables to hold user input
        self.system_instruction = tk.StringVar()
        self.course_path = tk.StringVar()
        self.extra_prompt = tk.StringVar()
        self.api_keys_text = tk.StringVar()

        # Flag to prevent multiple analyses running simultaneously
        self.analysis_in_progress = False

        # Build the UI
        self._build_interface()

    def _build_interface(self) -> None:
        """Constructs the GUI elements."""
        row = 0
        # System instruction label and text box
        tk.Label(self.master, text="System Instruction / Hướng dẫn hệ thống:").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        row += 1
        self.system_instruction_text = scrolledtext.ScrolledText(self.master, width=90, height=6)
        self.system_instruction_text.grid(row=row, column=0, columnspan=3, sticky='we', padx=5)
        row += 1

        # Course folder selection
        tk.Label(self.master, text="Thư mục khóa học:").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        tk.Entry(self.master, textvariable=self.course_path, width=60).grid(row=row, column=1, sticky='we', padx=5)
        tk.Button(self.master, text="Chọn...", command=self.choose_folder).grid(row=row, column=2, sticky='w', padx=5)
        row += 1

        # Extra prompt
        tk.Label(self.master, text="Prompt bổ sung (tùy chọn):").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        tk.Entry(self.master, textvariable=self.extra_prompt, width=60).grid(row=row, column=1, columnspan=2, sticky='we', padx=5)
        row += 1

        # API keys input
        tk.Label(self.master, text="API Keys (mỗi dòng một key):").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        row += 1
        self.api_keys_textbox = scrolledtext.ScrolledText(self.master, width=60, height=4)
        self.api_keys_textbox.grid(row=row, column=0, columnspan=3, sticky='we', padx=5)
        row += 1

        # Start button
        self.start_button = tk.Button(self.master, text="Bắt đầu phân tích", command=self.start_analysis)
        self.start_button.grid(row=row, column=0, pady=10, padx=5, sticky='w')
        row += 1

        # Log area
        tk.Label(self.master, text="Log tiến trình:").grid(row=row, column=0, sticky='w', padx=5)
        row += 1
        self.log_text = scrolledtext.ScrolledText(self.master, width=90, height=15, state='disabled')
        self.log_text.grid(row=row, column=0, columnspan=3, sticky='we', padx=5, pady=(0, 5))

        # Make columns expand with window resizing
        self.master.columnconfigure(1, weight=1)

    def choose_folder(self) -> None:
        """Open a dialog for the user to pick a course directory."""
        selected = filedialog.askdirectory(title="Chọn thư mục khóa học")
        if selected:
            self.course_path.set(selected)

    def _log(self, message: str) -> None:
        """Append a message to the log text box in a thread‑safe manner."""
        def append():
            self.log_text.configure(state='normal')
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state='disabled')
        self.master.after(0, append)

    def start_analysis(self) -> None:
        """Validate user inputs and start the analysis in a new thread."""
        if self.analysis_in_progress:
            messagebox.showinfo("Thông báo", "Đang phân tích, vui lòng chờ hoàn thành trước khi bắt đầu phiên mới.")
            return

        system_instruction = self.system_instruction_text.get("1.0", tk.END).strip()
        course_path = self.course_path.get().strip()
        extra_prompt = self.extra_prompt.get().strip()
        api_keys_input = self.api_keys_textbox.get("1.0", tk.END).strip()
        api_keys = [key.strip() for key in api_keys_input.splitlines() if key.strip()]

        if not system_instruction:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập System Instruction để mô tả cách AI cần phân tích video.")
            return
        if not course_path or not os.path.isdir(course_path):
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn thư mục khóa học hợp lệ.")
            return
        if not api_keys:
            messagebox.showwarning("Thiếu API key", "Vui lòng nhập ít nhất một API key.")
            return

        # Clear previous logs
        self.log_text.configure(state='normal')
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state='disabled')

        # Disable start button while processing
        self.start_button.configure(state='disabled')
        self.analysis_in_progress = True

        # Start background thread
        thread = threading.Thread(
            target=self.process_course,
            args=(system_instruction, course_path, extra_prompt, api_keys),
            daemon=True,
        )
        thread.start()

    def process_course(self, system_instruction: str, course_path: str, extra_prompt: str, api_keys: List[str]) -> None:
        """Perform the directory scan and call the AI service for each video.

        This runs in a separate thread to keep the GUI responsive. Results
        are written to a `study_guide.txt` file in the same directory
        where this script is executed. Log messages are sent back to the
        GUI thread using `_log`.
        """
        try:
            self._log(f"Bắt đầu quét thư mục: {course_path}")
            try:
                course_structure = scan_course_folder(course_path)
            except Exception as e:
                self._log(f"Lỗi khi quét thư mục: {e}")
                return

            if not course_structure:
                self._log("Không tìm thấy video nào trong thư mục đã chọn.")
                return

            # Prepare API manager
            api_manager = ApiManager(api_keys)

            # Prepare output file
            output_path = os.path.join(os.getcwd(), "study_guide.txt")
            self._log(f"Kết quả sẽ được ghi vào: {output_path}")

            token_limit_videos: List[str] = []

            with open(output_path, "w", encoding="utf-8") as out_file:
                for folder_name, videos in course_structure.items():
                    out_file.write(f"# {folder_name}\n")
                    for entry in videos:
                        video_path = entry["video"]
                        subtitle_path = entry["subtitle"]
                        text_path = entry["text"]

                        self._log(f"Phân tích video: {os.path.basename(video_path)}")
                        # Collect text content
                        content_parts: List[str] = []
                        if subtitle_path:
                            content_parts.append(read_text_file(subtitle_path))
                        if text_path and text_path != subtitle_path:
                            content_parts.append(read_text_file(text_path))
                        if not content_parts:
                            # Fall back to audio transcription stub
                            content_parts.append(extract_audio_and_transcribe(video_path))
                        combined_content = "\n".join(content_parts)

                        # Compose prompt
                        prompt = f"{system_instruction}\n\nNội dung video:\n{combined_content}".strip()
                        if extra_prompt:
                            prompt += f"\n\n{extra_prompt}"

                        # Get an API key
                        key = api_manager.get_active_key()
                        if not key:
                            self._log("Hết API key hoạt động. Dừng phân tích.")
                            return
                        try:
                            response = call_api(prompt, key)
                            # Check for token limit marker in response; this is heuristic
                            if isinstance(response, str) and "TOKEN_LIMIT" in response:
                                token_limit_videos.append(os.path.basename(video_path))
                                self._log(f"Video vượt quá giới hạn token: {video_path}")
                            else:
                                out_file.write(f"\n## {os.path.basename(video_path)}\n")
                                out_file.write(response.strip() + "\n")
                        except Exception as exc:
                            # If an API error occurs, disable current key and retry once
                            self._log(f"Lỗi khi gọi API với khóa {key}: {exc}")
                            api_manager.disable_current_key()
                            continue

            if token_limit_videos:
                self._log("Một số video vượt quá giới hạn token và không được xử lý:")
                for vid in token_limit_videos:
                    self._log(f" - {vid}")

            self._log("Hoàn thành phân tích toàn bộ thư mục!")
        finally:
            # Re-enable start button regardless of outcome
            self.analysis_in_progress = False
            self.master.after(0, lambda: self.start_button.configure(state='normal'))
