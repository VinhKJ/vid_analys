"""Entry point for the AI Video Course Analyzer application.

Running this script will launch a simple Tkinter window that allows
users to specify how they want AI to analyse videos, select a folder
containing course materials, provide API keys, and start the analysis.
"""

from __future__ import annotations

import tkinter as tk

try:  # Allow running as a script or a module
    from .gui import VideoAnalyzerApp
except ImportError:  # pragma: no cover - fallback for direct execution
    from gui import VideoAnalyzerApp


def main() -> None:
    root = tk.Tk()
    root.title("AI Video Course Analyzer")
    # Instantiate the application
    app = VideoAnalyzerApp(root)
    # Start the Tkinter event loop
    root.mainloop()


if __name__ == "__main__":
    main()
