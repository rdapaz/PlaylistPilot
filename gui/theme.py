"""Colour tokens and stylesheet constants shared by every view (pyside6-ux design system)."""
from PySide6.QtGui import QFont

NAVY = "#1F3864"
ACCENT = "#4E79A7"
ACCENT_LIGHT = "#A0CBE8"
BG_CARD = "#FFFFFF"
BG_MAIN = "#F5F6FA"
TEXT_PRIMARY = "#1A1A2E"
TEXT_SECONDARY = "#6B7280"
POSITIVE = "#22C55E"
NEGATIVE = "#EF4444"
WARNING = "#F59E0B"
BORDER = "#E5E7EB"


def font_heading(size: int = 16) -> QFont:
    f = QFont("Segoe UI", size)
    f.setWeight(QFont.Weight.DemiBold)
    return f


def font_body(size: int = 10) -> QFont:
    return QFont("Segoe UI", size)


def font_mono(size: int = 9) -> QFont:
    return QFont("Cascadia Code", size)


CARD_STYLE = f"""
    QFrame#card {{
        background-color: {BG_CARD}; color: {TEXT_PRIMARY};
        border: 1px solid {BORDER}; border-radius: 12px;
    }}
    QFrame#card QLabel {{ background: transparent; border: none; }}
"""

BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {NAVY}; color: white; border: none;
        border-radius: 6px; padding: 6px 16px; font-size: 10pt; font-weight: 600;
    }}
    QPushButton:hover {{ background-color: #2B4A8C; }}
    QPushButton:disabled {{ background-color: #9CA3AF; }}
"""

BUTTON_SECONDARY_STYLE = f"""
    QPushButton {{
        background-color: {ACCENT}; color: white; border: none;
        border-radius: 6px; padding: 6px 16px; font-size: 10pt; font-weight: 600;
    }}
    QPushButton:hover {{ background-color: #3A6591; }}
    QPushButton:disabled {{ background-color: #9CA3AF; }}
"""

BUTTON_DANGER_STYLE = f"""
    QPushButton {{
        background-color: {NEGATIVE}; color: white; border: none;
        border-radius: 6px; padding: 6px 16px; font-size: 10pt; font-weight: 600;
    }}
    QPushButton:hover {{ background-color: #DC2626; }}
    QPushButton:disabled {{ background-color: #9CA3AF; }}
"""

BUTTON_GHOST_STYLE = f"""
    QPushButton {{
        background-color: transparent; color: {TEXT_SECONDARY};
        border: 1px solid {BORDER}; border-radius: 6px; padding: 6px 16px; font-size: 10pt;
    }}
    QPushButton:hover {{ background-color: #F3F4F6; }}
"""

SMALL_BTN = "QPushButton { padding: 2px 10px; font-size: 9pt; }"

INPUT_STYLE = f"""
    QLineEdit, QSpinBox, QPlainTextEdit, QTextEdit {{
        border: 1px solid {BORDER}; border-radius: 6px; padding: 6px 10px; font-size: 10pt;
        background-color: white; color: {TEXT_PRIMARY};
    }}
    QLineEdit:focus, QSpinBox:focus, QPlainTextEdit:focus {{ border-color: {NAVY}; }}
"""

COMBO_STYLE = f"""
    QComboBox {{
        border: 1px solid {BORDER}; border-radius: 6px; padding: 6px 10px; font-size: 10pt;
        background-color: white; color: {TEXT_PRIMARY};
    }}
    QComboBox:focus {{ border-color: {NAVY}; }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox QAbstractItemView {{
        background-color: white; color: {TEXT_PRIMARY}; border: 1px solid {BORDER};
        selection-background-color: #E8EDF5; selection-color: {NAVY}; font-size: 10pt; padding: 4px;
    }}
"""

TABLE_STYLE = f"""
    QTableView, QTableWidget, QListWidget, QTreeWidget {{
        border: none; background-color: white; color: {TEXT_PRIMARY};
        alternate-background-color: #F9FAFB; selection-background-color: #E8EDF5;
        selection-color: {NAVY}; font-size: 10pt; gridline-color: transparent;
    }}
    QListWidget {{ border: 1px solid {BORDER}; border-radius: 6px; }}
    QTableView::item, QTableWidget::item, QListWidget::item {{
        padding: 6px 8px; border-bottom: 1px solid #F3F4F6; color: {TEXT_PRIMARY};
    }}
    QHeaderView::section {{
        background-color: #F9FAFB; color: {NAVY}; font-weight: 600; font-size: 10pt; padding: 8px;
        border: none; border-bottom: 2px solid {BORDER};
    }}
"""

CHECK_STYLE = f"QCheckBox {{ color: {TEXT_PRIMARY}; font-size: 10pt; background: transparent; }}"

# Scoped so it does not cascade into every child widget (a bare "background:" on a view does).
VIEW_STYLE = f"QWidget#view {{ background-color: {BG_MAIN}; }}"

# Global stylesheet: every widget type gets an explicit foreground AND background, so nothing falls back to
# the platform palette (Windows dark mode gives white text on our white cards otherwise).
APP_STYLE = f"""
    QWidget {{ color: {TEXT_PRIMARY}; font-family: 'Segoe UI'; }}
    QMainWindow, QDialog, QScrollArea, QStackedWidget, QFileDialog, QMessageBox, QInputDialog {{
        background-color: {BG_MAIN}; color: {TEXT_PRIMARY}; }}
    QLabel {{ color: {TEXT_PRIMARY}; background: transparent; }}
    QCheckBox, QRadioButton {{ color: {TEXT_PRIMARY}; background: transparent; }}
    QCheckBox::indicator, QRadioButton::indicator {{ width: 15px; height: 15px; }}
    QGroupBox {{ color: {NAVY}; background: transparent; }}
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit, QTimeEdit {{
        color: {TEXT_PRIMARY}; background-color: white; selection-background-color: #E8EDF5; selection-color: {NAVY}; }}
    QLineEdit::placeholder {{ color: {TEXT_SECONDARY}; }}
    QComboBox QAbstractItemView, QListView, QTreeView, QTableView, QListWidget, QTreeWidget, QTableWidget {{
        color: {TEXT_PRIMARY}; background-color: white; alternate-background-color: #F9FAFB;
        selection-background-color: #E8EDF5; selection-color: {NAVY}; }}
    QAbstractItemView::item:selected {{ color: {NAVY}; background-color: #E8EDF5; }}
    QHeaderView::section {{ color: {NAVY}; background-color: #F9FAFB; }}
    QTableCornerButton::section {{ background-color: #F9FAFB; border: none; }}
    QPushButton {{ color: {TEXT_PRIMARY}; background-color: #E5E7EB; border: 1px solid {BORDER};
                   border-radius: 6px; padding: 5px 12px; }}
    QPushButton:hover {{ background-color: #D1D5DB; }}
    QPushButton:disabled {{ color: #9CA3AF; }}
    QToolButton {{ color: {TEXT_PRIMARY}; background: transparent; }}
    QToolTip {{ color: {TEXT_PRIMARY}; background-color: #FFFBEB; border: 1px solid {BORDER}; padding: 4px; }}
    QMenu {{ color: {TEXT_PRIMARY}; background-color: white; border: 1px solid {BORDER}; }}
    QMenu::item:selected {{ color: {NAVY}; background-color: #E8EDF5; }}
    QMenuBar, QStatusBar {{ color: {TEXT_PRIMARY}; background-color: {BG_MAIN}; }}
    QTabWidget::pane {{ border: 1px solid {BORDER}; background: white; }}
    QTabBar::tab {{ color: {TEXT_PRIMARY}; background: #E5E7EB; padding: 6px 12px; }}
    QTabBar::tab:selected {{ color: {NAVY}; background: white; }}
    QTextBrowser {{ color: {TEXT_PRIMARY}; background-color: white; }}
    QProgressBar {{ color: {TEXT_PRIMARY}; background-color: white; border: 1px solid {BORDER}; border-radius: 4px; text-align: center; }}
    QProgressBar::chunk {{ background-color: {ACCENT}; }}
    QScrollBar:vertical {{ background: #F3F4F6; width: 12px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: #CBD5E1; border-radius: 6px; min-height: 24px; }}
    QScrollBar:horizontal {{ background: #F3F4F6; height: 12px; margin: 0; }}
    QScrollBar::handle:horizontal {{ background: #CBD5E1; border-radius: 6px; min-width: 24px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QMessageBox QLabel, QFileDialog QLabel, QInputDialog QLabel {{ color: {TEXT_PRIMARY}; }}
    QMessageBox QPushButton, QFileDialog QPushButton {{ min-width: 72px; }}
"""


def apply_theme(app) -> None:
    """Fusion style + explicit light palette + global stylesheet. Call once on the QApplication."""
    from PySide6.QtGui import QColor, QPalette
    from PySide6.QtWidgets import QStyleFactory

    if "Fusion" in QStyleFactory.keys():
        app.setStyle("Fusion")            # ignores the Windows dark-mode theme entirely
    pal = QPalette()
    roles = {
        QPalette.ColorRole.Window: BG_MAIN, QPalette.ColorRole.WindowText: TEXT_PRIMARY,
        QPalette.ColorRole.Base: "#FFFFFF", QPalette.ColorRole.AlternateBase: "#F9FAFB",
        QPalette.ColorRole.Text: TEXT_PRIMARY, QPalette.ColorRole.PlaceholderText: TEXT_SECONDARY,
        QPalette.ColorRole.Button: "#E5E7EB", QPalette.ColorRole.ButtonText: TEXT_PRIMARY,
        QPalette.ColorRole.Highlight: "#E8EDF5", QPalette.ColorRole.HighlightedText: NAVY,
        QPalette.ColorRole.ToolTipBase: "#FFFBEB", QPalette.ColorRole.ToolTipText: TEXT_PRIMARY,
        QPalette.ColorRole.Link: ACCENT, QPalette.ColorRole.BrightText: "#FFFFFF",
        QPalette.ColorRole.Light: "#FFFFFF", QPalette.ColorRole.Midlight: "#F3F4F6",
        QPalette.ColorRole.Mid: "#D1D5DB", QPalette.ColorRole.Dark: "#9CA3AF", QPalette.ColorRole.Shadow: "#6B7280",
    }
    for role, hexcol in roles.items():
        pal.setColor(role, QColor(hexcol))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#9CA3AF"))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#9CA3AF"))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#9CA3AF"))
    app.setPalette(pal)
    app.setStyleSheet(APP_STYLE)
LABEL_HINT = f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent; border: none;"
LABEL_BODY = f"color: {TEXT_PRIMARY}; font-size: 10pt; background: transparent; border: none;"
SECTION_TITLE = f"color: {NAVY}; background: transparent; border: none;"
LOG_STYLE = """
    QPlainTextEdit {
        border: 1px solid #E5E7EB; border-radius: 6px; background: #0F172A; color: #E2E8F0;
        font-family: 'Cascadia Code', Consolas, monospace; font-size: 9pt; padding: 8px;
    }
"""
