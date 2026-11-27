"""Мелкие переиспользуемые виджеты и сервис диалогов."""
from tkinter import filedialog, messagebox, ttk


class Dialogs:
    """Интерфейс диалогов, позволяющий подменять их в интеграционных тестах."""

    @staticmethod
    def open_file(title, filetypes):
        return filedialog.askopenfilename(title=title, filetypes=filetypes)

    @staticmethod
    def open_files(title, filetypes):
        return filedialog.askopenfilenames(title=title, filetypes=filetypes)

    @staticmethod
    def save_file(title, initialfile, filetypes=(
            ("PNG", "*.png"), ("JPEG", "*.jpg"), ("TIFF", "*.tif"))):
        return filedialog.asksaveasfilename(
            title=title, initialfile=initialfile, filetypes=filetypes)

    @staticmethod
    def error(parent, message):
        messagebox.showerror("Ошибка", message, parent=parent)


def named_button(parent, text, action, side="left"):
    button = ttk.Button(parent, text=text, command=action)
    button.pack(side=side, padx=3, pady=4)
    return button
