from collections.abc import Callable
from typing import Any

from PySide6 import QtCore
from PySide6.QtCore import (
    QAbstractTableModel,
    QItemSelection,
    QModelIndex,
    QPersistentModelIndex,
    QRect,
    QSize,
    Qt,
)
from PySide6.QtGui import QAction, QCursor, QIcon, QKeyEvent, QPainter, QPixmap, QTextDocument
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialogButtonBox,
    QItemDelegate,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QStyleOptionViewItem,
    QTableView,
    QTextEdit,
    QWidget,
)
from pytide6 import Dialog, HBoxPanel, PushButton, VBoxLayout, VBoxPanel, W
from pytide6.inputs import LineEdit

from i2cc.app import App


class Txt2HTMLDelegate(QItemDelegate):
    def __init__(self) -> None:
        super().__init__()

    def mk_text_document(self, text: str) -> QTextDocument:
        document = QTextDocument()
        document.setHtml(text)
        document.setDocumentMargin(1)
        return document

    def drawDisplay(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        rect: QRect,
        text: str,
        /,
    ) -> None:
        document = self.mk_text_document(text)
        painter.save()
        painter.translate(rect.topLeft())
        document.drawContents(painter)
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex) -> QSize:
        data = index.data(Qt.ItemDataRole.DisplayRole)
        return self.mk_text_document(data).size().toSize()


class TableModelWithFilterAction(QAbstractTableModel):
    def apply_filter(self, filter_text: str, post_filter_action: Callable[[], Any]):
        pass


class ListTableView[T: TableModelWithFilterAction](QTableView):
    def __init__(
        self,
        table_model: T,
        pass_key_press_event: Callable[[], Callable[[QKeyEvent], None]] | None,
        on_double_clicked: Callable[[QModelIndex], None] | None,
        hide_horizontal_header: bool = False,
        on_selection_change: Callable[[QtCore.QItemSelection], None] = lambda _: None,
    ):
        super().__init__(None)
        self.pass_key_press_event = pass_key_press_event
        self.on_selection_change = on_selection_change
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.horizontalHeader().setStretchLastSection(True)
        if hide_horizontal_header:
            self.horizontalHeader().hide()
        self.select_chars = []
        self.table_model = table_model
        self.setModel(self.table_model)
        self.setItemDelegate(Txt2HTMLDelegate())

        if on_double_clicked is not None:
            self.doubleClicked.connect(on_double_clicked)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.pass_key_press_event is None:
            super().keyPressEvent(event)
        else:
            self.pass_key_press_event()(event)

    def selectionChanged(self, selected: QtCore.QItemSelection, deselected: QtCore.QItemSelection, /) -> None:
        super().selectionChanged(selected, deselected)
        self.on_selection_change(selected)


class InTableSearchField[T: TableModelWithFilterAction](LineEdit):
    def __init__(
        self,
        table_view: ListTableView[T],
        on_key_enter: Callable[[QModelIndex], None],
        close_action: Callable[[], Any],
    ):
        super().__init__()
        self.table_view = table_view
        self.on_key_enter = on_key_enter
        self.close_action = close_action

        # place "find" icon on the left side of search text field.
        self.addAction(
            QIcon.fromTheme(QIcon.ThemeIcon.EditFind),
            QLineEdit.ActionPosition.LeadingPosition,
        )

        def post_filter_action():
            if table_view.table_model.rowCount() == 0:
                # this will trigger selection change event when there are no more items in a list
                # without this code no such event is emitted on its own
                table_view.selectionModel().selectionChanged.emit(QItemSelection(), QItemSelection())
            else:
                table_view.selectRow(0)

        self.textChanged.connect(lambda text: table_view.table_model.apply_filter(text, post_filter_action))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        event_key = event.key()
        match event_key:
            case Qt.Key.Key_Escape:
                if self.text() == "":
                    self.close_action()
                else:
                    self.setText("")
                    return

            case Qt.Key.Key_Return:
                selected_rows = self.table_view.selectedIndexes()
                self.close_action()
                if selected_rows != []:
                    self.on_key_enter(selected_rows[0])
                return

            case Qt.Key.Key_Down:
                selected_rows = self.table_view.selectedIndexes()
                if selected_rows == []:
                    self.table_view.selectRow(0)
                else:
                    next_row = selected_rows[0].row() + 1
                    if next_row <= self.table_view.table_model.rowCount():
                        self.table_view.selectRow(next_row)
                return

            case Qt.Key.Key_Up:
                selected_rows = self.table_view.selectedIndexes()
                if selected_rows == []:
                    self.table_view.selectRow(0)
                else:
                    next_row = selected_rows[0].row() - 1
                    if next_row >= 0:
                        self.table_view.selectRow(next_row)
                return

        super().keyPressEvent(event)


class TableModelWithOneColumn:
    def columnCount(self, /, parent: QModelIndex | QPersistentModelIndex = ...) -> int:
        return 1


class TableModelWithTwoColumns:
    def columnCount(self, /, parent: QModelIndex | QPersistentModelIndex = ...) -> int:
        return 2


