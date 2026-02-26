"""Dark theme QSS — Dracula-ish palette."""

BG = "#282a36"
BG_LIGHT = "#343746"
BG_LIGHTER = "#44475a"
FG = "#f8f8f2"
CYAN = "#8be9fd"
GREEN = "#50fa7b"
ORANGE = "#ffb86c"
PINK = "#ff79c6"
PURPLE = "#bd93f9"
RED = "#ff5555"
YELLOW = "#f1fa8c"
COMMENT = "#6272a4"

DARK_STYLE = f"""
QWidget {{
    background-color: {BG};
    color: {FG};
    font-family: "Inter", "Segoe UI", "Helvetica Neue", sans-serif;
    font-size: 13px;
}}

/* Sidebar */
#sidebar {{
    background-color: {BG_LIGHT};
    min-width: 200px;
    max-width: 200px;
}}
#sidebar QPushButton {{
    background: transparent;
    border: none;
    text-align: left;
    padding: 10px 16px;
    font-size: 13px;
    color: {COMMENT};
    border-radius: 0;
}}
#sidebar QPushButton:hover {{
    background-color: {BG_LIGHTER};
    color: {FG};
}}
#sidebar QPushButton:checked {{
    background-color: {BG_LIGHTER};
    color: {PURPLE};
    font-weight: bold;
}}

/* Cards / Option Grid */
.OptionCard {{
    background-color: {BG_LIGHT};
    border: 2px solid transparent;
    border-radius: 8px;
    padding: 12px;
}}
.OptionCard:hover {{
    border-color: {COMMENT};
}}
.OptionCard[selected="true"] {{
    border-color: {PURPLE};
    background-color: {BG_LIGHTER};
}}

/* Buttons */
QPushButton {{
    background-color: {PURPLE};
    color: {BG};
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: bold;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: #caa4fa;
}}
QPushButton:pressed {{
    background-color: #a87af5;
}}
QPushButton:disabled {{
    background-color: {BG_LIGHTER};
    color: {COMMENT};
}}

/* Inputs */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {BG_LIGHT};
    border: 1px solid {BG_LIGHTER};
    border-radius: 6px;
    padding: 6px 10px;
    color: {FG};
    selection-background-color: {PURPLE};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {PURPLE};
}}

/* Progress bar */
QProgressBar {{
    background-color: {BG_LIGHT};
    border: none;
    border-radius: 4px;
    text-align: center;
    color: {FG};
    height: 22px;
}}
QProgressBar::chunk {{
    background-color: {PURPLE};
    border-radius: 4px;
}}

/* Log output */
QPlainTextEdit {{
    background-color: {BG_LIGHT};
    border: 1px solid {BG_LIGHTER};
    border-radius: 6px;
    padding: 8px;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    font-size: 12px;
    color: {GREEN};
}}

/* Labels */
QLabel {{
    background: transparent;
}}
QLabel#heading {{
    font-size: 20px;
    font-weight: bold;
    color: {FG};
}}
QLabel#subheading {{
    font-size: 13px;
    color: {COMMENT};
}}

/* Slider */
QSlider::groove:horizontal {{
    background: {BG_LIGHTER};
    height: 6px;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {PURPLE};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}

/* Scroll bar */
QScrollBar:vertical {{
    background: {BG};
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: {BG_LIGHTER};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* Table */
QTableWidget {{
    background-color: {BG_LIGHT};
    gridline-color: {BG_LIGHTER};
    border: 1px solid {BG_LIGHTER};
    border-radius: 6px;
}}
QTableWidget::item {{
    padding: 4px 8px;
}}
QTableWidget::item:selected {{
    background-color: {PURPLE};
    color: {BG};
}}
QHeaderView::section {{
    background-color: {BG_LIGHTER};
    color: {FG};
    padding: 6px;
    border: none;
    font-weight: bold;
}}
"""
