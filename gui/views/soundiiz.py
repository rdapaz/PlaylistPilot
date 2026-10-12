"""Soundiiz view: import a Soundiiz CSV and match it against the device library; export playlists as CSV."""
from __future__ import annotations

import os
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QDoubleSpinBox, QFileDialog, QFrame,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from core import settings
from core.genres import GENRES, group_by_genre
from core.library import Track
from core.playlists import safe_name, sort_tracks
from core.soundiiz import (LibraryIndex, Match, match_rows, read_soundiiz_csv, rows_from_m3u, write_soundiiz_csv,
                           write_soundiiz_csv_rows)
from gui.state import AppState
from gui.theme import (VIEW_STYLE, BG_MAIN, BUTTON_GHOST_STYLE, BUTTON_SECONDARY_STYLE, BUTTON_STYLE, CARD_STYLE, CHECK_STYLE,
                       INPUT_STYLE, LABEL_HINT, NEGATIVE, POSITIVE, SECTION_TITLE, SMALL_BTN, TABLE_STYLE, WARNING,
                       font_heading)
from gui.widgets.help_window import make_help_button


class PickTrackDialog(QDialog):
    """Search the library and pick one track for an unmatched (or wrongly matched) CSV row."""

    def __init__(self, index: LibraryIndex, seed: str, parent=None):
        super().__init__(parent)
        self.index = index
        self.chosen: Optional[Track] = None
        self.setWindowTitle("Pick a track")
        self.resize(640, 460)
        lay = QVBoxLayout(self); lay.setContentsMargins(20, 20, 20, 20)
        self.search = QLineEdit(seed); self.search.setStyleSheet(INPUT_STYLE)
        self.search.setPlaceholderText("Type part of the artist or title..."); self.search.textChanged.connect(self._fill)
        lay.addWidget(self.search)
        self.list = QListWidget(); self.list.setStyleSheet(TABLE_STYLE); self.list.doubleClicked.connect(self._accept)
        lay.addWidget(self.list)
        row = QHBoxLayout(); row.addStretch()
        clear = QPushButton("Leave unmatched"); clear.setStyleSheet(BUTTON_GHOST_STYLE); clear.clicked.connect(lambda: self.done(2))
        cancel = QPushButton("Cancel"); cancel.setStyleSheet(BUTTON_GHOST_STYLE); cancel.clicked.connect(self.reject)
        ok = QPushButton("Use selected"); ok.setStyleSheet(BUTTON_STYLE); ok.clicked.connect(self._accept)
        row.addWidget(clear); row.addWidget(cancel); row.addWidget(ok); lay.addLayout(row)
        self._fill()

    def _fill(self):
        self.list.clear()
        for t in self.index.search(self.search.text()):
            it = QListWidgetItem(f"{t.artist} - {t.title}   [{t.album}]"); it.setData(Qt.ItemDataRole.UserRole, t)
            self.list.addItem(it)

    def _accept(self, *_):
        it = self.list.currentItem()
        if it:
            self.chosen = it.data(Qt.ItemDataRole.UserRole)
            self.accept()


