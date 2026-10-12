"""Context help: gui/help.md rendered in a QTextBrowser, opened at the section for the current view."""
from __future__ import annotations

import os
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QPushButton, QTextBrowser, QVBoxLayout

from gui.theme import NAVY, TEXT_PRIMARY, BORDER

HELP_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "help.md")
_window = None


def _md_to_html(md: str) -> str:
    html, in_list, in_code = [], False, False
    for line in md.splitlines():
        if line.startswith("```"):
            in_code = not in_code
            html.append("<pre>" if in_code else "</pre>")
            continue
        if in_code:
            html.append(line.replace("<", "&lt;"))
            continue
        if line.startswith("- "):
            if not in_list:
                html.append("<ul>"); in_list = True
            html.append(f"<li>{_inline(line[2:])}</li>")
            continue
        if in_list:
            html.append("</ul>"); in_list = False
        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if m:
            lvl = len(m.group(1))
            anchor = re.sub(r"[^a-z0-9]+", "-", m.group(2).lower()).strip("-")
            html.append(f'<h{lvl} id="{anchor}"><a name="{anchor}"></a>{_inline(m.group(2))}</h{lvl}>')
        elif line.strip():
            html.append(f"<p>{_inline(line)}</p>")
    if in_list:
        html.append("</ul>")
    css = (f"body {{ font-family: 'Segoe UI'; font-size: 10pt; color: {TEXT_PRIMARY}; }} "
           f"h1, h2, h3 {{ color: {NAVY}; }} code, pre {{ background: #F3F4F6; border: 1px solid {BORDER}; "
           f"border-radius: 4px; padding: 2px 4px; font-family: 'Cascadia Code', Consolas; }}")
    return f"<html><head><style>{css}</style></head><body>{''.join(html)}</body></html>"


def _inline(s: str) -> str:
    s = s.replace("&", "&amp;").replace("<", "&lt;")
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    return s


class HelpWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PlaylistPilot help")
        self.resize(720, 600)
        lay = QVBoxLayout(self)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        lay.addWidget(self.browser)
        self.reload()

    def reload(self):
        try:
            with open(HELP_FILE, encoding="utf-8") as f:
                self.browser.setHtml(_md_to_html(f.read()))
        except OSError:
            self.browser.setHtml("<p>help.md not found.</p>")

    def show_section(self, section: str):
        self.show()
        self.raise_()
        self.browser.scrollToAnchor(re.sub(r"[^a-z0-9]+", "-", section.lower()).strip("-"))


def make_help_button(section: str, parent=None) -> QPushButton:
    btn = QPushButton("?", parent)
    btn.setFixedSize(24, 24)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setToolTip(f"Help: {section}")
    btn.setStyleSheet(f"""
        QPushButton {{ background-color: #E5E7EB; color: {NAVY}; border: none;
                       border-radius: 12px; font-size: 10pt; font-weight: 700; }}
        QPushButton:hover {{ background-color: #D1D5DB; }}
    """)

    def _open():
        global _window
        if _window is None:
            _window = HelpWindow()
        _window.show_section(section)

    btn.clicked.connect(_open)
    return btn
