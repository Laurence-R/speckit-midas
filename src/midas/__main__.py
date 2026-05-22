"""Entry point for 'python -m midas' and PyInstaller."""
from __future__ import annotations

import sys


def main() -> None:
    """Bootstrap the Midas application."""
    import customtkinter as ctk
    from midas.app import App

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
