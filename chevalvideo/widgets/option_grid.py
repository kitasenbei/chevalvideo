"""Clickable option card grid with single or multi select."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class OptionCard(QPushButton):
    """A single selectable card."""

    def __init__(self, value: str, label: str, description: str = "", parent=None):
        super().__init__(parent)
        self.value = value
        self.setCheckable(True)
        self.setProperty("class", "OptionCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        title = QLabel(label)
        title.setStyleSheet("font-weight: bold; background: transparent;")
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(title)

        if description:
            desc = QLabel(description)
            desc.setObjectName("subheading")
            desc.setWordWrap(True)
            desc.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(desc)

        self.setMinimumWidth(100)
        self.setMinimumHeight(50)

    def _update_style(self):
        self.setProperty("selected", "true" if self.isChecked() else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class OptionGrid(QWidget):
    """Grid of selectable option cards."""

    selection_changed = pyqtSignal(list)

    def __init__(self, columns: int = 3, multi: bool = False, parent=None):
        super().__init__(parent)
        self._multi = multi
        self._columns = columns
        self._cards: list[OptionCard] = []
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)

    def set_options(self, options: list[dict]):
        """Set options. Each dict: {value, label, description?}."""
        self._clear()
        for i, opt in enumerate(options):
            card = OptionCard(
                opt["value"], opt["label"], opt.get("description", ""), self
            )
            card.clicked.connect(lambda checked, c=card: self._on_click(c))
            self._cards.append(card)
            self._layout.addWidget(card, i // self._columns, i % self._columns)

    def select(self, value: str):
        """Programmatically select a value."""
        for c in self._cards:
            if c.value == value:
                c.setChecked(True)
                c._update_style()
            elif not self._multi:
                c.setChecked(False)
                c._update_style()

    def selected(self) -> list[str]:
        return [c.value for c in self._cards if c.isChecked()]

    def _on_click(self, card: OptionCard):
        if not self._multi:
            for c in self._cards:
                if c is not card:
                    c.setChecked(False)
                    c._update_style()
        card._update_style()
        self.selection_changed.emit(self.selected())

    def _clear(self):
        for c in self._cards:
            self._layout.removeWidget(c)
            c.deleteLater()
        self._cards.clear()
