"""Add / edit a device profile: connection, volumes (label -> playlist prefix), deploy folders, format."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QSpinBox, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from core.profiles import DeviceProfile, Volume, FTP_GUIDE, USB_GUIDE
from gui.theme import (BUTTON_GHOST_STYLE, BUTTON_SECONDARY_STYLE, BUTTON_STYLE, CHECK_STYLE, COMBO_STYLE,
                       INPUT_STYLE, LABEL_HINT, SMALL_BTN, TABLE_STYLE)


class ProfileDialog(QDialog):
    def __init__(self, profile: DeviceProfile | None = None, existing_names=(), parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit device" if profile else "Add device")
        self.setMinimumWidth(640)
        self._existing = set(existing_names)
        self._original = profile
        p = profile or DeviceProfile(name="", kind="ftp", port=2100, guidance=FTP_GUIDE)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        form = QFormLayout()
        form.setSpacing(10)

        self.name = QLineEdit(p.name); self.name.setStyleSheet(INPUT_STYLE)
        self.name.setReadOnly(bool(profile and profile.builtin))
        form.addRow("Name:", self.name)

        self.kind = QComboBox(); self.kind.setStyleSheet(COMBO_STYLE)
        self.kind.addItems(["ftp", "usb"]); self.kind.setCurrentText(p.kind)
        self.kind.currentTextChanged.connect(self._kind_changed)
        form.addRow("Connection:", self.kind)

        self.host = QLineEdit(p.host); self.host.setStyleSheet(INPUT_STYLE); self.host.setPlaceholderText("192.168.1.100")
        self.port = QSpinBox(); self.port.setRange(1, 65535); self.port.setValue(p.port); self.port.setStyleSheet(INPUT_STYLE)
        self.user = QLineEdit(p.user); self.user.setStyleSheet(INPUT_STYLE)
        form.addRow("Host / IP:", self.host)
        form.addRow("Port:", self.port)
        form.addRow("Username:", self.user)

        root_row = QHBoxLayout()
        self.usb_root = QLineEdit(p.usb_root); self.usb_root.setStyleSheet(INPUT_STYLE); self.usb_root.setPlaceholderText("D:\\")
        root_row.addWidget(self.usb_root)
        browse = QPushButton("Browse..."); browse.setStyleSheet(BUTTON_SECONDARY_STYLE + SMALL_BTN)
        browse.clicked.connect(self._browse_root)
        root_row.addWidget(browse)
        form.addRow("Drive root:", root_row)

        self.separator = QComboBox(); self.separator.setStyleSheet(COMBO_STYLE)
        self.separator.addItems(["/", "\\"]); self.separator.setCurrentText(p.separator)
        self.extension = QComboBox(); self.extension.setStyleSheet(COMBO_STYLE)
        self.extension.addItems([".m3u8", ".m3u"]); self.extension.setCurrentText(p.extension)
        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("separator")); fmt_row.addWidget(self.separator)
        fmt_row.addSpacing(12); fmt_row.addWidget(QLabel("extension")); fmt_row.addWidget(self.extension); fmt_row.addStretch()
        form.addRow("Playlist format:", fmt_row)

        self.decode = QCheckBox("FTP lists non-ASCII names percent-encoded (iPhone): decode before use")
        self.decode.setStyleSheet(CHECK_STYLE); self.decode.setChecked(p.decode_percent)
        form.addRow("", self.decode)
        lay.addLayout(form)

        hint = QLabel("Volumes: the folder label as the player exposes it, and the prefix a playlist entry needs "
                      "in front of the path below it. Leave the prefix empty for paths relative to the playlist's own folder.")
        hint.setWordWrap(True); hint.setStyleSheet(LABEL_HINT)
        lay.addWidget(hint)
        self.volumes = QTableWidget(0, 2); self.volumes.setStyleSheet(TABLE_STYLE)
        self.volumes.setHorizontalHeaderLabels(["Folder label", "Playlist prefix"])
        self.volumes.horizontalHeader().setStretchLastSection(True)
        self.volumes.setColumnWidth(0, 260)
        for v in p.volumes:
            self._add_volume_row(v.label, v.prefix)
        lay.addWidget(self.volumes)
        vb = QHBoxLayout()
        add_v = QPushButton("Add volume"); add_v.setStyleSheet(BUTTON_SECONDARY_STYLE + SMALL_BTN); add_v.clicked.connect(lambda: self._add_volume_row("", ""))
        rm_v = QPushButton("Remove selected"); rm_v.setStyleSheet(BUTTON_GHOST_STYLE + SMALL_BTN); rm_v.clicked.connect(self._remove_volume)
        vb.addWidget(add_v); vb.addWidget(rm_v); vb.addStretch()
        lay.addLayout(vb)

        self.deploy = QLineEdit("; ".join(p.deploy_dirs)); self.deploy.setStyleSheet(INPUT_STYLE)
        self.deploy.setPlaceholderText("/music on SD card; /foobar2000 Music Folder   or   _explaylist_data")
        f2 = QFormLayout(); f2.addRow("Deploy folders (; separated):", self.deploy)
        self.guidance = QPlainTextEdit(p.guidance); self.guidance.setStyleSheet(INPUT_STYLE); self.guidance.setFixedHeight(110)
        f2.addRow("Guidance shown to user:", self.guidance)
        lay.addLayout(f2)

        btns = QHBoxLayout(); btns.addStretch()
        cancel = QPushButton("Cancel"); cancel.setStyleSheet(BUTTON_GHOST_STYLE); cancel.clicked.connect(self.reject)
        save = QPushButton("Save"); save.setStyleSheet(BUTTON_STYLE); save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self._validate_and_accept)
        btns.addWidget(cancel); btns.addWidget(save)
        lay.addLayout(btns)
        self._kind_changed(p.kind)

    def _kind_changed(self, kind: str):
        ftp = kind == "ftp"
        for w in (self.host, self.port, self.user):
            w.setEnabled(ftp)
        self.usb_root.setEnabled(not ftp)
        if not self._original and not self.guidance.toPlainText().strip():
            self.guidance.setPlainText(FTP_GUIDE if ftp else USB_GUIDE)

    def _browse_root(self):
        path = QFileDialog.getExistingDirectory(self, "Select the player's drive root", self.usb_root.text() or "C:\\")
        if path:
            self.usb_root.setText(path.replace("/", "\\") + ("\\" if not path.endswith(("/", "\\")) else ""))

    def _add_volume_row(self, label: str, prefix: str):
        r = self.volumes.rowCount(); self.volumes.insertRow(r)
        self.volumes.setItem(r, 0, QTableWidgetItem(label)); self.volumes.setItem(r, 1, QTableWidgetItem(prefix))

    def _remove_volume(self):
        for idx in sorted({i.row() for i in self.volumes.selectedIndexes()}, reverse=True):
            self.volumes.removeRow(idx)

    def _validate_and_accept(self):
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Name is required."); return
        if not self._original and name in self._existing:
            QMessageBox.warning(self, "Validation", "A device with that name already exists."); return
        if self.kind.currentText() == "ftp" and not self.host.text().strip():
            QMessageBox.warning(self, "Validation", "Host / IP is required for an FTP device."); return
        if self.kind.currentText() == "usb" and not self.usb_root.text().strip():
            QMessageBox.warning(self, "Validation", "Drive root is required for a USB device."); return
        if self.volumes.rowCount() == 0:
            QMessageBox.warning(self, "Validation", "Add at least one volume."); return
        self.accept()

    def result_profile(self) -> DeviceProfile:
        vols = []
        for r in range(self.volumes.rowCount()):
            lab = (self.volumes.item(r, 0).text() if self.volumes.item(r, 0) else "").strip()
            pre = (self.volumes.item(r, 1).text() if self.volumes.item(r, 1) else "").strip()
            if lab:
                vols.append(Volume(lab, pre))
        base = self._original
        return DeviceProfile(
            name=self.name.text().strip(), kind=self.kind.currentText(), host=self.host.text().strip(),
            port=self.port.value(), user=self.user.text().strip(), usb_root=self.usb_root.text().strip(),
            volumes=vols, deploy_dirs=[d.strip() for d in self.deploy.text().split(";") if d.strip()],
            separator=self.separator.currentText(), extension=self.extension.currentText(),
            decode_percent=self.decode.isChecked(), skip_dirs=base.skip_dirs if base else DeviceProfile(name="x").skip_dirs,
            guidance=self.guidance.toPlainText(), builtin=bool(base and base.builtin),
        )
