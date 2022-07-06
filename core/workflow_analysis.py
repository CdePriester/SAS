from datetime import datetime
from sas.database.db import DB
from sas.core.discipline import Discipline
from matplotlib import pyplot as plt

from typing import Union

import copy
import functools

from statistics import stdev


class WorkflowAnalysis:
    def __init__(self, disciplines: list[Discipline]):
        self.disciplines = disciplines
        self.combined_discipline_analyses = None
        self.runs = []
        self.total_runtime = None
        self.total_points = None  # Total amount of optimization iterations, DoE Samples, etc.
        self.total_combined_discipline_calls = None
        self.scores = None

        self.flattened_runs = None

    def add_timeline(self, run_id: str, timeline: list[dict]):
        self.runs.append(RunAnalysis(run_id=run_id,
                                     timeline=timeline,
                                     disciplines=self.disciplines))

        self.score()

    def remove_timeline(self, run_id: str):
        run = [run for run in self.runs if run.run_id == run_id]
        run = run[0]

        self.runs.remove(run)
        self.score()

    def get_metric(self, metric):
        if not self.total_runtime:
            self._flatten()

        if metric == 'total_runtime':
            return self.total_runtime
        elif metric == 'total_obj_func_calls':
            return self.total_points
        elif metric == 'total_combined_discipline_calls':
            return self.total_combined_discipline_calls

    @property
    def _discipline_look_up(self) -> dict:
        look_up_table = {}
        for discipline_analysis in self.combined_discipline_analyses:
            look_up_table[discipline_analysis.id] = discipline_analysis

        return look_up_table

    def get_discipline_analysis(self, discipline: Union[Discipline, str]) -> 'DisciplineAnalysis':
        if isinstance(discipline, str):
            return self._discipline_look_up[discipline]
        else:
            return self._discipline_look_up[discipline.id]

    def get_discipline_metric(self, discipline: Union[Discipline, str], metric: str):
        if hasattr(self.get_discipline_analysis(discipline), metric):
            return getattr(self.get_discipline_analysis(discipline), metric)
        else:
            raise AssertionError('Not a valid metric is provided')
    def get_discipline_score(self, discipline: Union[Discipline, str]) -> dict:
        if isinstance(discipline, str):
            return self.scores[discipline]
        else:
            return self.scores[discipline.id]

    def score(self):
        """Score the disciplines in the workflow based on their runtimes and execution behavior
        """
        self._flatten()

        scores = {}
        for discipline in self.combined_discipline_analyses:
            score = {'significant_variables': discipline.get_significant_variables(),
                     'normalized_runtime': discipline.total_runtime / self.total_runtime,
                     'normalized_calls': discipline.n_calls / self.total_combined_discipline_calls,
                     'mean_iterations': discipline.n_calls / self.total_points}
            scores[discipline.id] = score

        self.scores = scores

    def _flatten(self):
        """Take all the information stored in the individual runs and disciplines, and combine them into a
        flat structure where all the information can be accessed.
        """
        if self.runs == self.flattened_runs:
            return

        self.combined_discipline_analyses = [DisciplineAnalysis(run_id='WORKFLOW',  # No parent anymore, falls under WF
                                                                discipline=discipline) for discipline in self.disciplines]

        # Combine all the discipline calls into single DisciplineAnalysis objects
        for discipline_analysis in self.combined_discipline_analyses:
            for run in self.runs:
                discipline_analysis.combine(run.get_discipline_analysis(discipline_analysis.id))

        self.total_runtime = sum([run.runtime for run in self.runs])
        self.total_points = sum([run.points for run in self.runs])
        self.runtime_per_point = self.total_runtime/self.total_points

        self.total_combined_discipline_calls = sum([disc.n_calls for disc in self.combined_discipline_analyses])

        self.flattened_runs = copy.deepcopy(self.runs)

