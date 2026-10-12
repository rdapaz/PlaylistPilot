from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from gui.theme import CARD_STYLE, NAVY, TEXT_SECONDARY


class StatCard(QFrame):
    def __init__(self, label: str, value: str = "0", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(CARD_STYLE)
        self.setMinimumHeight(96)
        self.setMinimumWidth(150)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.addStretch()
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {NAVY}; font-size: 28px; font-weight: 600;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(self.value_label)
        self.text_label = QLabel(label)
        self.text_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        lay.addWidget(self.text_label)
        lay.addStretch()

    def set_value(self, value) -> None:
        self.value_label.setText(f"{value:,}" if isinstance(value, int) else str(value))
