from PyQt5.QtWidgets import QFileDialog

from sas.core.sas_core import SAS
from sas.gui.view.mainUI import MainUI
from sas.cmdows.cmdowsInterface import CMDOWSInterface

from sas.gui.controller.variableController import VariableController


class MainController:
    """Controller for main GUI"""

    sas: SAS

    cmdows_file_path: str
    cmdows_interface: CMDOWSInterface

    open_design_variable_windows: dict

    def __init__(self, view: MainUI):
        self.view = view

        self._connect_signals()

        self.sas = SAS()

    def _connect_signals(self):
        """Connects all clickable objects to their controlling functions"""
        self.view.cmdows_file_picker_button.clicked.connect(self._cmdows_file_picker)
        self.view.discipline_box.itemClicked.connect(self._discipline_box_clicked)
        self.view.design_var_box.itemClicked.connect(self._design_var_box_clicked)

    def _design_var_box_clicked(self):
        """Variable is clicked in listbox. Open variable dialogue"""
        selected = self.view.design_var_box.selectedItems()

        for sel_var in selected:
            uid = sel_var.text()

            if not hasattr(self, 'open_design_variable_windows'):
                self.open_design_variable_windows = dict()

            # Add new instance of discipline viewer to dict of discipline windows
            if uid not in self.open_design_variable_windows:
                variable = self.sas.get_design_variable(uid=uid)
                self.open_design_variable_windows[uid] = VariableController(variable)

            # Reopen hidden or open new window
            self.open_design_variable_windows[uid].show_window()

        print(f'Clicked design variable box, selected {[x.text() for x in selected]}')

    def _discipline_box_clicked(self):
        selected = self.view.discipline_box.selectedItems()
        print(f'Clicked discipline box, selected {[x.text() for x in selected]}')

    def _cmdows_file_picker(self):
        """Open file dialog and extract filename of CMDOWS file"""
        if hasattr(self, 'cmdows_file_path'):
            init_directory = self.cmdows_file_path
        else:
            init_directory = '../examples'

        file_path = QFileDialog.getOpenFileName(self.view,
                                                directory=init_directory,
                                                caption='Select CMDOWS file of optimization',
                                                filter='*.xml')

        if isinstance(file_path, tuple):
            self.set_cmdows_file(file_path=file_path[0])
        else:
            self.set_cmdows_file(file_path=file_path)

    def set_cmdows_file(self, file_path: str):
        """Initiate a given CMDOWS file based on a path and modify GUI state.

        :param file_path: file_path to existing CMDOWS file.
        :type file_path: str
        """
        self.sas.init_kadmos(cmdows_opt_file=file_path)

        self._update_cmdows_info()

    def _update_cmdows_info(self):
        """Update all cmdows related info"""
        creator = self.sas.cmdows.get_header_info(field='creator')
        architecture = self.sas.cmdows.get_problem_info('mdaoArchitecture')
        converger = self.sas.cmdows.get_problem_info('convergerType')

        self.view.info_boxes['filename'].setText(self.sas.cmdows_file_path)
        self.view.info_boxes['creator'].setText(creator)
        self.view.info_boxes['architecture'].setText(f'{architecture}: {converger}')

        self._update_disciplines_listbox()
        self._update_design_variables_listbox()

    def _update_disciplines_listbox(self):
        self.view.discipline_box.clear()

        available_disciplines = self.sas.cmdows.get_surrogate_candidates()
        self.view.discipline_box.addItems(available_disciplines)

    def _update_design_variables_listbox(self):
        self.view.design_var_box.clear()

        uid = [x.parameter_uid for x in self.sas.design_variables]
        self.view.design_var_box.addItems(uid)  # Add keys of design variables dict to listbox
