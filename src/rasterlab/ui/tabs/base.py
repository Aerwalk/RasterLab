"""Базовый класс вкладки с общим обработчиком ошибок и кнопками."""
from tkinter import ttk


class Tab(ttk.Frame):
    def __init__(self, parent, app, title):
        super().__init__(parent)
        self.app = app
        self.title = title
        self.app.tabs.add(self, text=title)

    def run(self, action):
        return self.app.guarded(action)

    def button(self, parent, text, action):
        button = ttk.Button(parent, text=text,
                            command=lambda: self.run(action))
        button.pack(side="left", padx=3, pady=4)
        return button