class RunAnalysis:
    top_level_driver_components = ['DOE', 'Optimizer']
    nested_driver_components = ['Converger']
    driver_components = top_level_driver_components + nested_driver_components

    def __init__(self, run_id: str, timeline: list[dict], disciplines: list[Discipline]):
        self.run_id = run_id
        self.timeline = timeline

        self.disciplines = disciplines
        self.discipline_analyses = [DisciplineAnalysis(run_id=self.run_id,
                                                       discipline=discipline) for discipline in disciplines]

        self.runtime = None
        self.points = None  # Amount of DoE samples, or amount of objective function calls, etc.
        self.runtime_per_point = None

        self._process_timeline()

    @functools.cached_property
    def _discipline_look_up(self) -> dict:
        look_up_table = {}
        for discipline_analysis in self.discipline_analyses:
            look_up_table[discipline_analysis.id] = discipline_analysis

        return look_up_table

    def get_discipline_analysis(self, discipline: Union[Discipline, str]) -> 'DisciplineAnalysis':
        if isinstance(discipline, str):
            return self._discipline_look_up[discipline]
        else:
            return self._discipline_look_up[discipline.id]

    def _process_timeline(self):
        min_timestamp = None
        max_timestamp = None

        total_timeline_calls = 0
        total_toplevel_calls = 0

        for event in self.timeline:
            if min_timestamp is None or event['start_timestamp'] < min_timestamp:
                min_timestamp = event['start_timestamp']
            if max_timestamp is None or event['start_timestamp'] > max_timestamp:
                max_timestamp = event['start_timestamp']

            component = event['component']

            if component in self.nested_driver_components:
                continue

            if component in self.top_level_driver_components:
                total_toplevel_calls += 1
                continue

            # Add this elapsed time to the specific DisciplineAnalysis object
            self._discipline_look_up[component].add_discipline_call(event['time_spent'].total_seconds())

        self.runtime = (max_timestamp-min_timestamp).total_seconds()
        self.points = total_toplevel_calls
        self.runtime_per_point = self.runtime/self.points
        self.total_timeline_discipline_calls = sum([disc_anal.n_calls for disc_anal in self.discipline_analyses])


class DisciplineAnalysis:
    def __init__(self, run_id: str, discipline: Discipline):
        self.parent_run = run_id
        self.discipline = discipline
        self.id = self.discipline.id

        self.discipline_call_runtimes = []

    def add_discipline_call(self, elapsed_time: float):
        self.discipline_call_runtimes.append(elapsed_time)

    def combine(self, other_analysis: 'DisciplineAnalysis'):
        assert self.id == other_analysis.id, "Please only combine two identical disciplines"
        self.discipline_call_runtimes += other_analysis.discipline_call_runtimes

    def get_significant_variables(self):
        """Method to find significant variables in a discipline. Might be interesting to extend with further metrics

        :return: amount of non-static inputs for discipline
        """
        input_samples, output_samples = self.discipline.get_all_samples()

        n_varying_variables = 0
        for variable in input_samples:
            input_variable = input_samples[variable]
            if not max(input_variable) - min(input_variable) == 0:
                n_varying_variables += 1

        return n_varying_variables

    @property
    def n_calls(self):
        return len(self.discipline_call_runtimes)

    @property
    def min_runtime(self):
        if self.n_calls < 1:
            return None
        else:
            return min(self.discipline_call_runtimes)

    @property
    def max_runtime(self):
        if self.n_calls < 1:
            return None
        else:
            return max(self.discipline_call_runtimes)

    @property
    def min_max_runtime(self):
        return self.max_runtime-self.min_runtime

    @property
    def total_runtime(self):
        if self.n_calls < 1:
            return None
        else:
            return sum(self.discipline_call_runtimes)

    @property
    def mean_runtime(self):
        if self.n_calls < 1:
            return None
        else:
            return self.total_runtime/self.n_calls

    @property
    def std_runtime(self):
        if self.n_calls <= 1:
            return None
        else:
            return stdev(self.discipline_call_runtimes)


class AnalysisVisualizer:
    def __init__(self, workflow_analysis: WorkflowAnalysis):
        self.workflow_analysis = workflow_analysis