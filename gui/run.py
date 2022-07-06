from PyQt5.QtWidgets import QApplication
import sys
from view.mainUI import MainUI
from controller.mainController import MainController


def main():
    app = QApplication(sys.argv)

    view = MainUI()
    controller = MainController(view=view)
    view.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
