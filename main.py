"""PlaylistPilot: build and deploy playlists for portable music players."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.main_window import MainWindow  # noqa: E402
from gui.state import AppState  # noqa: E402
from gui.theme import apply_theme, font_body  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PlaylistPilot")
    app.setOrganizationName("ricdeez")
    app.setFont(font_body(10))
    apply_theme(app)
    state = AppState()
    win = MainWindow(state)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