class TableModelWithThreeColumns:
    def columnCount(self, /, parent: QModelIndex | QPersistentModelIndex = ...) -> int:
        return 3


class TableModelWithoutHeader:
    def headerData(self, section, orientation, /, role=...) -> Any:
        return None


class TableModelAllSelectableAndEnabled:
    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled


def apply_filter_to_text(char_filter: list[str], text: str) -> str | None:
    j = 0
    new_text = ""
    char_filter = [c.lower() for c in char_filter]
    num_chars_in_filter = len(char_filter)
    for i in range(len(text)):
        if j < num_chars_in_filter and char_filter[j] == text[i].lower():
            j += 1
            new_text += f'<span style="background-color: pink; color: #000000;">{text[i]}</span>'
        else:
            new_text += text[i]

    return new_text if j == num_chars_in_filter else None


class XButton(PushButton):
    def __init__(
        self,
        text: str,
        parent: QWidget | None = None,
        *,
        on_clicked: Callable[[], Any] | None = None,
        auto_default: bool | None = None,
        cursor: QCursor | Qt.CursorShape | QPixmap | None = None,
        enabled: bool = True,
        tool_tip: str | None = None,
        respond_to_enter_and_return_keys: bool = True,
    ):
        super().__init__(
            text,
            parent,
            on_clicked=on_clicked,
            auto_default=auto_default,
            style_sheet=App.css.PushButton,
            cursor=cursor,
            enabled=enabled,
            tool_tip=tool_tip,
            respond_to_enter_and_return_keys=respond_to_enter_and_return_keys,
        )


class ModalMessageDialog(Dialog):
    def __init__(self, parent, *, message: str, windowTitle: str, icon: QIcon.ThemeIcon | None, buttons: list[XButton]):
        super().__init__(parent, windowTitle=windowTitle, modal=True, css=App.css.ErrorDialog)

        msg_widgets = []
        if icon is not None:
            icon_label = QLabel()
            icon_label.setPixmap(QIcon.fromTheme(icon).pixmap(QSize(52, 52)))
            msg_widgets.append(VBoxPanel([icon_label, W(stretch=1)], margins=0))
        text_edit = QTextEdit(message)
        text_edit.setReadOnly(True)

        min_width = text_edit.fontMetrics().horizontalAdvance(message + "  ")
        max_width = text_edit.fontMetrics().horizontalAdvance("_" * 100)
        text_edit.setMinimumWidth(min(min_width, max_width))
        text_edit.setMaximumWidth(max_width)

        msg_widgets.append(text_edit)
        self.setLayout(
            VBoxLayout(
                [
                    HBoxPanel(msg_widgets),
                    # W(stretch=1),
                    HBoxPanel([W(stretch=1)] + buttons),
                ]
            )
        )

    @staticmethod
    def error(parent, message: Any):
        dialog = []

        def close():
            dialog[0].close()

        message_dialog = ModalMessageDialog(
            parent,
            message=str(message),
            windowTitle="Error",
            icon=QIcon.ThemeIcon.DialogError,
            buttons=[XButton("Ok", on_clicked=close)],
        )
        dialog.append(message_dialog)
        message_dialog.exec()

    @staticmethod
    def information(parent, message: Any):
        dialog = []

        def close():
            dialog[0].close()

        message_dialog = ModalMessageDialog(
            parent,
            message=str(message),
            windowTitle="Info",
            icon=QIcon.ThemeIcon.DialogInformation,
            buttons=[XButton("Ok", on_clicked=close)],
        )
        dialog.append(message_dialog)
        message_dialog.exec()

    @staticmethod
    def about(parent, message: Any):
        dialog = []

        def close():
            dialog[0].close()

        message_dialog = ModalMessageDialog(
            parent, message=str(message), windowTitle="About", icon=None, buttons=[XButton("Ok", on_clicked=close)]
        )
        dialog.append(message_dialog)
        message_dialog.exec()

    @staticmethod
    def question(parent, title: str, message: Any) -> QDialogButtonBox.StandardButton:
        dialog = []
        retval = [QMessageBox.StandardButton.No]

        def yes():
            retval.clear()
            retval.append(QMessageBox.StandardButton.Yes)
            dialog[0].close()

        def no():
            dialog[0].close()

        message_dialog = ModalMessageDialog(
            parent,
            message=str(message),
            windowTitle=title,
            icon=QIcon.ThemeIcon.DialogQuestion,
            buttons=[XButton("Yes", on_clicked=yes), XButton("No", on_clicked=no)],
        )
        dialog.append(message_dialog)
        message_dialog.exec()
        return retval[0]


class ReactiveActionLabelWithMenu(QLabel):
    def __init__(self, text="⋮⋮"):
        super().__init__(text)
        "⬔"
        self.setStyleSheet(App.css.ReactiveActionLabel)

        self.menu = QMenu(self)

    def addMenuAction(self, action_text: str) -> QAction:
        action = QAction(action_text, self)
        self.menu.addAction(action)
        return action

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.menu.exec(event.globalPosition().toPoint())
        super().mousePressEvent(event)
