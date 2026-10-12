"""Device view: pick a player, read the connection guidance, connect, scan the library."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget)

from core import settings
from core.library import ftp_list_root, load_listing, save_listing, scan_ftp, scan_local
from core.playlists import safe_name
from gui.dialogs.profile_dialog import ProfileDialog
from gui.state import AppState
from gui.theme import (VIEW_STYLE, BG_MAIN, BUTTON_DANGER_STYLE, BUTTON_GHOST_STYLE, BUTTON_SECONDARY_STYLE, BUTTON_STYLE,
                       CARD_STYLE, CHECK_STYLE, COMBO_STYLE, INPUT_STYLE, LABEL_BODY, LABEL_HINT, LOG_STYLE, NAVY,
                       SECTION_TITLE, SMALL_BTN, font_heading)
from gui.widgets.help_window import make_help_button
from gui.widgets.stat_card import StatCard
from gui.workers import Worker


class DeviceView(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.worker = None
        self.setObjectName("view")
        self.setStyleSheet(VIEW_STYLE)
        self._build_ui()
        state.device_changed.connect(self.refresh)
        state.library_changed.connect(self._update_stats)
        state.logged.connect(self._log)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        header = QLabel("Device")
        header.setFont(font_heading(20)); header.setStyleSheet(SECTION_TITLE)
        header_row.addWidget(header)
        header_row.addWidget(make_help_button("Device", self))
        header_row.addStretch()
        add_btn = QPushButton("Add device"); add_btn.setStyleSheet(BUTTON_STYLE); add_btn.clicked.connect(self._add)
        edit_btn = QPushButton("Edit"); edit_btn.setStyleSheet(BUTTON_SECONDARY_STYLE); edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton("Delete"); del_btn.setStyleSheet(BUTTON_DANGER_STYLE); del_btn.clicked.connect(self._delete)
        for b in (add_btn, edit_btn, del_btn):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            header_row.addWidget(b)
        layout.addLayout(header_row)

        # --- device picker + guidance
        pick = QFrame(); pick.setObjectName("card"); pick.setStyleSheet(CARD_STYLE)
        pl = QVBoxLayout(pick); pl.setContentsMargins(16, 12, 16, 12); pl.setSpacing(8)
        row = QHBoxLayout()
        row.addWidget(QLabel("Player:"))
        self.device_combo = QComboBox(); self.device_combo.setStyleSheet(COMBO_STYLE); self.device_combo.setMinimumWidth(260)
        self.device_combo.currentIndexChanged.connect(self._device_picked)
        row.addWidget(self.device_combo)
        self.kind_label = QLabel(""); self.kind_label.setStyleSheet(LABEL_HINT)
        row.addWidget(self.kind_label); row.addStretch()
        pl.addLayout(row)
        self.guidance = QLabel(""); self.guidance.setWordWrap(True); self.guidance.setStyleSheet(LABEL_BODY)
        pl.addWidget(self.guidance)
        layout.addWidget(pick)

        # --- connection
        conn = QFrame(); conn.setObjectName("card"); conn.setStyleSheet(CARD_STYLE)
        cl = QVBoxLayout(conn); cl.setContentsMargins(16, 12, 16, 12)
        title = QLabel("Connection"); title.setFont(font_heading(14)); title.setStyleSheet(SECTION_TITLE)
        cl.addWidget(title)
        form = QFormLayout(); form.setSpacing(8)
        self.target_label = QLabel(""); self.target_label.setStyleSheet(LABEL_BODY)
        form.addRow("Target:", self.target_label)
        pw_row = QHBoxLayout()
        self.password = QLineEdit(); self.password.setStyleSheet(INPUT_STYLE); self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("FTP password"); self.password.textChanged.connect(self._pw_changed)
        pw_row.addWidget(self.password)
        self.remember = QCheckBox("Remember on this PC"); self.remember.setStyleSheet(CHECK_STYLE)
        self.remember.toggled.connect(self._pw_changed)
        pw_row.addWidget(self.remember)
        form.addRow("Password:", pw_row)
        self.read_tags = QCheckBox("Read artist/album/genre from file tags while scanning (slower, USB only)")
        self.read_tags.setStyleSheet(CHECK_STYLE)
        form.addRow("", self.read_tags)
        cl.addLayout(form)
        btns = QHBoxLayout()
        self.test_btn = QPushButton("Test connection"); self.test_btn.setStyleSheet(BUTTON_SECONDARY_STYLE)
        self.test_btn.clicked.connect(self._test)
        self.scan_btn = QPushButton("Scan library"); self.scan_btn.setStyleSheet(BUTTON_STYLE)
        self.scan_btn.clicked.connect(self._scan)
        self.load_btn = QPushButton("Load last listing"); self.load_btn.setStyleSheet(BUTTON_GHOST_STYLE)
        self.load_btn.clicked.connect(self._load_listing)
        for b in (self.test_btn, self.scan_btn, self.load_btn):
            b.setCursor(Qt.CursorShape.PointingHandCursor); btns.addWidget(b)
        btns.addStretch()
        self.status = QLabel(""); self.status.setStyleSheet(LABEL_HINT)
        btns.addWidget(self.status)
        cl.addLayout(btns)
        layout.addWidget(conn)

        # --- stats
        cards = QHBoxLayout(); cards.setSpacing(16)
        self.card_tracks = StatCard("Tracks"); self.card_artists = StatCard("Artists")
        self.card_albums = StatCard("Albums"); self.card_vols = StatCard("Volumes")
        for c in (self.card_tracks, self.card_artists, self.card_albums, self.card_vols):
            cards.addWidget(c)
        layout.addLayout(cards)

        # --- log
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setStyleSheet(LOG_STYLE)
        self.log.setMaximumBlockCount(2000)
        layout.addWidget(self.log, stretch=1)

    # ------------------------------------------------------------------ data
    def refresh(self):
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        for p in self.state.profiles:
            self.device_combo.addItem(p.name)
        if self.state.profile:
            self.device_combo.setCurrentText(self.state.profile.name)
        self.device_combo.blockSignals(False)
        p = self.state.profile
        if not p:
            return
        self.kind_label.setText("FTP over Wi-Fi" if p.is_ftp else "USB drive")
        self.guidance.setText(p.guidance)
        if p.is_ftp:
            self.target_label.setText(f"ftp://{p.host}:{p.port}   user {p.user or '(anonymous)'}")
        else:
            self.target_label.setText(f"{p.usb_root}   folders: {', '.join(v.label for v in p.volumes)}")
        self.password.setEnabled(p.is_ftp); self.remember.setEnabled(p.is_ftp)
        self.read_tags.setEnabled(not p.is_ftp)
        self.password.blockSignals(True); self.remember.blockSignals(True)
        self.password.setText(self.state.password)
        self.remember.setChecked(bool(settings.remembered_password(p.name)))
        self.password.blockSignals(False); self.remember.blockSignals(False)
        self.load_btn.setEnabled(os.path.exists(self._listing_path()))
        self._update_stats()

    def _listing_path(self) -> str:
        return os.path.join(settings.playlist_root(), safe_name(self.state.profile.name), "file list.txt")

    def _update_stats(self):
        ts = self.state.tracks
        self.card_tracks.set_value(len(ts))
        self.card_artists.set_value(len({t.artist.lower() for t in ts if t.artist}))
        self.card_albums.set_value(len({(t.artist.lower(), t.album.lower()) for t in ts if t.album}))
        self.card_vols.set_value(len({t.volume for t in ts}))

    def _device_picked(self, idx: int):
        name = self.device_combo.currentText()
        prof = next((p for p in self.state.profiles if p.name == name), None)
        if prof:
            self.state.select_device(prof)

    def _pw_changed(self, *_):
        self.state.password = self.password.text()
        if self.state.profile:
            settings.remember_password(self.state.profile.name, self.password.text() if self.remember.isChecked() else "")

    def _log(self, msg: str):
        self.log.appendPlainText(msg)

    # ------------------------------------------------------------------ actions
    def _busy(self, on: bool, text: str = ""):
        for b in (self.test_btn, self.scan_btn, self.load_btn):
            b.setEnabled(not on)
        self.status.setText(text)

    def _test(self):
        p = self.state.profile
        if p.is_ftp:
            self._busy(True, "connecting...")
            self.worker = Worker(lambda progress=None: ftp_list_root(p, self.state.password))
            self.worker.finished_ok.connect(self._test_ok)
            self.worker.failed.connect(self._fail)
            self.worker.start()
        else:
            missing = [v.label for v in p.volumes if not os.path.isdir(os.path.join(p.usb_root, v.label))]
            if not os.path.isdir(p.usb_root):
                self._fail(f"Drive {p.usb_root} is not mounted.")
            elif missing:
                self._fail(f"Drive is there but folder(s) missing: {', '.join(missing)}")
            else:
                self._test_ok([v.label for v in p.volumes])

    def _test_ok(self, folders):
        self._busy(False, "connected")
        self.state.set_connected(True, "connected")
        self.state.log(f"Connected to {self.state.profile.name}. Top-level folders: {', '.join(folders)}")
        known = {v.label for v in self.state.profile.volumes}
        unknown = [f for f in folders if f not in known and f not in self.state.profile.skip_dirs and f != "foobar2000 Music Folder"]
        if unknown:
            self.state.log(f"Folders not in this profile's volumes (edit the device to add them): {', '.join(unknown)}")

    def _fail(self, msg: str):
        self._busy(False, "failed")
        self.state.set_connected(False, msg)
        self.state.log("ERROR " + msg)
        if "10061" in msg or "refused" in msg.lower():
            self.state.log("Hint: the FTP server stops when the player's screen locks. Wake it, reopen the FTP screen, try again.")

    def _scan(self):
        p = self.state.profile
        self._busy(True, "scanning...")
        self.state.log(f"Scanning {p.name} ...")
        if p.is_ftp:
            self.worker = Worker(scan_ftp, p, self.state.password)
        else:
            self.worker = Worker(scan_local, p, read_tags=self.read_tags.isChecked())
        self.worker.progress.connect(self.state.log)
        self.worker.finished_ok.connect(self._scan_done)
        self.worker.failed.connect(self._fail)
        self.worker.start()

    def _scan_done(self, tracks):
        self._busy(False, f"{len(tracks):,} tracks")
        self.state.set_connected(True, "connected")
        self.state.set_tracks(tracks)
        try:
            save_listing(tracks, self._listing_path())
            self.state.log(f"Listing saved to {self._listing_path()}")
        except OSError as e:
            self.state.log(f"Could not save listing: {e}")
        self.load_btn.setEnabled(True)
        self.state.log(f"Scan complete: {len(tracks):,} tracks. Go to Playlists to build.")

    def _load_listing(self):
        try:
            tracks = load_listing(self._listing_path(), self.state.profile)
        except OSError as e:
            self._fail(str(e)); return
        self.state.set_tracks(tracks)
        self.status.setText(f"{len(tracks):,} tracks (from saved listing)")
        self.state.log(f"Loaded {len(tracks):,} tracks from {self._listing_path()} (no connection needed to build; deploying still needs one).")

    def _add(self):
        dlg = ProfileDialog(None, [p.name for p in self.state.profiles], self)
        if dlg.exec():
            prof = dlg.result_profile()
            self.state.save_profile(prof)
            self.state.select_device(prof)

    def _edit(self):
        dlg = ProfileDialog(self.state.profile, [p.name for p in self.state.profiles], self)
        if dlg.exec():
            self.state.save_profile(dlg.result_profile())
            self.refresh()

    def _delete(self):
        p = self.state.profile
        what = "reset to its built-in defaults" if p.builtin else "deleted"
        if QMessageBox.question(self, "Delete device", f"'{p.name}' will be {what}. Continue?") == QMessageBox.StandardButton.Yes:
            self.state.delete_profile(p)
