from dataclasses import dataclass
from datetime import datetime

from sas.database.db import DB
from sas.pido_interface.pidoInterface import PIDOInterface

from sas.kadmos_interface.cpacs import PortableCpacs

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sas.core.surrogate_model import SurrogateModel
from lxml import etree
from lxml.etree import ElementTree


class DesignCompetence:
    is_surrogate = False

    def __init__(self, kadmos_uid, id, description, command, version, status):
        self.uid = kadmos_uid
        self.id = id
        self.description = description
        self.command = command
        self.version = version
        self.status = status

        self.registered_db = None
        self.uuid = None

        self.input_variables = []
        self.output_variables = []

    def register_to_db(self, database: DB):
        """Register this discipline to a database controller.

        Obtains UUID, which is the key to communicating with the DB.

        :param database: Database object
        :type database: DB
        """
        self.registered_db = database
        self.uuid = database.assert_tool(tool_name=self.id,
                                         kadmos_id=self.uid,
                                         version=self.version,
                                         tool_info={'command': self.command,
                                                    'description': self.description,
                                                    'status': self.status,
                                                    'version': self.version},
                                         inputs=self.input_variables,
                                         outputs=self.output_variables,
                                         comments=None,
                                         sur_model=self.is_surrogate)

    def add_cpacs_sample(self, database: DB, cpacs_in: str, cpacs_out: str, run_id: str, sample_in_run: int):
        # Extract input variables from cpacs
        parser = etree.XMLParser(remove_blank_text=True)
        root_input = ElementTree(file=cpacs_in, parser=parser).getroot()

        input_data = dict()
        # Make assumption that inputs are always floats
        for input_variable in self.input_variables:
            input_data[input_variable] = float(root_input.xpath(input_variable)[0].text)

        root_output = ElementTree(file=cpacs_out, parser=parser).getroot()
        output_data = dict()
        # Make assumption that inputs are always floats
        for output_variable in self.output_variables:
            output_data[output_variable] = float(root_output.xpath(output_variable)[0].text)

        database.add_sample_to_tool(tool_id=self.uuid,
                                    run_id=run_id,
                                    input_data=input_data,
                                    output_data=output_data,
                                    sample_in_run=sample_in_run)


class Discipline(DesignCompetence):
    """Each design competence gets a discipline class"""

    def __init__(self, kadmos_uid, id, description, command, version, status):
        super(Discipline, self).__init__(kadmos_uid, id, description, command, version, status)

        self.registered_db = None  # Keep track of the database that the discipline is registered to
        
        self.hidden_constraints = []

    def add_input_variables(self, list_of_variables: list[str]):
        if not hasattr(self, 'input_variables'):
            self.input_variables = list()
            self.input_variables = list_of_variables
        else:
            self.input_variables += list_of_variables

    def add_output_variables(self, list_of_variables: list[str]):
        if not hasattr(self, 'output_variables'):
            self.output_variables = list()
            self.output_variables = list_of_variables
        else:
            self.output_variables += list_of_variables

    def add_hidden_constraint(self, flags: dict, actions: list[dict], model='default', ignore_in_training=True):
        """Add a hidden constraint to the surrogate model.

        :param flags: dict in the form {'xpathVariable1': value1,
                                        'xpathVariable2': value2}.
                      if these conditions are met, a hidden constraint is broken and the output is considered invalid.
                      Example: flags = {'dataSchema/errorFlags/aero': 1}.
        :param actions: list of actions to take when a prediction encounters a hidden constraint
                        [{'action': 'set_variables_to_value',
                          'xpathVariable1': value1,
                          'xpathVariable2': value2},
                         {'action': 'set_variables_to_value_from_file',
                          'filename': 'cpacs_source_datafile',
                          'variables_to_reset': ['xpathVariable1', 'xpathVariable2', 'xpathVariableN']},
                         {'action': '... TO BE IMPLEMENTED'}]
        :param model: model used to train hidden constraint violation predictor
        :param ignore_in_training: Ignore the samples that produce false output in the training of the normal surrogate
        """
        self.hidden_constraints.append(HiddenConstraint(flags=flags,
                                                        actions=actions,
                                                        model=model,
                                                        ignore_in_training=ignore_in_training))

    def get_non_constant_input_variables(self):
        inputs, outputs = self.registered_db.get_all_samples(tool_id=self.uuid)

        non_constant_vars = []
        for input_var, var_data in inputs.items():
            if not min(var_data)-max(var_data) == 0:
                non_constant_vars.append(input_var)

        return non_constant_vars

    def get_batched_samples(self):
        data = self.registered_db.get_all_samples(tool_id=self.uuid, batched=True)
        return data

    def get_all_samples(self):
        """ Get all samples for the discipline in the registered database

        :return: list of input and output samples, in format {'varN': [sample1, sample2, sampleN], ...}
        """
        inputs, outputs = self.registered_db.get_all_samples(tool_id=self.uuid)

        return inputs, outputs

    def get_mean_of_samples(self):
        inputs, outputs = self.get_all_samples()

        input_means = {}
        output_means = {}

        for input_var in inputs:
            input_means[input_var] = sum(inputs[input_var]) / len(inputs[input_var])

        for output_var in outputs:
            output_means[output_var] = sum(outputs[output_var]) / len(outputs[output_var])

        return input_means, output_means

    @property
    def n_available_samples(self):
        inputs, outputs = self.get_all_samples()
        return len(next(iter(inputs.values())))

@dataclass
class HiddenConstraint:
    """Container class for a hidden constraint. """
    flags: dict
    actions: list[dict]
    model: str
    ignore_in_training: bool = True

    def _add_flag(self, flag):
        self.flags.update(flag)

    def _add_action(self, action):
        self.actions.append(action)

if __name__ == '__main__':
    testCpacs = PortableCpacs(
        cpacs_in=r"C:\Users\Costijn\.sas\RCE_output\unprocessed\D1_877669ce-0f4b-41b6-ae12-4c92975fd3e2\0\Input\CPACS initial\sellar_cpacs_in.xml")

    testCpacs.update_value('/dataSchema/wahed/rendier', 4)