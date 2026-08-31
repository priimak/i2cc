from pytide6 import RichTextLabel

from i2cc.app import App


class OpenedProjectLabel(RichTextLabel):
    message_template = "<em>Project:</em> <b>{}</b>"

    def __init__(self, app: App):
        super().__init__(OpenedProjectLabel.message_template.format(""), css="border: 1px solid black;")
        app.update_project_selector_current_project = self.set_project_name

    def set_project_name(self, project_name: str):
        self.setText(OpenedProjectLabel.message_template.format(project_name))
