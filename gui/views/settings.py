"""Settings view: where local copies go, Claude API key and model, about."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QVBoxLayout, QWidget)

from core import settings
from gui.state import AppState
from gui.theme import (VIEW_STYLE, BG_MAIN, BUTTON_SECONDARY_STYLE, BUTTON_STYLE, CARD_STYLE, COMBO_STYLE, INPUT_STYLE,
                       LABEL_BODY, LABEL_HINT, SECTION_TITLE, SMALL_BTN, font_heading)
from gui.widgets.help_window import make_help_button


class SettingsView(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("view")
        self.setStyleSheet(VIEW_STYLE)
        self._build_ui()

    def _card(self, title: str):
        card = QFrame(); card.setObjectName("card"); card.setStyleSheet(CARD_STYLE)
        lay = QVBoxLayout(card); lay.setContentsMargins(16, 12, 16, 12); lay.setSpacing(10)
        t = QLabel(title); t.setFont(font_heading(14)); t.setStyleSheet(SECTION_TITLE); lay.addWidget(t)
        return card, lay

    def _build_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(24, 24, 24, 24); layout.setSpacing(16)
        header_row = QHBoxLayout()
        header = QLabel("Settings"); header.setFont(font_heading(20)); header.setStyleSheet(SECTION_TITLE)
        header_row.addWidget(header); header_row.addWidget(make_help_button("Settings", self)); header_row.addStretch()
        layout.addLayout(header_row)

        card, cl = self._card("Local playlist copies")
        form = QFormLayout()
        row = QHBoxLayout()
        self.root = QLineEdit(settings.playlist_root()); self.root.setStyleSheet(INPUT_STYLE)
        row.addWidget(self.root)
        b = QPushButton("Browse..."); b.setStyleSheet(BUTTON_SECONDARY_STYLE + SMALL_BTN); b.clicked.connect(self._browse)
        row.addWidget(b)
        form.addRow("Folder:", row)
        cl.addLayout(form)
        h = QLabel("Every build writes a copy of each playlist and the device's file listing under <folder>\\<device name>\\.")
        h.setStyleSheet(LABEL_HINT); h.setWordWrap(True); cl.addWidget(h)
        layout.addWidget(card)

        card, cl = self._card("Claude (optional, for classifying unknown artists)")
        form = QFormLayout()
        self.api_key = QLineEdit(settings.qs().value("anthropic_api_key", "")); self.api_key.setStyleSheet(INPUT_STYLE)
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password); self.api_key.setPlaceholderText("sk-ant-...  (leave empty to use ANTHROPIC_API_KEY)")
        form.addRow("API key:", self.api_key)
        self.model = QComboBox(); self.model.setStyleSheet(COMBO_STYLE); self.model.setEditable(True)
        self.model.addItems(settings.MODELS); self.model.setCurrentText(settings.model())
        form.addRow("Model:", self.model)
        cl.addLayout(form)
        h2 = QLabel("The key is stored in this user's Windows registry settings for PlaylistPilot. Only artist names and "
                    "album titles are sent; answers are cached so each artist is asked about once.")
        h2.setStyleSheet(LABEL_HINT); h2.setWordWrap(True); cl.addWidget(h2)
        layout.addWidget(card)

        brow = QHBoxLayout(); brow.addStretch()
        self.saved = QLabel(""); self.saved.setStyleSheet(LABEL_HINT); brow.addWidget(self.saved)
        save = QPushButton("Save settings"); save.setStyleSheet(BUTTON_STYLE); save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self._save); brow.addWidget(save)
        layout.addLayout(brow)

        card, cl = self._card("About")
        about = QLabel("PlaylistPilot builds genre and custom playlists for portable players that run foobar2000 mobile "
                       "(FTP) or mount as a drive (USB), writing each entry in the exact path form that player resolves. "
                       "Conventions for the FiiO M33 R2R, iBasso DX180, Shanling M0 Pro and iPhone are built in; "
                       "add your own under Device.")
        about.setWordWrap(True); about.setStyleSheet(LABEL_BODY); cl.addWidget(about)
        layout.addWidget(card)
        layout.addStretch()

    def refresh(self):
        self.root.setText(settings.playlist_root())
        self.model.setCurrentText(settings.model())

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Playlist folder", self.root.text())
        if path:
            self.root.setText(path.replace("/", "\\"))

    def _save(self):
        settings.set_playlist_root(self.root.text().strip())
        settings.set_api_key(self.api_key.text().strip())
        settings.set_model(self.model.currentText().strip() or settings.DEFAULT_MODEL)
        self.saved.setText("Saved.")
        self.state.log("Settings saved.")
