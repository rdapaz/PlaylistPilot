"""Main window: navy sidebar with four views, status label, Ctrl+1..4, geometry persistence."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from core import settings
from gui.state import AppState
from gui.theme import NAVY, NEGATIVE, POSITIVE, TEXT_SECONDARY
from gui.views.device import DeviceView
from gui.views.library import LibraryView
from gui.views.playlists import PlaylistsView
from gui.views.settings import SettingsView
from gui.views.soundiiz import SoundiizView


class NavButton(QPushButton):
    def __init__(self, icon_char: str, text: str, parent=None):
        super().__init__(f"  {icon_char}  {text}", parent)
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton { background-color: transparent; color: #A0AEC0; border: none; border-radius: 8px;
                          text-align: left; padding-left: 16px; font-size: 11pt; font-family: 'Segoe UI'; }
            QPushButton:hover { background-color: rgba(255,255,255,0.08); color: white; }
            QPushButton:checked { background-color: rgba(255,255,255,0.12); color: white; font-weight: 600; }
        """)


class MainWindow(QMainWindow):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.setWindowTitle("PlaylistPilot")
        self.resize(1240, 820)
        central = QWidget(); self.setCentralWidget(central)
        root = QHBoxLayout(central); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        sidebar = QFrame(); sidebar.setFixedWidth(220); sidebar.setStyleSheet(f"background-color: {NAVY};")
        sl = QVBoxLayout(sidebar); sl.setContentsMargins(12, 20, 12, 16); sl.setSpacing(6)
        title = QLabel("PlaylistPilot"); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: white; font-size: 16pt; font-weight: 600; font-family: 'Segoe UI'; margin-bottom: 12px;")
        sl.addWidget(title)
        self.views = [
            ("\U0001F3A7", "Device", DeviceView(state)),
            ("\U0001F4DA", "Library", LibraryView(state)),
            ("\U0001F3B5", "Playlists", PlaylistsView(state)),
            ("\U0001F504", "Soundiiz", SoundiizView(state)),
            ("⚙️", "Settings", SettingsView(state)),
        ]
        self.stack = QStackedWidget()
        self.nav_buttons = []
        for i, (icon, name, view) in enumerate(self.views):
            btn = NavButton(icon, name)
            btn.clicked.connect(lambda checked, idx=i: self._navigate_to(idx))
            sl.addWidget(btn); self.nav_buttons.append(btn)
            self.stack.addWidget(view)
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self).activated.connect(lambda idx=i: self._navigate_to(idx))
        sl.addStretch()
        self.device_label = QLabel(""); self.device_label.setStyleSheet("color: #A0AEC0; font-size: 9pt;")
        self.device_label.setWordWrap(True)
        self.connection_label = QLabel("not connected"); self.connection_label.setStyleSheet("color: #F87171; font-size: 9pt;")
        self.connection_label.setWordWrap(True)
        sl.addWidget(self.device_label); sl.addWidget(self.connection_label)
        root.addWidget(sidebar); root.addWidget(self.stack, stretch=1)

        state.connection_changed.connect(self._conn)
        state.device_changed.connect(self._dev)
        self._dev(); self._navigate_to(0)
        geo = settings.qs().value("geometry")
        if geo:
            self.restoreGeometry(geo)

    def _navigate_to(self, idx: int):
        for i, b in enumerate(self.nav_buttons):
            b.setChecked(i == idx)
        self.stack.setCurrentIndex(idx)
        self.views[idx][2].refresh()

    def _conn(self, ok: bool, detail: str):
        self.connection_label.setText(detail if len(detail) < 60 else detail[:57] + "...")
        # lighter tints than POSITIVE/NEGATIVE so they read on the navy sidebar
        self.connection_label.setStyleSheet(f"color: {'#4ADE80' if ok else '#F87171'}; font-size: 9pt;")

    def _dev(self):
        p = self.state.profile
        self.device_label.setText(f"Device: {p.name}" if p else "")

    def closeEvent(self, event):
        settings.qs().setValue("geometry", self.saveGeometry())
        super().closeEvent(event)
