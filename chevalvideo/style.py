"""Bloomberg Terminal theme — black bg, amber/orange text, monospace everything."""

BLACK = "#000000"
BG = "#0a0a0a"
BG_PANEL = "#111111"
BG_CELL = "#1a1a1a"
BORDER = "#333333"
AMBER = "#ff8c00"
AMBER_BRIGHT = "#ffa733"
AMBER_DIM = "#cc7000"
GREEN = "#00cc00"
RED = "#ff3333"
WHITE = "#cccccc"
DIM = "#666666"
BLUE = "#3399ff"

DARK_STYLE = f"""
QWidget {{
    background-color: {BLACK};
    color: {AMBER};
    font-family: "JetBrains Mono", "Fira Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
}}

/* Sidebar */
#sidebar {{
    background-color: {BG};
    border-right: 1px solid {BORDER};
    min-width: 180px;
    max-width: 180px;
}}
#sidebar QPushButton {{
    background: transparent;
    border: none;
    border-left: 2px solid transparent;
    text-align: left;
    padding: 6px 12px;
    font-size: 12px;
    color: {DIM};
    border-radius: 0;
    text-transform: uppercase;
}}
#sidebar QPushButton:hover {{
    background-color: {BG_PANEL};
    color: {AMBER};
    border-left: 2px solid {DIM};
}}
#sidebar QPushButton:checked {{
    background-color: {BG_PANEL};
    color: {AMBER_BRIGHT};
    border-left: 2px solid {AMBER};
    font-weight: bold;
}}

/* Cards / Option Grid */
.OptionCard {{
    background-color: {BG_CELL};
    border: 1px solid {BORDER};
    border-radius: 0;
    padding: 8px;
}}
.OptionCard:hover {{
    border-color: {AMBER_DIM};
    background-color: {BG_PANEL};
}}
.OptionCard[selected="true"] {{
    border-color: {AMBER};
    background-color: {BG_PANEL};
}}

/* Buttons */
QPushButton {{
    background-color: {AMBER};
    color: {BLACK};
    border: none;
    border-radius: 0;
    padding: 6px 16px;
    font-weight: bold;
    font-size: 12px;
    text-transform: uppercase;
}}
QPushButton:hover {{
    background-color: {AMBER_BRIGHT};
}}
QPushButton:pressed {{
    background-color: {AMBER_DIM};
}}
QPushButton:disabled {{
    background-color: {BG_CELL};
    color: {DIM};
}}

/* Inputs */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {BG_CELL};
    border: 1px solid {BORDER};
    border-radius: 0;
    padding: 5px 8px;
    color: {WHITE};
    selection-background-color: {AMBER_DIM};
    selection-color: {BLACK};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {AMBER};
}}

/* Checkbox */
QCheckBox {{
    color: {AMBER};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 12px;
    height: 12px;
    border: 1px solid {BORDER};
    background-color: {BG_CELL};
}}
QCheckBox::indicator:checked {{
    background-color: {AMBER};
    border-color: {AMBER};
}}

/* Progress bar */
QProgressBar {{
    background-color: {BG_CELL};
    border: 1px solid {BORDER};
    border-radius: 0;
    text-align: center;
    color: {AMBER};
    height: 18px;
    font-size: 11px;
}}
QProgressBar::chunk {{
    background-color: {AMBER_DIM};
    border-radius: 0;
}}

/* Log output */
QPlainTextEdit {{
    background-color: {BLACK};
    border: 1px solid {BORDER};
    border-radius: 0;
    padding: 6px;
    font-family: "JetBrains Mono", "Fira Code", "Consolas", "Courier New", monospace;
    font-size: 11px;
    color: {GREEN};
}}

/* Labels */
QLabel {{
    background: transparent;
}}
QLabel#heading {{
    font-size: 16px;
    font-weight: bold;
    color: {AMBER_BRIGHT};
    text-transform: uppercase;
}}
QLabel#subheading {{
    font-size: 11px;
    color: {DIM};
}}

/* Slider */
QSlider::groove:horizontal {{
    background: {BORDER};
    height: 4px;
    border-radius: 0;
}}
QSlider::handle:horizontal {{
    background: {AMBER};
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 0;
}}

/* Scroll bar */
QScrollBar:vertical {{
    background: {BLACK};
    width: 8px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 0;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {BLACK};
    height: 8px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 0;
    min-width: 24px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* Table */
QTableWidget {{
    background-color: {BLACK};
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    border-radius: 0;
    color: {WHITE};
}}
QTableWidget::item {{
    padding: 3px 6px;
    border-bottom: 1px solid {BG_CELL};
}}
QTableWidget::item:selected {{
    background-color: {AMBER_DIM};
    color: {BLACK};
}}
QHeaderView::section {{
    background-color: {BG_CELL};
    color: {AMBER};
    padding: 4px 6px;
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    font-weight: bold;
    text-transform: uppercase;
    font-size: 11px;
}}

/* File drop zone */
FileDropWidget {{
    border: 1px dashed {BORDER};
    border-radius: 0;
}}

/* Group box */
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 0;
    margin-top: 12px;
    padding: 12px 8px 8px 8px;
    font-weight: bold;
    color: {AMBER};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: {AMBER};
}}

/* Scroll area */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}
"""
