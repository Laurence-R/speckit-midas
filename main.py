"""Midas — 台股盤後投研桌面應用  Entry point."""
import customtkinter as ctk

from midas.app import App


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
