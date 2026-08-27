"""Punto de entrada de la aplicación."""
import customtkinter as ctk

from db.init_db import initialize_database
from ui.app import App


def main():
    initialize_database()
    ctk.set_appearance_mode("light")
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
