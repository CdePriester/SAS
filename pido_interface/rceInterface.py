import json

from .pidoInterface import PIDOInterface

from sas.database.db import DB

from datetime import datetime
import os
import re
import shutil
import distutils.dir_util

from sas.core.discipline import Discipline


class RCEInterface(PIDOInterface):
    """Handles interfacing with RCE. Follows parent PIDOInterface class"""
    pido_path: str

    rce_workspace: str
    output_location: str

    processing_directory: str

    wf_file: str

    def __init__(self, pido_path: str,
                 rce_workspace_path: str = None,
                 test_connection: bool = False,
                 run_file: str = False):

        self.pido_path = pido_path

        if rce_workspace_path:
            self.rce_workspace = rce_workspace_path
        else:
            default_workspace = os.path.join(os.path.expanduser('~'), '.rce', 'default')
            self.rce_workspace = default_workspace
            print(f'Default workspace at location {default_workspace} is selected.')

        if test_connection:
            self.test_pido_connection()

        if run_file is not None:
            self.wf_file = run_file

    def test_pido_connection(self):
        """
        Checks if RCE can startup. Immediatly shuts down afterwards.


        :return: Successfully made connection. True if success, false if failed
        :rtype: bool
        """
        command_string = '''shutdown'''
        status = os.system(fr"{self.pido_path} --headless --exec \"{command_string}\" -console")

        if status:
            return False
        else:
            return True

    def deploy_discipline_surrogate(self, surrogate, pickle_file, base_location):
        """Deploy a tool to RCE. Build JSON file and places it in workspace directory.

        Main idea is to use this for surrogate model deployment

        - Require and check definition of rce workspace location
        - Maybe some template json CPACS tool file? Fill in the important blanks
        - Place in workspace folder

        """
        file_location = os.path.dirname(os.path.abspath(__file__))
        new_repo_path = base_location
        # Init folder structure
        surrogate_name = surrogate.uid

        # Use ID of discipline for this repository instead of UUID from database, because of usability
        if not os.path.isdir(new_repo_path):
            os.makedirs(new_repo_path)

        cpacs_in_foldername = "cpacs_in"
        cpacs_out_foldername = "cpacs_out"

        cpacs_in_folder = os.path.join(new_repo_path, cpacs_in_foldername)
        cpacs_out_folder = os.path.join(new_repo_path, cpacs_out_foldername)

        if not os.path.isdir(cpacs_in_folder):
            os.mkdir(cpacs_in_folder)

        if not os.path.isdir(cpacs_out_folder):
            os.mkdir(cpacs_out_folder)

        new_pickle_file = os.path.join(new_repo_path, f'{surrogate_name}.pickle')
        shutil.copyfile(pickle_file, new_pickle_file)

        surrogate_execution_script = os.path.join(file_location, '../', 'resources/executeSurrogatedDiscipline.py')
        script_file = os.path.join(new_repo_path, f'executeSurrogate{surrogate_name}.py')
        shutil.copyfile(surrogate_execution_script, script_file)

        # RCE needs mapping files to select the required inputs for a certain tool
        input_mapping_filename = 'mappingInput.xml'
        output_mapping_filename = 'mappingOutput.xml'

        input_mapping_file = os.path.join(new_repo_path, input_mapping_filename)
        output_mapping_file = os.path.join(new_repo_path, output_mapping_filename)

        self._build_mapping_file(surrogate.input_variables, input_mapping_file)
        self._build_mapping_file(surrogate.output_variables, output_mapping_file)

        # Build configuration parameters such as the command string to execute the script
        # First venv needs to be activated, otherwise module are likely not installed
        venv_path = os.path.join(os.environ['VIRTUAL_ENV'], 'Scripts', 'activate.bat')

        cmd_str = f"""call "{venv_path}"\n\r"""

        cpacs_in_filename = 'cpacs_in.xml'
        cpacs_out_filename = 'cpacs_out.xml'

        cpacs_in_file = os.path.join(r"${dir:tool}", cpacs_in_foldername, cpacs_in_filename)
        cpacs_out_file = os.path.join(r"${dir:tool}", cpacs_out_foldername, cpacs_out_filename)

        cmd_str += rf"""python "{script_file}" -s "{pickle_file}" -i "{cpacs_in_file}" -o "{cpacs_out_file}" """

        # Create config file for new tool using template
        template_file = os.path.join(file_location, 'resources/rce_cpacs_tool/configuration.json')
        with open(template_file) as f:
            config = json.load(f)

        config['toolName'] = surrogate_name
        config['commandScriptWindows'] = cmd_str
        config['deleteWorkingDirectoriesAfterWorkflowExeuction'] = False
        config['deleteWorkingDirectoriesNever'] = True

        # Naming of these i/o connections is dynamic, but defined in the config
        for input in config['inputs']:
            if input['endpointName'] == config['cpacsInitialEndpointName']:
                print('found it')

        for output in config['outputs']:
            if output['endpointName'] == config['cpacsOutgoingEndpointName']:
                print('found it')

        config['launchSettings'][0]['rootWorkingDirectory'] = self.output_location
        config['launchSettings'][0]['toolDirectory'] = new_repo_path

        # Version has to be a float converted to a string!!
        config['launchSettings'][0]['version'] = str(1.0)

        config['mappingInputFilename'] = input_mapping_filename
        config['mappingOutputFilename'] = output_mapping_filename

        # Maybe create tool description?
        timestamp_format = '%Y-%m-%d_%H-%M-%S'

        description_text = f"Surrogate Model generated by SAS. \r\n"
        description_text += f"Build at {datetime.strftime(datetime.now(), timestamp_format)}. \r\n"
        description_text += surrogate.write_text_report()

        config['toolDescription'] = description_text

        config['toolInputFileName'] = os.path.join(cpacs_in_foldername, cpacs_in_filename)
        config['toolOutputFilename'] = os.path.join(cpacs_out_foldername, cpacs_out_filename)

        # Store old config file and documentation in RCE_backup folder. The config file for the surrogate in RCE_new
        timestamp_format = '%Y-%m-%d_%H-%M-%S'

        backup_path = os.path.join(new_repo_path, 'RCE_backup',
                                   f"{datetime.strftime(datetime.now(), timestamp_format)}")
        new_path = os.path.join(new_repo_path, 'RCE_new')

        if not os.path.isdir(backup_path):
            os.makedirs(backup_path)

        if not os.path.isdir(new_path):
            os.makedirs(new_path)

        configuration_file = os.path.join(new_path, 'configuration.json')
        doc_folder = os.path.join(new_path, 'docs')

        # Write configuration.json and create empty "documentation folder"
        with open(configuration_file, 'w') as f:
            json.dump(config, f, indent=4)
        if not os.path.isdir(doc_folder):
            os.mkdir(doc_folder)

        # old_tool_location = self._find_tool_location(tool_id=discipline.id)

        '''
        # Move old configuration to backup folder
        shutil.move(src=old_tool_location,
                    dst=backup_path)
        '''
        # Copy the new tool configuration to the RCE repository
        tool_folder = os.path.join(self.rce_workspace, 'integration', 'tools', 'cpacs', surrogate_name)
        distutils.dir_util.copy_tree(src=new_path,
                                     dst=tool_folder)

    def deploy_discipline(self,
                          discipline: Discipline,
                          tool_folder: str,
                          tool_output_folder: str = None,
                          cpacs_input_folder='cpacs_in',
                          cpacs_input_file='cpacs_in.xml',
                          cpacs_output_folder='cpacs_out',
                          cpacs_output_file='cpacs_out.xml',
                          overwrite=False):

        rce_deployed_folder = os.path.join(self.rce_workspace, 'integration', 'tools', 'cpacs', discipline.id)

        if os.path.isdir(rce_deployed_folder):
            if not overwrite:
                print(f'There is already a tool deployed under the same name. Skipping deployment of {discipline.id}.')
                return
        else:
            os.mkdir(rce_deployed_folder)

        current_path = os.path.dirname(os.path.abspath(__file__))

        template_configuration_folder = os.path.join(current_path, 'resources/RCE_cpacs_tool')
        template_file = os.path.join(template_configuration_folder, 'configuration.json')

        with open(template_file) as f:
            config = json.load(f)

        config['toolName'] = discipline.id
        config['commandScriptWindows'] = discipline.command
        config['deleteWorkingDirectoriesAfterWorkflowExeuction'] = False
        config['deleteWorkingDirectoriesNever'] = True

        config['launchSettings'][0]['rootWorkingDirectory'] = self.output_location
        config['launchSettings'][0]['toolDirectory'] = tool_folder

        config['launchSettings'][0]['version'] = str(discipline.version)

        mapping_folder = f'mapping'
        input_mapping_file = os.path.join(mapping_folder, f'{discipline.id}-mapping-input.xml')
        output_mapping_file = os.path.join(mapping_folder, f'{discipline.id}-mapping-output.xml')

        self._build_mapping_file(discipline.input_variables, os.path.join(tool_folder, input_mapping_file))
        self._build_mapping_file(discipline.output_variables, os.path.join(tool_folder, output_mapping_file))

        config['mappingInputFilename'] = input_mapping_file
        config['mappingOutputFilename'] = output_mapping_file

        config['toolInputFileName'] = os.path.join(cpacs_input_folder, cpacs_input_file)
        config['toolOutputFilename'] = os.path.join(cpacs_output_folder, cpacs_output_file)

        # Write configuration.json and create empty "documentation folder"
        configuration_file = os.path.join(rce_deployed_folder, 'configuration.json')
        with open(configuration_file, 'w') as f:
            json.dump(config, f, indent=4)

        doc_folder = os.path.join(rce_deployed_folder, 'docs')
        if not os.path.isdir(doc_folder):
            os.mkdir(doc_folder)

    def set_pido_output(self, location: str):
        self.output_location = os.path.join(location, 'RCE_output', 'unprocessed')

        if not os.path.isdir(self.output_location):
            os.makedirs(self.output_location)
            print(f'Folder {self.output_location} did not exist, so it was created.')

    def update_tool_output_location(self, tool_id: str):
        """Change output location of tool's runtime information to specified folder"""

        fixed_tool_folder = os.path.join(self.rce_workspace, 'integration', 'tools', 'cpacs', tool_id)
        configuration_file = os.path.join(fixed_tool_folder, 'configuration.json')

        with open(configuration_file, 'r') as f:
            config = json.load(f)

        config['launchSettings'][0]['rootWorkingDirectory'] = self.output_location
        config['deleteWorkingDirectoriesAfterWorkflowExecution'] = False
        config['deleteWorkingDirectoriesNever'] = True
        config['useIterationDirectories'] = True

        with open(configuration_file, 'w') as f:
            json.dump(config, f, indent=4)

    def connect_run_to_output(self):
        """The log files generated in the same folder as the .wf file contains the information to find the correct
        run information for a certain .wf execution. each tool has format:

        'rceOutputFolder/TOOLNAME_UUID/...'. UUID has following regexp: ([a-f0-9]{8}(-[a-f0-9]{4}){4}[a-f0-9]{8}).
        Fully described in /log file. Should be enough to connect the dots and find the correct data for the creation
        of the surrogates.
        """
        pass

    def execute_workflow(self, wf_file, input_cpacs=None, run_output_folder=None):
        """Execute an RCE workflow file .wf using the RCE command line interface.

        See RCE pdf manual for shell commands. Tested using RCE 8.2.2.201805301316

        :param input_cpacs:
        :param wf_file: path to workflow (.wf) file
        :type wf_file: str
        """
        if wf_file is not None:
            self.wf_file = wf_file

        assert self.wf_file is not None, "Please provide a run file for the execution of the workflow"

        placeholder_file = self._build_placeholder(wf_file=self.wf_file,
                                                   input_cpacs=input_cpacs,
                                                   run_output_folder=run_output_folder)

        command_string = fr"wf run --delete never -p {placeholder_file} {self.wf_file}"
        command = f"{self.pido_path} --headless --batch \"{command_string}\" -consoleLog"

        status = os.system(command)

        # log_file = self._find_corresponding_log(time_started)

        return status

    @property
    def last_run_file(self):
        return self.wf_file

    def _find_corresponding_log(self, time_started: datetime, wf_file: str):
        """ Simulation creates a log file that contains useful information. This function finds and returns the log-file
        that has been generated by the workflow execution and returns its path.


        :param time_started: starttime of the workflow execution. Will find log created closest to this time
        :type time_started: datetime
        :return: path to corresponding .log file
        :rtype: str
        """
        # Eventueel beter om die time_started te gebruiken
        logs_folder = os.path.join(os.path.dirname(wf_file), 'logs')
        logs_content = os.listdir(logs_folder)

        # Specific RCE format for date and time numeration of their log files
        # Example folder name: sellar_full_try_2022-01-10_14-29-33-289_1
        date_regex = "[0-9]{4}-[0-9]{2}-[0-9]{2}"
        time_regex = "[0-9]{2}-[0-9]{2}-[0-9]{2}-"

        times_delta = list()
        for log_folder in logs_content:
            date = re.findall(date_regex, log_folder)[0]
            time = re.findall(time_regex, log_folder)[0][:-1]

            date_corrected = datetime.strptime(date, '%Y-%m-%d')
            time_corrected = datetime.strptime(time, '%H-%M-%S').time()

            # Store the difference to the start time of the workflow execution
            times_delta.append(abs(time_started - datetime.combine(date_corrected, time_corrected)))

        # Sort folder containing logs based on calculated times_delta list. Select the smallest
        logs_sorted = [x for _, x in sorted(zip(times_delta, logs_content))]

        return os.path.join(logs_folder, logs_sorted[0], 'workflow.log')

    @staticmethod
    def _process_log_file(log_file):
        """ Function to parse provided .log file from RCE and find UUID's from used tool instances.

        Can be used to match certain tool output folders to a run. Might be extended with other functionalities.

        :param log_file: file path to RCE generated log file
        :type log_file: str
        :return: set with UUID's if available
        :rtype: set
        """
        with open(log_file, 'r') as f:
            lines = f.readlines()

        uuid_pattern = "([a-f0-9]{8}(?:-[a-f0-9]{4}){4}[a-f0-9]{8})"
        uuids = set()  # Only store unique UUIDs in file -> use set
        for line in lines:
            matches = re.findall(uuid_pattern, line)
            if len(matches) > 0:
                uuids.add(matches[0])

        return uuids

    def _find_tool_location(self, tool_id: str):
        """Find the path of a tool with tool_id in the current RCE CPACS workspace.

        :param tool_id: tool_id of the to-be-found tool
        :type tool_id: str
        :return: absolute path of the tool
        :rtype: str
        """
        tool_folder = os.path.join(self.rce_workspace, 'integration', 'tools', 'cpacs')
        tools_content = os.listdir(tool_folder)

        for tool in tools_content:
            if tool_id in tool:
                return os.path.join(tool_folder, tool)
        else:
            return None

    def check_tool_naming_consistency(self, tool_ids):
        """Check whether all provided tools are deployed in RCE.

        Tools in RCE are deployed in the workspace space folder: RCE_WORKSPACE/integration/tools/cpacs. This check is
        needed to make sure the system is able to find and replace the tools in the RCE repository with surrogate
        models.

        :param tool_ids: List of kadmos id's of tools
        :type tool_ids: list[str]
        :returns: Result of check (true: naming is consistent. False: naming inconsistent/tools are not deployed)
        :rtype: bool
        """

        tool_folder = os.path.join(self.rce_workspace, 'integration', 'tools', 'cpacs')
        tools_content = os.listdir(tool_folder)

        non_deployed = list()
        for tool_id in tool_ids:
            if tool_id not in tools_content:
                non_deployed.append((tool_id))

        if not len(non_deployed) == 0:
            print(f"Not all tools seem to be deployed! Missing tools {non_deployed}")
            return False
        else:
            return True

    def get_final_cpacs(self, run_id: str, database):
        run_start_time = database.get_run_data(field='run_start_time', run_id=run_id)
        run_file = database.get_run_data(field='run_file', run_id=run_id)

        run_log_file = self._find_corresponding_log(time_started=datetime.strptime(run_start_time,
                                                                                   database.timestamp_format),
                                                    wf_file=run_file)

        with open(run_log_file, 'r') as f:
            lines = f.readlines()

        # We want to find last occurence of the output coordinator and the file he wrote. Therefore: reverse list:
        lines.reverse()
        filepath_re = r'(\/.*?\.[\w:]+)'

        for line in lines:
            if "Coordinator-in" in line and "Wrote file" in line:
                path = line.split(" ")[-1].strip()

                return path

    def process_results(self, database, disciplines, final_storage_base_folder=None, run_id=None):
        """ Select the runs that need to be processed.

        If run_id is provided, this run will be processed. If not provided, all non-processed runs in the database
        will be processed.

        If final_storage_base_folder is filled in, all files will be moved to that location

        :param database: database object
        :param disciplines: list of discipline objects
        :param final_storage_base_folder: location where files will be saved indefinitely
        :param run_id: uuid of run for identification in databases
        :param only_use_pido_output_files:
        """
        if run_id is not None:
            self._process_run(database, disciplines, run_id)
        else:
            # TODO: process all runs that have tag 'unprocessed' in the run-database
            print('To be implemented')
        if final_storage_base_folder is not None:
            self._cleanup_files(disciplines, final_storage_base_folder, run_id)

    def _process_run(self, database: DB, disciplines, run_id):
        """ Process the generated files by RCE and make them usable for the design database and SAS.

        RCE stores the folder information in a specified location, and uses format disciplineID_CertainUUID
        The correct foldernames can be determined by reading out the log. This happens in the _process_log_file function
        Using these uuids, the results for the specific run can be extracted from the output folder

        Function has following structure:

        1. Determine uuids (and therefore foldernames) for the output folders for this run for each tool and match
        2. Move all folders to a processing folder and change folder names
        3. For each tool, loop over all its executions and find its input and output files.
        4. The found combination of input/output files are inserted in the database using the discipline object

        :param database: database object
        :param disciplines: list with discipline objects
        :param run_id: uuid of run for identification in databases
        """
        run_start_time = database.get_run_data(field='run_start_time', run_id=run_id)
        run_file = database.get_run_data(field='run_file', run_id=run_id)

        run_log_file = self._find_corresponding_log(time_started=datetime.strptime(run_start_time,
                                                                                   database.timestamp_format),
                                                    wf_file=run_file)
        folder_uuids_from_log = self._process_log_file(run_log_file)

        output_folder_contents = os.listdir(self.output_location)

        # Extract the folders that will be processed from the 'unprocessed' folder based on uuids from log
        folders_to_copy = list()
        uuid_pattern = "([a-f0-9]{8}(?:-[a-f0-9]{4}){4}[a-f0-9]{8})"
        for folder_name in output_folder_contents:
            uuid = re.findall(uuid_pattern, folder_name)

            if len(uuid) > 0 and uuid[0] in folder_uuids_from_log:
                folders_to_copy.append(folder_name)

        assert len(folders_to_copy) == len(folder_uuids_from_log),\
            "Not all uuids from log have been found in output. Most likely, RCE failed executing. Please ensure other RCE instances are closed! "

        # Copy all folders to the processing folder/run_id folder and remove RCE specific UUIDs from folder names
        run_processing_folder = os.path.join(self.processing_directory, run_id)
        for folder_to_copy in folders_to_copy:
            new_folder_name = re.sub(f"_{uuid_pattern}", "", folder_to_copy)

            shutil.copytree(src=os.path.join(self.output_location, folder_to_copy),
                            dst=os.path.join(run_processing_folder, new_folder_name))

            try:
                shutil.rmtree(os.path.join(self.output_location, folder_to_copy))
            except OSError as e:
                print("Error: %s : %s" % (os.path.join(self.output_location, folder_to_copy), e.strerror))

        # Loop over all copied tool folders, extract the input and output files for each run and process the cpacs files
        for discipline_id in os.listdir(run_processing_folder):  # Folders now have same name as disciplines
            # Find corresponding discipline object from list of disciplines
            discipline = [discipline for discipline in disciplines if discipline.id == discipline_id]
            assert len(discipline) == 1, f"Multiple disciplines {discipline_id} found with same ID. Should not be possible."
            discipline = discipline[0]

            discipline_run_folder = os.path.join(run_processing_folder, discipline_id)

            # Enter folder, recurse over all the runs
            runs = os.listdir(discipline_run_folder)
            for idx_sample, run in enumerate(runs):
                if not run.isdigit():
                    continue

                input_file = self.find_file_type_in_folders(root_path=os.path.join(discipline_run_folder, run, "Input"),
                                                            extension='.xml')
                assert len(input_file) == 1, f"Multiple input files found for discipline {discipline_id} and run {run}."
                input_file = input_file[0]

                output_file = self.find_file_type_in_folders(
                    root_path=os.path.join(discipline_run_folder, run, "Output"),
                    extension='.xml')
                assert len(
                    output_file) == 1, f"Multiple output files found for discipline {discipline_id} and run {run}."
                output_file = output_file[0]

                discipline.add_cpacs_sample(database=database,
                                            cpacs_in=input_file,
                                            cpacs_out=output_file,
                                            run_id=run_id,
                                            sample_in_run=int(run))

        database.mark_run_as_processed(run_id)

    def _cleanup_files(self, disciplines, final_storage_base_folder, run_id):
        """Move all folders to a location where they will indefinitely be stored.

        Folder structure of final_storage_base_folder will be:

        final_storage_base_folder\tool_id\run_id\..

        :param disciplines: List of disciplines objects
        :param final_storage_base_folder: base folder from where the data will be stored
        :param run_id: uuid to identify run in databases

        """
        run_folder = os.path.join(self.processing_directory, run_id)
        run_folder_contents = os.listdir(run_folder)

        for discipline_id in run_folder_contents:  # Folders have same name as disciplines

            # Find corresponding discipline object from list of disciplines
            discipline = [discipline for discipline in disciplines if discipline.id == discipline_id]
            assert len(discipline) == 1, "Multiple disciplines found with same ID. Should not be possible."
            discipline = discipline[0]

            destination_path = os.path.join(final_storage_base_folder, discipline.uuid, run_id)

            current_folder = os.path.join(run_folder, discipline_id)

            shutil.move(current_folder, destination_path)

        os.rmdir(run_folder)

    def get_timeline(self, database: DB, disciplines: list[Discipline], run_id):
        self.wf_file = database.get_run_data(field='run_file', run_id=run_id)
        run_timestamp = database.get_run_data(field='run_start_time', run_id=run_id)
        run_log_file = self._find_corresponding_log(datetime.strptime(run_timestamp, database.timestamp_format),
                                                    self.wf_file)

        return self._build_timeline_from_log(log_file=run_log_file, disciplines=disciplines)

    @staticmethod
    def _build_placeholder(wf_file: str, input_cpacs: str, run_output_folder: str):
        """ RCE needs a placeholder file to run along with a wf_file. The file defines the:
            - Python execution path
            - Input CPACS file
            - Output location

        :param wf_file:
        """
        placeholder_config = {}

        python_path = os.path.join(os.environ['VIRTUAL_ENV'], 'Scripts', 'python.exe')
        placeholder_config["de.rcenvironment.script/3.4"] = {'pythonExecutionPath': python_path}

        with open(wf_file, 'r') as f:
            wf_config = json.load(f)

        for node in wf_config['nodes']:
            if node['component']['identifier'] == 'de.rcenvironment.outputwriter':
                version = node['component']['version']

                placeholder_config[f'de.rcenvironment.outputwriter/{version}'] = {'targetRootFolder': run_output_folder}
            if node['component']['identifier'] == 'de.rcenvironment.inputprovider':
                version = node['component']['version']
                output_var_name = node['dynamicOutputs'][0]['name']

                placeholder_config[f'de.rcenvironment.inputprovider/{version}'] = {output_var_name: input_cpacs}

        wf_folder = os.path.dirname(wf_file)

        placeholder_file = os.path.join(wf_folder, 'placeholder.json')
        with open(placeholder_file, "w") as f:
            json.dump(placeholder_config, f, indent=4)

        return placeholder_file

    def deploy_custom_design_table_into_workflow(self, wf_file: str, samples: dict):
        ''' Workaround: Inserts custom design table into existing DOE workflow (.wf) file

        CMDOWS files cannot directly be loaded into RCE. Therefore, it is not possible to change custom DOE settings
        on the fly, which is needed to analyse some workflow specifics. If it becomes possible to directly load and
        execute CMDOWS files in RCE, this function can be replaced by something far more general.

        :param wf_file: path to .wf file
        :param samples: dictionary containing sample list. Format {'Variable name': [sample1, sample2, ..., sampleN]}
        :return:
        '''
        with open(wf_file, 'r') as file:
            wf_config = json.load(file)

        for node in wf_config['nodes']:
            if node['name'] == 'DOE':
                doe_config = node
                break
        else:
            AssertionError('Provided workflow is not a DOE')
            return

        doe_config['configuration']['method'] = 'Custom design table'
        # assert doe_config['configuration']['method'] == 'Custom design table', \
        #    "Please input workflow that uses the Custom Design Table method"

        for var in samples:
            if not isinstance(samples[var], list):
                samples[var] = [samples[var]]

        # Find amount of samples used. Extract first key and use the length of first design vector for length
        n_samples = len(samples[next(iter(samples))])

        # RCE uses different variable order for their design table, extract:
        rce_variable_order = [var['name'] for var in doe_config['dynamicOutputs'] if var['name'] in samples]

        # And build table in correct format (full string). Probably neater way to do this, but this seems to work
        rce_sample_table = "["
        for idx in range(0, n_samples):
            sample_table_row = "["
            for var in rce_variable_order:
                sample_table_row += f'"{samples[var][idx]}",'
            sample_table_row = sample_table_row[:-1]
            sample_table_row += "],"
            rce_sample_table += sample_table_row
        rce_sample_table = rce_sample_table[:-1]
        rce_sample_table += "]"

        # Modify configuration and insert table
        doe_config['configuration']['runNumber'] = str(n_samples)
        doe_config['configuration']['table'] = str(rce_sample_table)
        doe_config['configuration']['endSample'] = str(n_samples - 1)

        wf_name = os.path.splitext(wf_file)[0]
        new_wf_name = f"{wf_name}_customTable_N_{n_samples}.wf"

        with open(new_wf_name, 'w') as f:
            json.dump(wf_config, f, indent=4)

        return new_wf_name

    @staticmethod
    def _build_timeline_from_log(log_file: str, disciplines: list[Discipline]):
        """ Process a given log_file and extract the timeline of the executed workflow

        Captures each event of interest (driver calls, discipline calls, etc.) and extract its start and end time

        :param log_file: Log file to be parsed into a workflow timeline
        :param disciplines: List of disciplines from the workflow
        :return: timeline of workflow
        :rtype: list[dict]
        """

        rce_log_timestamp_format = '%Y-%m-%d-%H:%M:%S,%f'
        timeline = []
        driver_components = ['DOE', 'Optimizer', 'Converger']
        discipline_ids = [disc.id for disc in disciplines]

        with open(log_file, 'r') as f:
            log_messages = f.readlines()

        active_disciplines = {}  # Track disciplines currently being executed. Can be multiple due to multithreading
        for log_message in log_messages:
            # Extract and prepare information from log statement
            # TODO Can cause problem if there is a nested square bracket such as D[1]. Outer bracket is not taken into account
            log_parts = re.findall(r'\[.*?\]', log_message)

            timestamp_raw = log_parts[0][1:-1]
            timestamp = datetime.strptime(timestamp_raw, rce_log_timestamp_format)

            log_type = log_parts[1][1:-1]

            component_raw = log_parts[2]  # Keep for extracting message later
            component = component_raw[1:-1]

            # Message is part coming from the component to end of line
            message_start_idx = log_message.rfind(component_raw) + len(component_raw)
            message = log_message[message_start_idx:-1].strip()

            if component in driver_components and 'COMPONENT_LOG_FINISHED' in message:
                driver_instance_id = int(message.split(':')[-1])
                timeline.append(dict(component=component,
                                     start_timestamp=timestamp,
                                     id=driver_instance_id))

            if component in driver_components and 'COMPONENT_TERMINATED' in message and timeline[-1][
                'component'] == component:
                # RCE writes an extra driver output at the end of the analysis, which messes up the results
                timeline.pop(-1)

            if component in discipline_ids and 'TOOL_STARTING' in message:
                tool_instance_id = int(message.split(':')[-1])
                active_disciplines[tool_instance_id] = timestamp

            if component in discipline_ids and 'TOOL_FINISHED' in message:
                tool_instance_id = int(message.split(':')[-1])

                start_timestamp = active_disciplines[tool_instance_id]

                timeline.append(dict(component=component,
                                     start_timestamp=start_timestamp,
                                     end_timestamp=timestamp,
                                     time_spent=timestamp - start_timestamp,
                                     id=tool_instance_id))

                active_disciplines.pop(tool_instance_id)

        return timeline

    def find_file_type_in_folders(self, root_path, extension):
        """ Execute a recursive search for all files with provided extension in folder structure. Returns all files
        with the extension in the root_path folder and its subfolders


        :param root_path: initial search folder
        :type root_path: str
        :param extension: extension to search for. For example '.xml', 'xml' or '.csv'
        :type extension: str
        :return: list with files found
        :rtype: list
        """

        contents = os.listdir(root_path)

        files = list()
        for content in contents:
            full_path = os.path.join(root_path, content)
            if os.path.isfile(full_path) and content.endswith(extension):
                files.append(full_path)

            if os.path.isdir(full_path):
                # Go one level deeper. If results are found, extend the files list
                files += self.find_file_type_in_folders(full_path, extension)

        return files

    @staticmethod
    def _build_mapping_file(variables, filepath):
        header = '<?xml version="1.0" encoding="UTF-8"?>\n' \
                 '<map:mappings xmlns:map="http://www.dlr.de/sistec/tiva/tool/mapping" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">\n'
        footer = '</map:mappings>'

        content = ''
        for input_variable in variables:
            content += '<map:mapping>\n'
            content += f'    <map:source>{input_variable}</map:source>\n'
            content += f'    <map:target>{input_variable}</map:target>\n'
            content += '</map:mapping>\n'

        output = header + content + footer

        if not os.path.isdir(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))

        with open(filepath, 'w+') as f:
            f.write(output)

    @property
    def processing_directory(self):
        return os.path.abspath(os.path.join(self.output_location, "..", "processing"))


class LogParser:
    def __init__(self, log_file: str):
        self.log_file = log_file


if __name__ == '__main__':
    rce_path = r"\Dev\Thesis\rce\rce.exe"

    # rce --headless --exec "wf run --delete never -p "C:\Users\Costijn\.rce\default\workspace\sellar_full_try\placeholder.json" "C:\Users\Costijn\.rce\default\workspace\sellar_full_try\sellar_full_try.wf"" -console

    interface = RCEInterface(pido_path=rce_path)
    # interface.test_pido_connection()

    interface.deploy_tool()
    interface.set_output_location('D1', r"\Dev\Thesis\rce_out_temp")
