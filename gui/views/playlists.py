"""Playlists view: build the standard genre playlists (with Claude filling the gaps), compose custom ones,
save copies locally and deploy to the player."""
from __future__ import annotations

from typing import Dict, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QTextEdit,
                               QVBoxLayout, QWidget)

from core import settings
from core.genres import GENRES, classify_with_claude, group_by_genre
from core.library import Track
from core.playlists import deploy, render_m3u, write_local_copies
from gui.state import AppState
from gui.theme import (VIEW_STYLE, BG_MAIN, BUTTON_DANGER_STYLE, BUTTON_GHOST_STYLE, BUTTON_SECONDARY_STYLE, BUTTON_STYLE,
                       CARD_STYLE, CHECK_STYLE, INPUT_STYLE, LABEL_HINT, LOG_STYLE, SECTION_TITLE, SMALL_BTN,
                       TABLE_STYLE, font_heading)
from gui.widgets.help_window import make_help_button
from gui.workers import Worker


class PlaylistsView(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.worker = None
        self.setObjectName("view")
        self.setStyleSheet(VIEW_STYLE)
        self._build_ui()
        state.library_changed.connect(self.refresh)
        state.genres_changed.connect(self.refresh)
        state.device_changed.connect(self.refresh)
        state.logged.connect(self.log.appendPlainText)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(24, 24, 24, 24); layout.setSpacing(16)
        header_row = QHBoxLayout()
        header = QLabel("Playlists"); header.setFont(font_heading(20)); header.setStyleSheet(SECTION_TITLE)
        header_row.addWidget(header); header_row.addWidget(make_help_button("Playlists", self)); header_row.addStretch()
        self.preview_btn = QPushButton("Preview"); self.preview_btn.setStyleSheet(BUTTON_GHOST_STYLE); self.preview_btn.clicked.connect(self._preview)
        self.save_btn = QPushButton("Save copies locally"); self.save_btn.setStyleSheet(BUTTON_SECONDARY_STYLE); self.save_btn.clicked.connect(self._save_local)
        self.deploy_btn = QPushButton("Deploy to device"); self.deploy_btn.setStyleSheet(BUTTON_STYLE); self.deploy_btn.clicked.connect(self._deploy)
        for b in (self.preview_btn, self.save_btn, self.deploy_btn):
            b.setCursor(Qt.CursorShape.PointingHandCursor); header_row.addWidget(b)
        layout.addLayout(header_row)

        body = QHBoxLayout(); body.setSpacing(16)

        # --- genre playlists card
        gcard = QFrame(); gcard.setObjectName("card"); gcard.setStyleSheet(CARD_STYLE)
        gl = QVBoxLayout(gcard); gl.setContentsMargins(16, 12, 16, 12); gl.setSpacing(8)
        t = QLabel("Genre playlists"); t.setFont(font_heading(14)); t.setStyleSheet(SECTION_TITLE); gl.addWidget(t)
        self.genre_boxes: Dict[str, QCheckBox] = {}
        for g in GENRES:
            cb = QCheckBox(g.replace("&", "&&")); cb.setStyleSheet(CHECK_STYLE); cb.setChecked(True)
            self.genre_boxes[g] = cb; gl.addWidget(cb)
        self.unknown_label = QLabel(""); self.unknown_label.setStyleSheet(LABEL_HINT); self.unknown_label.setWordWrap(True)
        gl.addWidget(self.unknown_label)
        crow = QHBoxLayout()
        self.claude_btn = QPushButton("Ask Claude about unknown artists"); self.claude_btn.setStyleSheet(BUTTON_SECONDARY_STYLE + SMALL_BTN)
        self.claude_btn.clicked.connect(self._ask_claude)
        self.review_btn = QPushButton("Review Claude's answers"); self.review_btn.setStyleSheet(BUTTON_GHOST_STYLE + SMALL_BTN)
        self.review_btn.clicked.connect(self._review_claude)
        crow.addWidget(self.claude_btn); crow.addWidget(self.review_btn); crow.addStretch()
        gl.addLayout(crow)
        gl.addStretch()
        body.addWidget(gcard, stretch=2)

        # --- custom playlist card
        ccard = QFrame(); ccard.setObjectName("card"); ccard.setStyleSheet(CARD_STYLE)
        cl = QVBoxLayout(ccard); cl.setContentsMargins(16, 12, 16, 12); cl.setSpacing(8)
        t2 = QLabel("Custom playlist"); t2.setFont(font_heading(14)); t2.setStyleSheet(SECTION_TITLE); cl.addWidget(t2)
        nrow = QHBoxLayout()
        self.custom_name = QLineEdit(); self.custom_name.setStyleSheet(INPUT_STYLE); self.custom_name.setPlaceholderText("Playlist name")
        nrow.addWidget(self.custom_name)
        self.custom_search = QLineEdit(); self.custom_search.setStyleSheet(INPUT_STYLE); self.custom_search.setPlaceholderText("Filter library...")
        self.custom_search.textChanged.connect(self._fill_available)
        nrow.addWidget(self.custom_search)
        cl.addLayout(nrow)
        lists = QHBoxLayout()
        self.available = QListWidget(); self.available.setStyleSheet(TABLE_STYLE)
        self.available.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.available.doubleClicked.connect(self._add_selected)
        self.chosen = QListWidget(); self.chosen.setStyleSheet(TABLE_STYLE)
        self.chosen.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.chosen.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        mid = QVBoxLayout(); mid.addStretch()
        add_b = QPushButton("Add >"); add_b.setStyleSheet(BUTTON_SECONDARY_STYLE + SMALL_BTN); add_b.clicked.connect(self._add_selected)
        all_b = QPushButton("Add all shown >>"); all_b.setStyleSheet(BUTTON_SECONDARY_STYLE + SMALL_BTN); all_b.clicked.connect(self._add_all)
        rm_b = QPushButton("< Remove"); rm_b.setStyleSheet(BUTTON_GHOST_STYLE + SMALL_BTN); rm_b.clicked.connect(self._remove_selected)
        clr_b = QPushButton("Clear"); clr_b.setStyleSheet(BUTTON_GHOST_STYLE + SMALL_BTN); clr_b.clicked.connect(self.chosen.clear)
        for b in (add_b, all_b, rm_b, clr_b):
            mid.addWidget(b)
        mid.addStretch()
        lists.addWidget(self.available, stretch=3); lists.addLayout(mid); lists.addWidget(self.chosen, stretch=3)
        cl.addLayout(lists, stretch=1)
        qrow = QHBoxLayout()
        self.chosen_label = QLabel("0 tracks"); self.chosen_label.setStyleSheet(LABEL_HINT); qrow.addWidget(self.chosen_label); qrow.addStretch()
        queue_b = QPushButton("Add to build list"); queue_b.setStyleSheet(BUTTON_STYLE + SMALL_BTN); queue_b.clicked.connect(self._queue_custom)
        qrow.addWidget(queue_b)
        cl.addLayout(qrow)
        self.queued = QListWidget(); self.queued.setStyleSheet(TABLE_STYLE); self.queued.setMaximumHeight(90)
        cl.addWidget(QLabel("Custom playlists in the build list (double-click to remove):"))
        self.queued.doubleClicked.connect(self._unqueue)
        cl.addWidget(self.queued)
        body.addWidget(ccard, stretch=5)
        layout.addLayout(body, stretch=1)

        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setStyleSheet(LOG_STYLE)
        self.log.setMaximumBlockCount(2000); self.log.setFixedHeight(150)
        layout.addWidget(self.log)

    # ------------------------------------------------------------------ data
    def refresh(self):
        groups = group_by_genre(self.state.tracks, self.state.genre_map)
        for g, cb in self.genre_boxes.items():
            n = len(groups[g])
            cb.setText(f"{g.replace(chr(38), chr(38) * 2)}   ({n:,} tracks)")
            cb.setEnabled(n > 0)
            if n == 0:
                cb.setChecked(False)
        unknown = self.state.genre_map.unknown_artists(self.state.tracks)
        n_unknown_tracks = sum(1 for t in self.state.tracks if not self.state.genre_map.genres_for(t))
        self.unknown_label.setText(
            f"{len(unknown):,} artists ({n_unknown_tracks:,} tracks) are not placed by any rule. "
            + ("Claude can suggest where they belong; answers are cached and editable in Library." if unknown else "")
        )
        self.claude_btn.setEnabled(bool(unknown))
        self._fill_available()
        self.chosen.clear(); self.queued.clear()
        for name in self.state.custom_playlists:
            self.queued.addItem(name)
        self.deploy_btn.setText("Deploy to device" + ("" if self.state.profile is None else f" ({self.state.profile.name})"))

    def _fill_available(self):
        q = self.custom_search.text().strip().lower()
        self.available.clear()
        shown = 0
        for t in self.state.tracks:
            if q and q not in f"{t.artist} {t.album} {t.title}".lower():
                continue
            it = QListWidgetItem(f"{t.artist} - {t.title}   [{t.album}]"); it.setData(Qt.ItemDataRole.UserRole, t.key)
            self.available.addItem(it)
            shown += 1
            if shown >= 2000:
                break

    def _track_by_key(self) -> Dict[str, Track]:
        return {t.key: t for t in self.state.tracks}

    def _add_items(self, items):
        have = {self.chosen.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.chosen.count())}
        for it in items:
            k = it.data(Qt.ItemDataRole.UserRole)
            if k in have:
                continue
            new = QListWidgetItem(it.text()); new.setData(Qt.ItemDataRole.UserRole, k)
            self.chosen.addItem(new); have.add(k)
        self.chosen_label.setText(f"{self.chosen.count()} tracks")

    def _add_selected(self, *_):
        self._add_items(self.available.selectedItems())

    def _add_all(self):
        self._add_items([self.available.item(i) for i in range(self.available.count())])

    def _remove_selected(self):
        for it in self.chosen.selectedItems():
            self.chosen.takeItem(self.chosen.row(it))
        self.chosen_label.setText(f"{self.chosen.count()} tracks")

    def _queue_custom(self):
        name = self.custom_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Custom playlist", "Give the playlist a name first."); return
        if self.chosen.count() == 0:
            QMessageBox.warning(self, "Custom playlist", "Add some tracks first."); return
        by_key = self._track_by_key()
        tracks = [by_key[self.chosen.item(i).data(Qt.ItemDataRole.UserRole)] for i in range(self.chosen.count())]
        self.state.custom_playlists[name] = tracks
        if not self.queued.findItems(name, Qt.MatchFlag.MatchExactly):
            self.queued.addItem(name)
        self.state.log(f"Custom playlist '{name}' with {len(tracks)} tracks added to the build list.")
        self.chosen.clear(); self.custom_name.clear(); self.chosen_label.setText("0 tracks")

    def _unqueue(self, idx):
        name = self.queued.item(idx.row()).text()
        self.state.custom_playlists.pop(name, None)
        self.queued.takeItem(idx.row())

    # ------------------------------------------------------------------ building
    def _build(self) -> Dict[str, str]:
        p = self.state.profile
        out: Dict[str, str] = {}
        groups = group_by_genre(self.state.tracks, self.state.genre_map)
        for g, cb in self.genre_boxes.items():
            if cb.isChecked() and groups[g]:
                out[g] = render_m3u(p, groups[g])
        for name, tracks in self.state.custom_playlists.items():
            out[name] = render_m3u(p, tracks, keep_order=True)
        return out

    def _check_ready(self) -> bool:
        if not self.state.tracks:
            QMessageBox.information(self, "No library", "Scan the device (or load its last listing) first."); return False
        if not any(cb.isChecked() for cb in self.genre_boxes.values()) and not self.state.custom_playlists:
            QMessageBox.information(self, "Nothing selected", "Tick at least one genre or add a custom playlist."); return False
        return True

    def _preview(self):
        if not self._check_ready():
            return
        pls = self._build()
        dlg = QDialog(self); dlg.setWindowTitle("Playlist preview"); dlg.resize(820, 600)
        lay = QVBoxLayout(dlg)
        txt = QTextEdit(); txt.setReadOnly(True); txt.setStyleSheet(INPUT_STYLE)
        txt.setPlainText("\n\n".join(f"===== {n}{self.state.profile.extension} ({text.count(chr(10)) // 2} tracks) =====\n"
                                     + "\n".join(text.splitlines()[:41]) + ("\n..." if text.count(chr(10)) > 41 else "")
                                     for n, text in pls.items()))
        lay.addWidget(txt)
        dlg.exec()

    def _save_local(self):
        if not self._check_ready():
            return
        pls = self._build()
        try:
            paths = write_local_copies(self.state.profile, pls, settings.playlist_root(), progress=self.state.log)
        except OSError as e:
            self.state.log(f"ERROR saving copies: {e}"); return
        self.state.log(f"{len(paths)} playlist(s) saved under {settings.playlist_root()}")

    def _deploy(self):
        if not self._check_ready():
            return
        p = self.state.profile
        if p.is_ftp and not self.state.password:
            if QMessageBox.question(self, "No password", "No FTP password entered. Try anyway?") != QMessageBox.StandardButton.Yes:
                return
        pls = self._build()
        targets = "\n".join(p.deploy_dirs)
        if QMessageBox.question(self, "Deploy", f"Write {len(pls)} playlist(s) to {p.name}:\n{targets}\n\n"
                                f"and save copies under {settings.playlist_root()}?") != QMessageBox.StandardButton.Yes:
            return
        self.deploy_btn.setEnabled(False)
        self.state.log(f"Deploying {len(pls)} playlist(s) to {p.name} ...")

        def job(progress=None):
            write_local_copies(p, pls, settings.playlist_root(), progress=progress)
            return deploy(p, pls, self.state.password, progress=progress)

        self.worker = Worker(job)
        self.worker.progress.connect(self.state.log)
        self.worker.finished_ok.connect(self._deploy_done)
        self.worker.failed.connect(self._deploy_failed)
        self.worker.start()

    def _deploy_done(self, results: List[str]):
        self.deploy_btn.setEnabled(True)
        bad = [r for r in results if not r.startswith("OK")]
        self.state.log(f"Deploy finished: {len(results) - len(bad)} OK, {len(bad)} problems.")
        if self.state.profile and not self.state.profile.is_ftp:
            self.state.log("Safely eject the drive, then import the playlists on the player.")

    def _deploy_failed(self, msg: str):
        self.deploy_btn.setEnabled(True)
        self.state.log("ERROR " + msg)
        if "10061" in msg or "refused" in msg.lower():
            self.state.log("Hint: the FTP server stops when the screen locks. Wake the player and deploy again.")

    # ------------------------------------------------------------------ Claude
    def _ask_claude(self):
        unknown = self.state.genre_map.unknown_artists(self.state.tracks)
        if not unknown:
            return
        key = settings.api_key()
        if not key:
            QMessageBox.information(self, "Claude", "Enter an Anthropic API key in Settings (or set ANTHROPIC_API_KEY) first.")
            return
        model = settings.model()
        if QMessageBox.question(self, "Ask Claude", f"Send {len(unknown)} artist names (with sample album titles) to {model} "
                                f"for genre suggestions?") != QMessageBox.StandardButton.Yes:
            return
        self.claude_btn.setEnabled(False)
        self.worker = Worker(classify_with_claude, unknown, key, model)
        self.worker.progress.connect(self.state.log)
        self.worker.finished_ok.connect(self._claude_done)
        self.worker.failed.connect(self._claude_failed)
        self.worker.start()

    def _claude_done(self, mapping: Dict[str, List[str]]):
        self.state.genre_map.remember_claude(mapping)
        placed = {a: g for a, g in mapping.items() if g}
        self.state.log(f"Claude placed {len(placed)} of {len(mapping)} artists. "
                       + "; ".join(f"{a}: {'/'.join(g)}" for a, g in list(placed.items())[:12])
                       + (" ..." if len(placed) > 12 else ""))
        self.state.genres_changed.emit()
        self.claude_btn.setEnabled(True)

    def _claude_failed(self, msg: str):
        self.claude_btn.setEnabled(True)
        self.state.log("ERROR Claude: " + msg)

    def _review_claude(self):
        gm = self.state.genre_map
        if not gm.claude:
            QMessageBox.information(self, "Claude", "No cached Claude answers yet."); return
        dlg = QDialog(self); dlg.setWindowTitle("Claude's genre suggestions"); dlg.resize(560, 500)
        lay = QVBoxLayout(dlg)
        hint = QLabel("Double-click an artist in Library to change its genres; that override wins over Claude's answer.")
        hint.setStyleSheet(LABEL_HINT); hint.setWordWrap(True); lay.addWidget(hint)
        lst = QListWidget(); lst.setStyleSheet(TABLE_STYLE)
        for a, gs in sorted(gm.claude.items()):
            lst.addItem(f"{a}   ->   {', '.join(gs) if gs else '(none)'}")
        lay.addWidget(lst)
        row = QHBoxLayout(); row.addStretch()
        forget = QPushButton("Forget all Claude answers"); forget.setStyleSheet(BUTTON_DANGER_STYLE + SMALL_BTN)

        def _forget():
            gm.remember_claude({k: [] for k in list(gm.claude)})
            gm.claude.clear(); gm.remember_claude({})
            self.state.genres_changed.emit(); dlg.accept()

        forget.clicked.connect(_forget)
        close = QPushButton("Close"); close.setStyleSheet(BUTTON_GHOST_STYLE + SMALL_BTN); close.clicked.connect(dlg.accept)
        row.addWidget(forget); row.addWidget(close); lay.addLayout(row)
        dlg.exec()
