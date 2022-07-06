import sys

from PyQt5.QtWidgets import QFormLayout,QMainWindow, QApplication, QPushButton, QVBoxLayout, QHBoxLayout, QListWidget, QWidget, QLabel


class MainUI(QMainWindow):
    """The UI of the main window of the Surrogate Assistance System GUI.

    Class itself contains no logic, only the view. GUI currently split-up in an upper- and lower section.
    Upper section contains CMDOWS info, listing of disciplines and design variables. Lower section contains buttons to interact with. First draft, but extra functionality
    can be added using a menu bar.
    """
    def __init__(self):
        # Initialize empty window
        super().__init__()
        self._centralWidget = QWidget(self)
        self.setCentralWidget(self._centralWidget)
        self.setWindowTitle('Surrogate Assistance System')

        # Built up of lower- and upper section, therefore Vertical (QVBox) layout is used
        self.general_layout = QVBoxLayout()
        self._centralWidget.setLayout(self.general_layout)

        # Fill up layout and add
        self._build_upper_layout()
        self._build_lower_layout()
        self.general_layout.addLayout(self.upper_layout)

    def _build_upper_layout(self):
        self.upper_layout = QHBoxLayout()

        # Build the three upper sections
        self._build_cmdows_info()
        self._build_disciplines_box()
        self._build_design_variables_box()

        self.general_layout.addLayout(self.upper_layout)

    def _build_cmdows_info(self):
        cmdows_info_layout = QVBoxLayout()

        # Build the CMDOWS file picker button
        self.cmdows_file_picker_button = QPushButton('Select CMDOWS File')
        cmdows_info_layout.addWidget(self.cmdows_file_picker_button)

        # Build information section
        info_description_layout = QFormLayout()

        self.info_boxes = dict()

        self.info_boxes['filename'] = QLabel('Selected CMDOWS File before continuing')
        self.info_boxes['creator'] = QLabel('Creator of the CMDOWS file')
        self.info_boxes['architecture'] = QLabel('Selected architecture for optimization')
        self.info_boxes['connected_pido'] = QLabel('Selected and verified PIDO')
        self.info_boxes['system_valid'] = QLabel('Overall verification of system')

        info_description_layout.addRow('Selected CMDOWS File:', self.info_boxes['filename'])
        info_description_layout.addRow('Creator:', self.info_boxes['creator'])
        info_description_layout.addRow('Architecture:', self.info_boxes['architecture'])
        info_description_layout.addRow('Connected PIDO:', self.info_boxes['connected_pido'])
        info_description_layout.addRow('Valid?:', self.info_boxes['system_valid'])

        cmdows_info_layout.addLayout(info_description_layout)

        # Build the PIDO Setup button
        self.pido_options_button = QPushButton('PIDO Setup')
        cmdows_info_layout.addWidget(self.pido_options_button)

        self.upper_layout.addLayout(cmdows_info_layout)

    def _build_disciplines_box(self):
        discipline_layout = QVBoxLayout()

        discipline_layout.addWidget(QLabel('Available Disciplines:'))

        self.discipline_box = QListWidget()

        self.discipline_box.addItem('Select CMDOWS file to continue...')

        discipline_layout.addWidget(self.discipline_box)

        self.upper_layout.addLayout(discipline_layout)

    def _build_design_variables_box(self):
        design_var_layout = QVBoxLayout()

        design_var_layout.addWidget(QLabel('Design Variables:'))

        self.design_var_box = QListWidget()

        self.design_var_box.addItem('Select CMDOWS file to continue...')

        design_var_layout.addWidget(self.design_var_box)

        self.upper_layout.addLayout(design_var_layout)

    def _build_lower_layout(self):
        lower_button_layout = QHBoxLayout()

        self.sur_options_button = QPushButton('Surrogate Options')
        self.design_database_button = QPushButton('Design Database')
        self.vistoms_viewer_button = QPushButton('View in VISTOMS')
        self.run_optim_button = QPushButton('Run Optimization')

        lower_button_layout.addWidget(self.sur_options_button)
        lower_button_layout.addWidget(self.design_database_button)
        lower_button_layout.addWidget(self.vistoms_viewer_button)
        lower_button_layout.addWidget(self.run_optim_button)

        self.general_layout.addLayout(lower_button_layout)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    view = MainUI()
    view.show()
    sys.exit(app.exec_())
