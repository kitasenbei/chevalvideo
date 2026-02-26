import sys
from PyQt6.QtWidgets import QApplication
from chevalvideo.app import MainWindow
from chevalvideo.style import DARK_STYLE


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("chevalvideo")
    app.setStyleSheet(DARK_STYLE)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
