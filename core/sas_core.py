import os.path

from sas.core.surrogate_model import SurrogateModel
from sas.core.discipline import Discipline
from sas.core.variable import Variable
from sas.core.workflow_analysis import WorkflowAnalysis
from sas.core.advise import Advisor
from sas.pido_interface.pidoInterface import PIDOInterface
from sas.pido_interface.rceInterface import RCEInterface
from sas.kadmos_interface.kadmos_interface import KadmosInterface
from sas.kadmos_interface.cpacs import PortableCpacs
from sas.database.db import DB

from datetime import datetime
import datetime as dt
import numpy as np
import math
import pickle

from smt import sampling_methods
import numpy as np

from typing import Union


class SAS:
    """Main class of the application. All controlling logic and intra-module connections are handled in this class.

    Should be completely independent of the GUI, but GUI is heavily dependent on this module.
    """
    cmdows_file_path: str

    kadmos: KadmosInterface

    disciplines: list[Discipline]
    design_variables: list[Variable]
    sas_workspace: str

    pido_interface: PIDOInterface
    database: DB

    def __init__(self, sas_workspace: str = None,
                 cmdows_opt_file: str = None,
                 initial_cpacs: str = None,
                 runs_output_location: str = None):

        self._init_sas_workspace(sas_workspace)
        self.database = DB(self.sas_workspace)
        if cmdows_opt_file:
            self.init_kadmos(cmdows_opt_file=cmdows_opt_file)
        self.workflow_analysis = WorkflowAnalysis(disciplines=self.disciplines)

        if initial_cpacs:
            self.initial_cpacs = os.path.abspath(initial_cpacs)
        else:
            self.initial_cpacs = None

        if not runs_output_location:
            self.runs_output_location = os.path.join(self.sas_workspace, 'run_outputs')
        else:
            self.runs_output_location = runs_output_location

        if not os.path.isdir(self.runs_output_location):
            os.makedirs(self.runs_output_location)

        self.surrogate_models = {}

    def init_kadmos(self, cmdows_opt_file: str):
        """Initiate KADMOS using a provided CMDOWS in SAS.

        :param cmdows_opt_file: file_path to existing CMDOWS file.
        :type cmdows_opt_file: str
        """
        try:
            self.kadmos = KadmosInterface(cmdows_opt_file=cmdows_opt_file)
            self.cmdows_file_path = cmdows_opt_file
        except AssertionError as msg:
            print(f'Error occured: {msg}')

        self._extract_design_variables()
        self._extract_disciplines()

    def _init_sas_workspace(self, sas_workspace: str = None):
        """Init a SAS workspace. Currently simply a simple check if folder exists, and creating one if not.

        Will probably be extended to initiate previous settings, run some checks, etc.

        :param sas_workspace: Path to non-default workspace location
        :type sas_workspace: str
        """
        # Make C:\Users\USERNAME\.sas (or similar, home folder for other OS) default for RCE.
        default_workspace = os.path.join(os.path.expanduser('~'), '.sas')

        if not sas_workspace:
            sas_workspace = default_workspace

        if os.path.isdir(sas_workspace):
            self.sas_workspace = sas_workspace
        else:
            os.mkdir(sas_workspace)
            print(f'Initiated SAS workspace directory at {sas_workspace}')

            self.sas_workspace = sas_workspace

    def _extract_disciplines(self):
        """From CMDOWS file extract all disciplines and assign their coupling variables"""
        self.disciplines = self.kadmos.get_disciplines()

        # Assign correct out and input variables to each discipline
        for discipline in self.disciplines:
            discipline.add_input_variables(self.kadmos.get_io_for_discipline(discipline, 'in'))
            discipline.add_output_variables(self.kadmos.get_io_for_discipline(discipline, 'out'))

            discipline.register_to_db(self.database)

    def _extract_design_variables(self):
        """Extract all design variables and assign them to a variable object"""
        self.design_variables = self.kadmos.get_design_variables()

    def deploy_all_disciplines(self, tool_folder: str, **kwargs):
        for discipline in self.disciplines:
            self.pido_interface.deploy_discipline(discipline,
                                                  tool_folder=tool_folder,
                                                  **kwargs)

    def deploy_discipline(self, discipline_uid: str, tool_folder: str, **kwargs):
        self.pido_interface.deploy_discipline(self.get_discipline(discipline_uid),
                                              tool_folder=tool_folder,
                                              **kwargs)

    def get_design_variable(self, uid: str) -> Variable:
        """Get Variable object for UID

        :param uid: UID of parameter
        :type uid: str
        :return: Variable object belonging to UID
        :rtype: Variable
        """
        variable = [var for var in self.design_variables if var.uid == uid or var.parameter_uid == uid]

        assert len(variable) == 1, "Duplicate UID's in design variable list. Should be only one."
        return variable[0]

    def get_discipline(self, uid: str) -> Discipline:
        """Get Discipline object for UID

        :param uid: UID of discipline
        :type uid: str
        :return: Discipline object belonging to UID
        :rtype: Discipline
        """
        discipline = [disc for disc in self.disciplines if disc.uid == uid or disc.id == uid]

        assert len(discipline) == 1, "Duplicate UID's in discipline list. Should be only one."
        return discipline[0]

    def get_tool_ids(self):
        """Get all ID's for the included disciplines/tools in SAS

        :return: list id's of tools included in sas
        """
        return [tool.id for tool in self.disciplines]

    def init_pido(self, pido_path: str = None, test_connection: bool = False, run_file: str = None):
        if pido_path:
            self.pido_interface = RCEInterface(pido_path=pido_path,
                                               test_connection=test_connection,
                                               run_file=run_file)
        else:
            self.pido_interface = RCEInterface(pido_path=r"\Dev\Thesis\rce\rce.exe",
                                               test_connection=test_connection,
                                               run_file=run_file)

        self.pido_interface.set_pido_output(self.sas_workspace)

    def process_run(self, run_id=None, final_storage_base_folder=None):
        """Process either a specific run (if run_uuid is provided) or process all runs that are unprocessed in the DB.

        All process files will be moved to the final_storage_location if provided. If argument is not passed, files will
        not be moved.

        :param run_id: (optional) UUID of run to-be processed. If not provided, all unprocessed runs are processed
        :type run_id: str
        """

        if len(self.surrogate_models) > 0:
            disciplines_to_process = self.disciplines + list(self.surrogate_models.values())
        else:
            disciplines_to_process = self.disciplines

        self.pido_interface.process_results(database=self.database,
                                            disciplines=disciplines_to_process,
                                            final_storage_base_folder=final_storage_base_folder,
                                            run_id=run_id)

    def init_surrogate_model(self, disciplines: Union[str, list[str], tuple[str]]):
        if (isinstance(disciplines, list) or isinstance(disciplines, tuple)) and 'Converger' in disciplines:
            converged = True
        else:
            converged = False

        inputs, outputs = self.kadmos.get_io_for_replaced_disciplines(disciplines, converged=converged,
                                                                      only_non_const=True)
        all_inputs, outputs = self.kadmos.get_io_for_replaced_disciplines(disciplines, converged=converged,
                                                                          only_non_const=False)

        if isinstance(disciplines, str):
            key = tuple([disciplines])

            if key not in self.surrogate_models:
                surrogate_model = SurrogateModel(disciplines=self.get_discipline(disciplines),
                                                 input_variables=inputs,
                                                 output_variables=outputs,
                                                 all_inputs=all_inputs)
                self.surrogate_models[key] = surrogate_model
                surrogate_model.register_to_db(self.database)
            else:
                self.surrogate_models[key].update_data()
        elif isinstance(disciplines, list) or isinstance(disciplines, tuple):
            key = tuple(disciplines)
            if key not in self.surrogate_models:
                surrogate_model = SurrogateModel(
                    disciplines=[self.get_discipline(discipline) for discipline in disciplines if
                                 not discipline == 'Converger'],
                    input_variables=inputs,
                    output_variables=outputs,
                    converged=converged,
                    all_inputs=all_inputs)
                self.surrogate_models[key] = surrogate_model
                surrogate_model.register_to_db(self.database)
            else:
                self.surrogate_models[key].update_data()
        else:
            raise AssertionError('Please provide surrogate model candidates in correct format')

        return key

    def build_surrogate_model(self, disciplines: Union[str, list[str], tuple[str]], **kwargs):
        key = self.init_surrogate_model(disciplines)
        self.surrogate_models[key].build(**kwargs)

        return key

    def build_doe_for_disciplines(self, disciplines: Union[list[str], str], build_dsm=False):
        output_folder = os.path.join(self.sas_workspace, 'CMDOWS')

        doe_file = self.kadmos.build_doe_for_disciplines(disciplines=disciplines, output_location=output_folder,
                                                         build_dsm=build_dsm)
        return doe_file

    def apply_labels_in_graphs(self, labels):
        self.kadmos.apply_labels(labels)

    def deploy_surrogate(self, disciplines: Union[str, list[str], tuple[str]], build_dsm=False, **kwargs):
        key = self.build_surrogate_model(disciplines, **kwargs)
        file_folder = os.path.join(self.sas_workspace, 'surrogate_objects', ''.join(key))

        if not os.path.isdir(file_folder):
            os.makedirs(file_folder)

        timestamp_format = '%Y-%m-%d_%H-%M-%S'
        surrogate_name = f"{datetime.strftime(datetime.now(), timestamp_format)}.pickle"
        file = os.path.join(file_folder, surrogate_name)

        with open(file, 'w+b') as f:
            pickle.dump(self.surrogate_models[key], f)

        new_repo_path = os.path.join(self.sas_workspace, 'tool_repos', ''.join(key))

        self.pido_interface.deploy_discipline_surrogate(surrogate=self.surrogate_models[key],
                                                        pickle_file=file,
                                                        base_location=new_repo_path)

        new_mdg_file = self.kadmos.build_new_opt_files(self.surrogate_models[key], new_repo_path, build_dsm=build_dsm)

        return new_mdg_file

    def run_pido(self, wf_file: str = None, initial_cpacs_file=None, only_use_pido_output_files=False):
        if not self.initial_cpacs and not initial_cpacs_file:
            raise AssertionError('Please provide an initial CPACS file for the desired run')

        if initial_cpacs_file:
            initial_cpacs_to_use = initial_cpacs_file
        else:
            initial_cpacs_to_use = self.initial_cpacs

        time_started = datetime.now() + dt.timedelta(seconds=3)
        status = self.pido_interface.execute_workflow(wf_file,
                                                      input_cpacs=initial_cpacs_to_use,
                                                      run_output_folder=self.runs_output_location
                                                      )

        if not status:
            run_id = self.database.store_run_information(platform='RCE',
                                                         run_start_time=time_started,
                                                         run_file=self.pido_interface.last_run_file)
            self.process_run(run_id=run_id,
                             final_storage_base_folder=os.path.join(self.sas_workspace, 'storage', 'data'))
        else:
            print('Something went wrong. Workflow is not executed. Check settings.')

        self.database.save_databases()

        return run_id

    def execute_surrogate_training(self, disciplines: Union[str, list[str], tuple[str]], wf_file: str, n_samples,
                                   doe_options: dict, surrogate_options: dict):
        sampling_plan = self.generate_samples(n_samples=n_samples, disciplines=disciplines, **doe_options)
        samples_wf_file = self.deploy_samples_into_workflow(wf_file=wf_file, sampling_plan=sampling_plan)

        run_id = self.run_pido(wf_file=samples_wf_file)

        sas.build_surrogate_model(disciplines=disciplines, **surrogate_options)

        return run_id

    def get_surrogate(self, disciplines: Union[str, list[str], tuple[str]]):
        if isinstance(disciplines, str):
            key = tuple([disciplines])
        else:
            key = tuple(disciplines)

        if key in self.surrogate_models:
            return self.surrogate_models[key]
        else:
            raise AssertionError('Surrogate Model does not exist. Run sas.init_surrogate() first.'
                                 '')
    def manually_process_run(self, platform, run_start_time, run_file):
        """ Currently not implemented. RCE does not automatically store the log files when runnning from the GUI.

        :param platform:
        :param run_start_time:
        :param run_file:
        :return:
        """

        implemented = False

        if implemented:
            run_id = self.database.store_run_information(platform='RCE',
                                                         run_start_time=run_start_time,
                                                         run_file=run_file)

            self.process_run(run_id=run_id,
                             final_storage_base_folder=os.path.join(self.sas_workspace, 'storage', 'data'))

    def set_pido_outputs_to_folder(self):
        """Ensure all the run information of the disciplines are being exported to a certain folder"""
        for discipline in self.disciplines:
            self.pido_interface.update_tool_output_location(discipline.uid)

    def generate_doe(self, filename: str, build_dsm=False):
        output_folder = os.path.join(self.sas_workspace, 'CMDOWS')
        self.kadmos.convert_to_doe(output_cmdows_folder=output_folder, output_cmdows_name=filename, n_samples=10,
                                   design_variables=self.design_variables, build_dsm=build_dsm)

        return os.path.join(output_folder, f'{filename}.xml')

    def analyse_run(self, run_id: str):
        run_timeline = self.pido_interface.get_timeline(database=self.database,
                                                        disciplines=self.disciplines,
                                                        run_id=run_id)

        self.workflow_analysis.add_timeline(run_id=run_id,
                                            timeline=run_timeline)

    def give_advise(self, optimization_budget: float, budget_type: str, account_for_profiling: bool = True):
        advisor = Advisor(worklow_analysis=self.workflow_analysis, kadmos=self.kadmos,
                          account_for_profiling=account_for_profiling)

        if budget_type == 'time':
            advisor.set_optimization_time_budget(time=optimization_budget)
        elif budget_type == 'iter':
            advisor.set_optimization_iteration_budget(iterations=int(optimization_budget))
        else:
            raise AssertionError("Please provide either 'time' or 'iter' to budget_type argument")

        candidates = self.kadmos.get_all_possible_surrogates_groups()

        advisor.build_advise(candidates)

        return advisor

    def build_sampling_point_from_cpacs(self, cpacs: str):
        cpacs = PortableCpacs(cpacs_in=cpacs)

        sample_point = {}
        for design_variable in self.design_variables:
            sample_point[design_variable.parameter_uid] = cpacs.get_value(design_variable.parameter_uid)

        return sample_point

    def get_final_cpacs(self, run_id: str):
        cpacs = self.pido_interface.get_final_cpacs(run_id=run_id, database=self.database)
        return cpacs

    def generate_samples(self, n_samples, method='LHS', disciplines: Union[str, list[str]] = None, seed=None,
                         surrogate_model: SurrogateModel = None, append_samples=False, expansion_factor=0,
                         custom_range=None, make_closest=False, criterion='ese'):
        # Generate a DoE for a certain amount of samples, generate a sampling scheme and deploy
        variable_order = []
        ranges = []
        design_var_indices = None

        if not disciplines and not surrogate_model:  # Sampling plan for complete workflow: inputs are design variables
            for design_variable in self.design_variables:
                variable_order.append(design_variable.parameter_uid)
                if custom_range and design_variable in custom_range:
                    ranges.append(custom_range[design_variable])
                    continue
                ranges.append([design_variable.minimal_value, design_variable.maximal_value])
        elif surrogate_model is not None or isinstance(disciplines, list):
            if surrogate_model is None:
                sm_key = self.init_surrogate_model(disciplines=disciplines)
                surrogate_model = self.surrogate_models[sm_key]

            variable_indices = surrogate_model.input_samples_indices
            input_samples = surrogate_model.all_input_samples
            for variable, variable_idx in variable_indices.items():
                variable_order.append(variable)
                if custom_range and variable in custom_range:
                    ranges.append(custom_range[variable])
                    continue
                min_val = min(input_samples[:, variable_idx])
                max_val = max(input_samples[:, variable_idx])
                if max_val - min_val == 0:
                    ranges.append([min_val, max_val])
                else:
                    ranges.append([min_val - expansion_factor * min_val, max_val + expansion_factor * max_val])
        elif isinstance(disciplines, str):  # Sampling plan for single discipline: use io for discipline
            discipline = self.get_discipline(disciplines)
            current_input_samples, outputs = discipline.get_all_samples()

            if len(current_input_samples[next(iter(current_input_samples))]) > 0:
                non_constant_vars = discipline.get_non_constant_input_variables()
            else:
                non_constant_vars = current_input_samples.keys()

            for input_var in current_input_samples:
                if input_var not in non_constant_vars:
                    continue

                variable_order.append(input_var)

                if custom_range and input_var in custom_range:
                    ranges.append(custom_range[input_var])
                    continue

                var_range = [min(current_input_samples[input_var]), max(current_input_samples[input_var])]

                if max(var_range) - min(var_range) == 0:
                    ranges.append([min(var_range),
                                   max(var_range)])
                else:
                    # Apply expansion ratio:
                    ranges.append([min(var_range) - expansion_factor * min(var_range),
                                   max(var_range) + expansion_factor * max(var_range)])

        limits = np.array(ranges)
        if not method == 'nominal':
            if method == 'LHS':
                smt_doe = sampling_methods.LHS(xlimits=limits, random_state=seed, criterion=criterion)
            elif method == 'FullFactorial':
                smt_doe = sampling_methods.FullFactorial(xlimits=limits)
            elif method == 'Random':
                smt_doe = sampling_methods.Random(xlimits=limits)
            else:
                AssertionError('No valid method given to create a design table with')
                return

            if surrogate_model is not None and append_samples:
                smt_samples = smt_doe.expand_lhs(x=surrogate_model.all_input_samples,
                                                 n_points=n_samples,
                                                 method='ese')
                smt_samples = smt_samples[surrogate_model.n_total_samples:, :]
            else:
                smt_samples = smt_doe(n_samples)

            if make_closest:
                smt_samples = self._order_on_closest(smt_samples)

            sampling_plan = {}
            for idx, var in enumerate(variable_order):
                sampling_plan[var] = smt_samples[:, idx].tolist()
        else:
            sampling_plan = {}
            for design_variable in self.design_variables:
                sampling_plan[design_variable.parameter_uid] = [design_variable.nominal_value]

        return sampling_plan

    def _order_on_closest(self, smt_samples):
        idx_samples, n_var = smt_samples.shape
        ordered_samples = np.zeros((idx_samples, n_var))

        available_samples = list(range(0, idx_samples))
        new_order = []

        while len(available_samples) > 0:
            if len(new_order) == 0:
                new_order.append(available_samples.pop(0))
                ordered_samples[0, :] = smt_samples[0, :]

            sample_idx_base = new_order[-1]
            samples_base = np.divide(smt_samples[sample_idx_base], smt_samples[sample_idx_base])
            considered_samples = np.divide(smt_samples[available_samples, :], smt_samples[sample_idx_base])

            difference = considered_samples - samples_base

            distances = np.linalg.norm(considered_samples - samples_base, axis=1)
            min_index = np.argmin(distances)

            new_order.append(available_samples.pop(min_index))
            ordered_samples[len(new_order) - 1, :] = smt_samples[new_order[-1], :]

        return ordered_samples

    def deploy_samples_into_workflow(self,
                                     wf_file,
                                     sampling_plan):

        new_wf_file = self.pido_interface.deploy_custom_design_table_into_workflow(wf_file=wf_file,
                                                                                   samples=sampling_plan)

        return new_wf_file

    def initial_exploratory_run(self, doe_file: str, budget: datetime):
        sampling_plan = self.generate_samples(method='nominal', n_samples=1)
        profile_wf_file = self.deploy_samples_into_workflow(wf_file=doe_file, sampling_plan=sampling_plan)

        print('Running DoE for nominal values to determine amount of runs...')
        run_id = self.run_pido(wf_file=profile_wf_file)
        self.analyse_run(run_id=run_id)
        print('Finished evaluating nominal point.')

        execution_time = self.workflow_analysis.get_metric('total_runtime')

        budget_delta = budget - dt.datetime(1900, 1, 1)
        budget_seconds = budget_delta.total_seconds()

        n_possible_runs = math.floor(budget_seconds / execution_time)
        print(f"Single point execution took {execution_time}s. Budget corresponds to {budget_seconds}s.")
        print(f"Conclusion estimation: {n_possible_runs} runs are possible within budget.")

        return n_possible_runs

    def full_exploratory_run(self, doe_file: str, n_samples: int):
        sampling_plan = self.generate_samples(method='LHS', n_samples=n_samples, seed=1, criterion='center')
        profile_wf_file = self.deploy_samples_into_workflow(wf_file=doe_file, sampling_plan=sampling_plan)
        print('Running exploratory DoE...')
        run_id = self.run_pido(wf_file=profile_wf_file)
        self.analyse_run(run_id=run_id)
        print('Finished exploratory DoE...')
        return


if __name__ == '__main__':
    sas = SAS(
        cmdows_opt_file=r'C:\Dev\Thesis\surrogateassistancesystem\tool_repository\sellar\Graphs\CMDOWS\RCE_prepped.xml',
        cmdows_fpg_file=r'C:\Dev\Thesis\surrogateassistancesystem\tool_repository\sellar\Graphs\CMDOWS\FPG_MDO.xml')

    sas.init_pido()
    sas.set_pido_outputs_to_folder()
    sas.run_pido()
    # sas.replace_discipline_with_surrogate('D1')
