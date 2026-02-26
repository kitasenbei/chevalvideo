"""QApplication main window with sidebar navigation."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from chevalvideo.pages.convert import ConvertPage
from chevalvideo.pages.compress import CompressPage
from chevalvideo.pages.extract_audio import ExtractAudioPage
from chevalvideo.pages.trim import TrimPage
from chevalvideo.pages.resize import ResizePage
from chevalvideo.pages.download import DownloadPage
from chevalvideo.pages.strip_meta import StripMetaPage
from chevalvideo.pages.thumbnail import ThumbnailPage
from chevalvideo.pages.gif import GifPage


PAGES = [
    ("Convert", ConvertPage),
    ("Compress", CompressPage),
    ("Extract Audio", ExtractAudioPage),
    ("Trim", TrimPage),
    ("Resize", ResizePage),
    ("Download", DownloadPage),
    ("Strip Meta", StripMetaPage),
    ("Thumbnail", ThumbnailPage),
    ("GIF", GifPage),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("chevalvideo")
        self.resize(960, 640)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 12, 0, 12)
        sb_layout.setSpacing(0)

        self._stack = QStackedWidget()
        self._nav_buttons: list[QPushButton] = []

        for i, (name, PageClass) in enumerate(PAGES):
            btn = QPushButton(f"  {name}")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._switch(idx))
            sb_layout.addWidget(btn)
            self._nav_buttons.append(btn)

            page = PageClass()
            self._stack.addWidget(page)

        sb_layout.addStretch()
        root.addWidget(sidebar)
        root.addWidget(self._stack, 1)

        self._switch(0)

    def _switch(self, idx: int):
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == idx)
