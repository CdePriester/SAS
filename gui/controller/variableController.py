from sas.gui.view.variableUI import VariableUI
from sas.core.variable import Variable


class VariableController:
    variable: Variable
    view: VariableUI

    def __init__(self, variable: Variable):
        self.variable = variable
        self.view = VariableUI()
        self._update_information()
        self.show_window()

    def _update_information(self):
        self.view.info_boxes['UID'].setText(self.variable.uid)
        self.view.info_boxes['parameter_UID'].setText(self.variable.parameter_uid)
        self.view.input_boxes['nominal'].setValue(self.variable.nominal_value)
        self.view.input_boxes['minimum'].setValue(self.variable.minimal_value)
        self.view.input_boxes['maximum'].setValue(self.variable.maximal_value)

    def show_window(self):
        self.view.show()