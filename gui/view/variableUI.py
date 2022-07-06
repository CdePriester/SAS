from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication, QFormLayout, QLineEdit, QHBoxLayout, QPushButton, QDoubleSpinBox
import sys


class VariableUI(QWidget):
    """View of the variable UI of the Surrogate Assistance System.

    Should always be started with a controller. Consists of upper part, where information is provided and selected
    variable ranges are given. This is built in _build_info_table(). Lower part consists of two buttons, generated in
    _build_buttons()

    """
    info_boxes: dict[str, QLabel]
    input_boxes: dict[str, QDoubleSpinBox]

    def __init__(self):

        super().__init__()
        self.general_layout = QVBoxLayout()
        self.setWindowTitle(f"Variable inspector")

        self.setLayout(self.general_layout)

        self._build_info_table()
        self._build_buttons()

    def _build_info_table(self):
        info_layout = QFormLayout()

        self.info_boxes = dict()
        self.input_boxes = dict()

        # Add info boxes
        self.info_boxes['UID'] = QLabel('UID for this design variable')
        self.info_boxes['parameter_UID'] = QLabel('UID for corresponding parameter')

        info_layout.addRow('UID:', self.info_boxes['UID'])
        info_layout.addRow('Parameter UID:', self.info_boxes['parameter_UID'])

        # Add input boxes
        self.input_boxes['nominal'] = QDoubleSpinBox()
        self.input_boxes['minimum'] = QDoubleSpinBox()
        self.input_boxes['maximum'] = QDoubleSpinBox()

        range_layout = QFormLayout()
        range_layout.addRow('Min', self.input_boxes['minimum'])
        range_layout.addRow('Max', self.input_boxes['maximum'])

        info_layout.addRow('Nominal value:', self.input_boxes['nominal'])
        info_layout.addRow('Range', range_layout)

        self.general_layout.addLayout(info_layout)

    def _build_buttons(self):
        button_layout = QHBoxLayout()

        self.close_button = QPushButton('Close window')
        self.save_button = QPushButton('Save changes')

        button_layout.addWidget(self.close_button)
        button_layout.addWidget(self.save_button)

        self.general_layout.addLayout(button_layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    varUI = VariableUI()
    varUI.show()
    sys.exit(app.exec_())
