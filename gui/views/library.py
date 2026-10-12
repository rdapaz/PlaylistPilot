"""Library view: every scanned track with its inferred artist/album and resolved genres; artist overrides."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from core.genres import GENRES
from gui.state import AppState
from gui.theme import (VIEW_STYLE, BG_MAIN, BUTTON_GHOST_STYLE, BUTTON_SECONDARY_STYLE, BUTTON_STYLE, CARD_STYLE, CHECK_STYLE,
                       COMBO_STYLE, INPUT_STYLE, LABEL_HINT, SECTION_TITLE, TABLE_STYLE, font_heading)
from gui.widgets.help_window import make_help_button

MAX_ROWS = 3000


class ArtistGenreDialog(QDialog):
    def __init__(self, artist: str, current: list, source: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Genres for {artist}")
        self.setMinimumWidth(360)
        lay = QVBoxLayout(self); lay.setContentsMargins(20, 20, 20, 20)
        hint = QLabel(f"Currently from: {source or 'nothing (unclassified)'}. Tick the playlists this artist belongs in.")
        hint.setWordWrap(True); hint.setStyleSheet(LABEL_HINT); lay.addWidget(hint)
        self.boxes = {}
        for g in GENRES:
            cb = QCheckBox(g.replace("&", "&&")); cb.setStyleSheet(CHECK_STYLE); cb.setChecked(g in current)
            self.boxes[g] = cb; lay.addWidget(cb)
        row = QHBoxLayout(); row.addStretch()
        self.reset_btn = QPushButton("Remove override"); self.reset_btn.setStyleSheet(BUTTON_GHOST_STYLE)
        self.reset_btn.setEnabled(source == "manual"); self.reset_btn.clicked.connect(lambda: self.done(2))
        cancel = QPushButton("Cancel"); cancel.setStyleSheet(BUTTON_GHOST_STYLE); cancel.clicked.connect(self.reject)
        ok = QPushButton("Save"); ok.setStyleSheet(BUTTON_STYLE); ok.clicked.connect(self.accept)
        row.addWidget(self.reset_btn); row.addWidget(cancel); row.addWidget(ok)
        lay.addLayout(row)

    def chosen(self) -> list:
        return [g for g, cb in self.boxes.items() if cb.isChecked()]


class LibraryView(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("view")
        self.setStyleSheet(VIEW_STYLE)
        self._build_ui()
        state.library_changed.connect(self.refresh)
        state.genres_changed.connect(self.refresh)

    def _build_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(24, 24, 24, 24); layout.setSpacing(16)
        header_row = QHBoxLayout()
        header = QLabel("Library"); header.setFont(font_heading(20)); header.setStyleSheet(SECTION_TITLE)
        header_row.addWidget(header); header_row.addWidget(make_help_button("Library", self)); header_row.addStretch()
        self.count_label = QLabel(""); self.count_label.setStyleSheet(LABEL_HINT); header_row.addWidget(self.count_label)
        self.override_btn = QPushButton("Set genres for selected artist")
        self.override_btn.setStyleSheet(BUTTON_SECONDARY_STYLE); self.override_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.override_btn.clicked.connect(self._override)
        header_row.addWidget(self.override_btn)
        layout.addLayout(header_row)

        filt = QFrame(); filt.setObjectName("card"); filt.setStyleSheet(CARD_STYLE)
        fl = QHBoxLayout(filt); fl.setContentsMargins(16, 8, 16, 8); fl.setSpacing(12)
        self.search = QLineEdit(); self.search.setStyleSheet(INPUT_STYLE); self.search.setPlaceholderText("Search artist, album, title or path...")
        self.search.textChanged.connect(self.refresh); fl.addWidget(self.search, stretch=1)
        fl.addWidget(QLabel("Genre:"))
        self.genre_filter = QComboBox(); self.genre_filter.setStyleSheet(COMBO_STYLE)
        self.genre_filter.addItems(["All", "Unclassified"] + GENRES); self.genre_filter.currentIndexChanged.connect(self.refresh)
        fl.addWidget(self.genre_filter)
        fl.addWidget(QLabel("Volume:"))
        self.volume_filter = QComboBox(); self.volume_filter.setStyleSheet(COMBO_STYLE); self.volume_filter.addItem("All")
        self.volume_filter.currentIndexChanged.connect(self.refresh); fl.addWidget(self.volume_filter)
        layout.addWidget(filt)

        card = QFrame(); card.setObjectName("card"); card.setStyleSheet(CARD_STYLE)
        cl = QVBoxLayout(card); cl.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 6); self.table.setStyleSheet(TABLE_STYLE)
        self.table.setHorizontalHeaderLabels(["Artist", "Album", "Title", "Genres", "Source", "Path"])
        self.table.setAlternatingRowColors(True); self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        hh = self.table.horizontalHeader(); hh.setStretchLastSection(True)
        for i, w in enumerate([180, 220, 240, 170, 70]):
            self.table.setColumnWidth(i, w)
        self.table.doubleClicked.connect(self._override)
        cl.addWidget(self.table)
        layout.addWidget(card, stretch=1)

    def _filtered(self):
        q = self.search.text().strip().lower()
        g = self.genre_filter.currentText(); v = self.volume_filter.currentText()
        gm = self.state.genre_map
        for t in self.state.tracks:
            if v != "All" and t.volume != v:
                continue
            if q and q not in f"{t.artist} {t.album} {t.title} {t.rel}".lower():
                continue
            genres = gm.genres_for(t)
            if g == "Unclassified" and genres:
                continue
            if g not in ("All", "Unclassified") and g not in genres:
                continue
            yield t, genres

    def refresh(self):
        vols = sorted({t.volume for t in self.state.tracks})
        if [self.volume_filter.itemText(i) for i in range(1, self.volume_filter.count())] != vols:
            self.volume_filter.blockSignals(True); self.volume_filter.clear()
            self.volume_filter.addItem("All"); self.volume_filter.addItems(vols); self.volume_filter.blockSignals(False)
        rows = list(self._filtered())
        gm = self.state.genre_map
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(min(len(rows), MAX_ROWS))
        for r, (t, genres) in enumerate(rows[:MAX_ROWS]):
            for c, val in enumerate([t.artist, t.album, t.title, ", ".join(genres), gm.source(t.artist), f"{t.volume}/{t.rel}"]):
                self.table.setItem(r, c, QTableWidgetItem(val))
        self.table.setUpdatesEnabled(True)
        more = f" (showing first {MAX_ROWS:,})" if len(rows) > MAX_ROWS else ""
        self.count_label.setText(f"{len(rows):,} of {len(self.state.tracks):,} tracks{more}")

    def _override(self, *_):
        sel = self.table.selectedItems()
        if not sel:
            return
        artist = self.table.item(sel[0].row(), 0).text()
        if not artist:
            return
        gm = self.state.genre_map
        dlg = ArtistGenreDialog(artist, gm.artist_genres(artist), gm.source(artist), self)
        res = dlg.exec()
        if res == 2:
            gm.clear_override(artist)
        elif res == QDialog.DialogCode.Accepted:
            gm.set_override(artist, dlg.chosen())
        else:
            return
        self.state.genres_changed.emit()