class SoundiizView(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.index: Optional[LibraryIndex] = None
        self.matches: List[Match] = []
        self.csv_path = ""
        self.setObjectName("view")
        self.setStyleSheet(VIEW_STYLE)
        self._build_ui()
        state.library_changed.connect(self._library_changed)
        state.genres_changed.connect(self._fill_export_list)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(24, 24, 24, 24); layout.setSpacing(16)
        header_row = QHBoxLayout()
        header = QLabel("Soundiiz"); header.setFont(font_heading(20)); header.setStyleSheet(SECTION_TITLE)
        header_row.addWidget(header); header_row.addWidget(make_help_button("Soundiiz", self)); header_row.addStretch()
        layout.addLayout(header_row)

        # --- import card
        icard = QFrame(); icard.setObjectName("card"); icard.setStyleSheet(CARD_STYLE)
        il = QVBoxLayout(icard); il.setContentsMargins(16, 12, 16, 12); il.setSpacing(8)
        t = QLabel("Import a Soundiiz CSV and match it to this device"); t.setFont(font_heading(14)); t.setStyleSheet(SECTION_TITLE)
        il.addWidget(t)
        top = QHBoxLayout()
        self.csv_label = QLabel("No file chosen"); self.csv_label.setStyleSheet(LABEL_HINT)
        open_b = QPushButton("Open CSV..."); open_b.setStyleSheet(BUTTON_STYLE + SMALL_BTN); open_b.clicked.connect(self._open_csv)
        top.addWidget(open_b); top.addWidget(self.csv_label, stretch=1)
        top.addWidget(QLabel("Min score:"))
        self.min_score = QDoubleSpinBox(); self.min_score.setRange(0.5, 1.0); self.min_score.setSingleStep(0.05)
        self.min_score.setValue(0.80); self.min_score.setStyleSheet(INPUT_STYLE); self.min_score.valueChanged.connect(self._rematch)
        top.addWidget(self.min_score)
        self.name_edit = QLineEdit(); self.name_edit.setStyleSheet(INPUT_STYLE); self.name_edit.setPlaceholderText("Playlist name"); self.name_edit.setMaximumWidth(220)
        top.addWidget(self.name_edit)
        il.addLayout(top)
        self.table = QTableWidget(0, 6); self.table.setStyleSheet(TABLE_STYLE)
        self.table.setHorizontalHeaderLabels(["CSV title", "CSV artist", "CSV album", "Matched track on device", "Score", "Status"])
        self.table.setAlternatingRowColors(True); self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        for i, w in enumerate([200, 150, 160, 420, 60]):
            self.table.setColumnWidth(i, w)
        self.table.doubleClicked.connect(self._fix_row)
        il.addWidget(self.table, stretch=1)
        brow = QHBoxLayout()
        self.summary = QLabel(""); self.summary.setStyleSheet(LABEL_HINT); brow.addWidget(self.summary, stretch=1)
        fix_b = QPushButton("Fix selected match"); fix_b.setStyleSheet(BUTTON_GHOST_STYLE + SMALL_BTN); fix_b.clicked.connect(self._fix_row)
        unm_b = QPushButton("Save unmatched as CSV"); unm_b.setStyleSheet(BUTTON_GHOST_STYLE + SMALL_BTN); unm_b.clicked.connect(self._save_unmatched)
        self.queue_b = QPushButton("Add matched tracks to build list"); self.queue_b.setStyleSheet(BUTTON_STYLE + SMALL_BTN)
        self.queue_b.clicked.connect(self._queue)
        for b in (fix_b, unm_b, self.queue_b):
            b.setCursor(Qt.CursorShape.PointingHandCursor); brow.addWidget(b)
        il.addLayout(brow)
        layout.addWidget(icard, stretch=3)

        # --- export card
        ecard = QFrame(); ecard.setObjectName("card"); ecard.setStyleSheet(CARD_STYLE)
        el = QVBoxLayout(ecard); el.setContentsMargins(16, 12, 16, 12); el.setSpacing(8)
        t2 = QLabel("Export playlists as Soundiiz CSV"); t2.setFont(font_heading(14)); t2.setStyleSheet(SECTION_TITLE)
        el.addWidget(t2)
        h = QLabel("One CSV per playlist, with Soundiiz's own columns (Track name, Artist name, Album, Playlist name, Type, ISRC, Duration). "
                   "Upload them at soundiiz.com > Import > CSV. Built playlists come from the current device's library; "
                   "an existing .m3u/.m3u8 file is converted from its track labels.")
        h.setWordWrap(True); h.setStyleSheet(LABEL_HINT); el.addWidget(h)
        erow = QHBoxLayout()
        self.export_list = QListWidget(); self.export_list.setStyleSheet(TABLE_STYLE); self.export_list.setMaximumHeight(120)
        self.export_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        erow.addWidget(self.export_list, stretch=1)
        eb = QVBoxLayout()
        exp_b = QPushButton("Export selected..."); exp_b.setStyleSheet(BUTTON_STYLE + SMALL_BTN); exp_b.clicked.connect(self._export_selected)
        m3u_b = QPushButton("Export an .m3u8 file..."); m3u_b.setStyleSheet(BUTTON_SECONDARY_STYLE + SMALL_BTN); m3u_b.clicked.connect(self._export_m3u)
        eb.addWidget(exp_b); eb.addWidget(m3u_b); eb.addStretch()
        erow.addLayout(eb)
        el.addLayout(erow)
        layout.addWidget(ecard, stretch=1)

    # ------------------------------------------------------------------ data
    def refresh(self):
        self._fill_export_list()
        if self.index is None and self.state.tracks:
            self.index = LibraryIndex(self.state.tracks)

    def _library_changed(self):
        self.index = LibraryIndex(self.state.tracks) if self.state.tracks else None
        if self.matches:
            self._rematch()
        self._fill_export_list()

    def _fill_export_list(self):
        self.export_list.clear()
        if not self.state.tracks:
            return
        groups = group_by_genre(self.state.tracks, self.state.genre_map)
        for g in GENRES:
            if groups[g]:
                it = QListWidgetItem(f"{g}  ({len(groups[g]):,} tracks)"); it.setData(Qt.ItemDataRole.UserRole, ("genre", g))
                self.export_list.addItem(it)
        for name, tracks in self.state.custom_playlists.items():
            it = QListWidgetItem(f"{name}  ({len(tracks)} tracks, custom)"); it.setData(Qt.ItemDataRole.UserRole, ("custom", name))
            self.export_list.addItem(it)

    # ------------------------------------------------------------------ import
    def _open_csv(self):
        if not self.state.tracks:
            QMessageBox.information(self, "No library", "Scan the device (or load its last listing) first, so there is something to match against.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Soundiiz CSV export", settings.playlist_root(), "CSV files (*.csv);;All files (*)")
        if not path:
            return
        try:
            rows = read_soundiiz_csv(path)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "CSV", str(e)); return
        self.csv_path = path
        self.rows = rows
        self.csv_label.setText(f"{os.path.basename(path)}: {len(rows)} rows")
        if not self.name_edit.text().strip():
            self.name_edit.setText(rows[0].playlist if rows and rows[0].playlist else os.path.splitext(os.path.basename(path))[0])
        self._rematch()

    def _rematch(self, *_):
        if not getattr(self, "rows", None):
            return
        if self.index is None:
            self.index = LibraryIndex(self.state.tracks)
        manual = {i: m for i, m in enumerate(self.matches) if m.manual}
        self.matches = match_rows(self.rows, self.index, self.min_score.value())
        for i, m in manual.items():
            if i < len(self.matches):
                self.matches[i] = m
        self._fill_table()

    def _fill_table(self):
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(self.matches))
        ok = 0
        for r, m in enumerate(self.matches):
            vals = [m.row.title, m.row.artist, m.row.album,
                    f"{m.track.artist} - {m.track.title}   [{m.track.album}]" if m.track else "",
                    f"{m.score:.2f}" if m.score else "", "manual" if m.manual else ("matched" if m.ok else "no match")]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c == 5:
                    it.setForeground(QColor(POSITIVE if m.ok else NEGATIVE))
                elif c == 4 and m.ok and m.score < 0.9 and not m.manual:
                    it.setForeground(QColor(WARNING))
                self.table.setItem(r, c, it)
            ok += m.ok
        self.table.setUpdatesEnabled(True)
        self.summary.setText(f"{ok} of {len(self.matches)} rows matched on {self.state.profile.name}. "
                             "Double-click a row to fix it. Amber scores are matches worth a glance.")
        self.queue_b.setEnabled(ok > 0)

    def _fix_row(self, *_):
        sel = self.table.selectedIndexes()
        if not sel or self.index is None:
            return
        r = sel[0].row(); m = self.matches[r]
        dlg = PickTrackDialog(self.index, f"{m.row.artist} {m.row.title}", self)
        res = dlg.exec()
        if res == 2:
            m.track, m.manual, m.score = None, True, 0.0
        elif res == QDialog.DialogCode.Accepted and dlg.chosen:
            m.track, m.manual, m.score = dlg.chosen, True, 1.0
        else:
            return
        self._fill_table()

    def _save_unmatched(self):
        bad = [m for m in self.matches if not m.ok]
        if not bad:
            QMessageBox.information(self, "Unmatched", "Every row matched."); return
        default = os.path.join(os.path.dirname(self.csv_path) or settings.playlist_root(),
                               os.path.splitext(os.path.basename(self.csv_path))[0] + ".not_on_device.csv")
        path, _ = QFileDialog.getSaveFileName(self, "Save unmatched rows", default, "CSV files (*.csv)")
        if not path:
            return
        write_soundiiz_csv_rows(path, self.name_edit.text().strip(), [(m.row.title, m.row.artist, m.row.album) for m in bad])
        self.state.log(f"{len(bad)} unmatched rows saved to {path}")

    def _queue(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Playlist name", "Give the playlist a name first."); return
        tracks, seen = [], set()
        for m in self.matches:
            if m.ok and m.track.key not in seen:
                tracks.append(m.track); seen.add(m.track.key)
        self.state.custom_playlists[name] = tracks
        self.state.log(f"Soundiiz playlist '{name}' queued with {len(tracks)} matched tracks "
                       f"({len(self.matches) - len(tracks)} rows skipped). Deploy it from the Playlists view.")
        self._fill_export_list()
        QMessageBox.information(self, "Queued", f"'{name}' is in the build list with {len(tracks)} tracks.\n"
                                "Go to Playlists and press Deploy to device (untick the genre playlists if you only want this one).")

    # ------------------------------------------------------------------ export
    def _export_selected(self):
        items = self.export_list.selectedItems()
        if not items:
            QMessageBox.information(self, "Export", "Select one or more playlists first."); return
        folder = QFileDialog.getExistingDirectory(self, "Folder for CSV files",
                                                  os.path.join(settings.playlist_root(), safe_name(self.state.profile.name)))
        if not folder:
            return
        groups = group_by_genre(self.state.tracks, self.state.genre_map)
        for it in items:
            kind, name = it.data(Qt.ItemDataRole.UserRole)
            tracks = sort_tracks(groups[name]) if kind == "genre" else self.state.custom_playlists.get(name, [])
            path = os.path.join(folder, safe_name(name) + ".soundiiz.csv")
            n = write_soundiiz_csv(path, name, tracks)
            self.state.log(f"Exported {n} rows to {path}")
        QMessageBox.information(self, "Export", f"{len(items)} CSV file(s) written to {folder}.")

    def _export_m3u(self):
        path, _ = QFileDialog.getOpenFileName(self, "Playlist file", settings.playlist_root(), "Playlists (*.m3u8 *.m3u)")
        if not path:
            return
        rows = rows_from_m3u(path)
        if not rows:
            QMessageBox.warning(self, "Export", "No tracks found in that file."); return
        name = os.path.splitext(os.path.basename(path))[0]
        out, _ = QFileDialog.getSaveFileName(self, "Save Soundiiz CSV", os.path.join(os.path.dirname(path), name + ".soundiiz.csv"), "CSV files (*.csv)")
        if not out:
            return
        n = write_soundiiz_csv_rows(out, name, rows)
        self.state.log(f"Exported {n} rows from {os.path.basename(path)} to {out}")
