from PySide6.QtWidgets import QPlainTextEdit, QTextEdit
from pytide6 import HBoxPanel, PushButton, VBoxPanel, W

from i2cc.app import App


class ProjectNotes(VBoxPanel):
    def __init__(self, app: App):
        super().__init__(background_color="lightyellow", margins=(7, 7, 7, 0))
        self.app = app

        def on_save():
            self.edit_button.setVisible(True)
            self.save_button.setVisible(False)
            self.cancel_button.setVisible(False)
            self.editor.setVisible(False)
            self.viewer.setVisible(True)
            self.app.project.notes = self.editor.toPlainText()
            self.viewer.setMarkdown(self.app.project.notes)
            self.app.project.save_notes()

        self.save_button = PushButton("Save", on_clicked=on_save)
        self.save_button.setVisible(False)

        def on_cancel():
            self.edit_button.setVisible(True)
            self.save_button.setVisible(False)
            self.cancel_button.setVisible(False)
            self.editor.setVisible(False)
            self.viewer.setVisible(True)

        self.cancel_button = PushButton("Cancel", on_clicked=on_cancel)
        self.cancel_button.setVisible(False)

        def on_edit():
            self.edit_button.setVisible(False)
            self.save_button.setVisible(True)
            self.cancel_button.setVisible(True)
            self.editor.setPlainText(app.project.notes)
            self.editor.setVisible(True)
            self.viewer.setVisible(False)

        self.edit_button = PushButton("Edit", on_clicked=on_edit)

        self.editor = QPlainTextEdit()
        self.editor.setVisible(False)
        self.viewer = QTextEdit()
        self.viewer.setMarkdown(app.project.notes)
        self.viewer.setReadOnly(True)

        def notes_reload():
            self.viewer.setMarkdown(app.project.notes)
            self.editor.setPlainText(app.project.notes)

        app.request_notes_reload = notes_reload

        self.withWidgets(
            HBoxPanel(widgets=[W(stretch=1), self.save_button, self.cancel_button, self.edit_button], margins=0),
            W(self.editor, stretch=1),
            W(self.viewer, stretch=1),
        )
