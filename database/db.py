import os
import uuid
from datetime import datetime
import json


class DB:
    """Database class that handles the storage of samples. This necessitates the storage of a tool database, and a
    database where all the executed runs are stored. This should enable the data to be tracable and should be straight-
    forward to analyse."""
    timestamp_format = '%Y-%m-%d_%H-%M-%S'

    db_location: str
    data_folder: str

    tool_db: json
    run_db: json

    def __init__(self, sas_workspace_path):
        """Either create or load database files

        :param sas_workspace_path: path to SAS workspace folder. Example C:\\Users\\USERNAME\\.sas
        :type sas_workspace_path: str"""

        self.db_location = os.path.join(sas_workspace_path, 'storage')
        self.data_folder = os.path.join(self.db_location, 'data')

        if not os.path.isdir(self.db_location) or not os.listdir(self.db_location):
            self._initialize_databases()

        self._load_databases()

    def store_run_information(self, platform, run_start_time, run_file, comments=None):
        """Add a run to the database"""
        run = dict()

        run_id = str(uuid.uuid4())
        run['timestamp'] = datetime.strftime(datetime.now(), self.timestamp_format)
        run['run_start_time'] = datetime.strftime(run_start_time, self.timestamp_format)
        run['platform'] = platform
        run['comments'] = comments
        run['processed'] = False
        run['run_file'] = run_file

        self.run_db[run_id] = run
        self._dump_databases()
        return run_id

    def mark_run_as_processed(self, run_id):
        """Mark run as processed"""
        self.run_db[run_id]['processed'] = True

    def get_run_data(self, field, run_id):
        """Get data for a certain run identified by a run_id.

        :param field: data of interest (e.g. 'run_start_time')
        :type field: str
        :param run_id: run_id of run of interest
        :type run_id: str
        """
        if run_id in self.run_db:
            return self.run_db[run_id][field]
        else:
            return None

    def add_tool(self, tool_name, kadmos_id, version, tool_info, inputs, outputs, comments=None, sur_model=False):
        """Add a new tool to the database"""
        entry = dict()

        tool_id = str(uuid.uuid4())
        entry['sur_model'] = sur_model
        entry['tool_name'] = tool_name
        entry['kadmos_id'] = kadmos_id
        entry['version'] = version
        entry['tool_info'] = tool_info
        entry['comments'] = comments
        entry['inputs'] = inputs
        entry['outputs'] = outputs

        self.tool_db[tool_id] = entry
        self._dump_databases()

        # Make new folder for tool. Here design database and other history will be stored
        os.makedirs(os.path.join(self.data_folder, tool_id), exist_ok=True)

        return tool_id

    def get_last_sample_in_run(self, run_id, tool_name):
        current_sample = None
        for sample in self.sample_db.values():
            if sample['run_id'] == run_id and sample['tool_name'] == tool_name:
                if current_sample is None:
                    current_sample = sample
                elif current_sample['sample_in_run'] < sample['sample_in_run']:
                    current_sample = sample

        return current_sample

    def assert_tool(self, tool_name, kadmos_id, version, tool_info, inputs, outputs, comments=None, sur_model=False):
        """Check if tool already exists. If yes, return uuid of entry. If not, enter in database and return new uuid."""
        for tool_id, tool in self.tool_db.items():
            if tool['kadmos_id'] == kadmos_id and tool['version'] == version and tool['sur_model'] == sur_model:
                print(f'{kadmos_id} using version {version} already in DB.')
                return tool_id

        return self.add_tool(tool_name=tool_name,
                             kadmos_id=kadmos_id,
                             version=version,
                             tool_info=tool_info,
                             inputs=inputs,
                             outputs=outputs,
                             comments=comments,
                             sur_model=sur_model)

    def add_sample_to_tool(self, tool_id, run_id, input_data, output_data, sample_in_run, check_duplicate=True):
        if tool_id in self.tool_db:
            tool_name = self.tool_db[tool_id]['tool_name']
        else:
            tool_name = ''

        sample = dict()
        sample_id = str(uuid.uuid4())
        sample['tool_id'] = tool_id
        sample['tool_name'] = tool_name
        sample['run_id'] = run_id
        sample['input'] = input_data
        sample['output'] = output_data
        sample['sample_in_run'] = sample_in_run
        sample['hash'] = hash(str(input_data | output_data))  # Use to quickly check uniqueness of sample

        if check_duplicate:
            for existing_sample in self.sample_db.values():
                if sample['hash'] == existing_sample['hash']:
                    print(f"Identical sample for {tool_name} is already in database. Sample skipped")
                    return

        self.sample_db[sample_id] = sample
        return sample

    def get_all_samples(self, tool_id: str, batched=False):
        """ Get all the samples from the database for a certain tool_id.

        Extracts the data and puts it in list/array format, grouped for input and output and variable. Structure:
        input: ['inVariable1': list, 'inVariableN': list]
        output: ['outVariable1': list, 'outVariableM': list]

        If the 'batched' mode is activated, the data gets returned grouped on run_id and sample_in_run.
        data = [runId][sample_in_run]{'input': {'inVariableN': float, ...}
                                      'output': {'outVariableN': float, ...}}

        :param tool_id: uuid of tool in database
        :type tool_id: str
        :param batched: Switch to 'batch' data per run and sample number, changes output dict
        :return: input and output dictionaries containing all samples for specified tool
        :rtype: [dict, dict]
        """
        inputs = dict()
        outputs = dict()

        assert tool_id in self.tool_db, "Invalid tool_id provided"

        tool = self.tool_db[tool_id]
        for input_variable in tool['inputs']:
            inputs[input_variable] = list()

        for output_variable in tool['outputs']:
            outputs[output_variable] = list()

        if batched:
            data = {}
            for sample in self.sample_db.values():
                if not sample['tool_id'] == tool_id:
                    continue

                if sample['run_id'] not in data:
                    data[sample['run_id']] = {}

                data[sample['run_id']][sample['sample_in_run']] = {}

                input = {}
                for variable in inputs:
                    input[variable] = sample['input'][variable]
                output = {}
                for variable in outputs:
                    output[variable] = sample['output'][variable]
                data[sample['run_id']][sample['sample_in_run']]['input'] = input
                data[sample['run_id']][sample['sample_in_run']]['output'] = output

            return data
        else:
            for sample in self.sample_db.values():
                if sample['tool_id'] == tool_id:
                    input_data = sample['input']
                    for variable in input_data:
                        inputs[variable].append(input_data[variable])

                    output_data = sample['output']
                    for variable in output_data:
                        outputs[variable].append(output_data[variable])

            return inputs, outputs

    def delete_runs(self, run_ids):
        [self.delete_run(run_id) for run_id in run_ids]

    def delete_run(self, run_id):
        self.run_db.pop(run_id)

        samples_to_pop = []
        for key, sample in self.sample_db.items():
            if sample['run_id'] == run_id:
                samples_to_pop.append(key)

        for key in samples_to_pop:
            self.sample_db.pop(key)

        self.save_databases()

    def save_databases(self):
        self._dump_databases()

    @property
    def tool_db_path(self):
        tool_db_file = 'tool_db.json'
        return os.path.join(self.db_location, tool_db_file)

    @property
    def run_db_path(self):
        run_db_file = 'run_db.json'
        return os.path.join(self.db_location, run_db_file)

    @property
    def sample_db_path(self):
        sample_db_file = 'sample_db.json'
        return os.path.join(self.db_location, sample_db_file)

    def _initialize_databases(self):
        if not os.path.isdir(self.db_location):
            os.mkdir(self.db_location)
            os.mkdir(self.data_folder)

        with open(self.tool_db_path, 'w') as f:
            f.write('{}')

        with open(self.run_db_path, 'w') as f:
            f.write('{}')

        with open(self.sample_db_path, 'w') as f:
            f.write('{}')

    def _load_databases(self):
        with open(self.tool_db_path, 'r') as f:
            self.tool_db = json.load(f)

        with open(self.run_db_path, 'r') as f:
            self.run_db = json.load(f)

        with open(self.sample_db_path, 'r') as f:
            self.sample_db = json.load(f)

    def _dump_databases(self):
        with open(self.tool_db_path, 'w') as f:
            json.dump(self.tool_db, f, indent=4)

        with open(self.run_db_path, 'w') as f:
            json.dump(self.run_db, f, indent=4)

        with open(self.sample_db_path, 'w') as f:
            json.dump(self.sample_db, f, indent=4)


if __name__ == '__main__':
    db = DB(sas_workspace_path=r"C:\Users\Costijn\.sas")
