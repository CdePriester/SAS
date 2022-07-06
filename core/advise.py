from sas.core.workflow_analysis import WorkflowAnalysis
from tkinter.filedialog import askopenfilename, askdirectory
from datetime import datetime
import math
import os.path
from typing import Union
from sas.kadmos_interface.kadmos_interface import KadmosInterface
import pandas as pd

from matplotlib import pyplot as plt


class Advisor:
    sample_advisors = {'jia': lambda n_var: (n_var + 1) * (n_var + 2),
                       'kaufman': lambda n_var: 3 / 4 * (n_var + 1) * (n_var + 2),
                       'jones': lambda n_var: 10 * n_var}

    default_advisor = 'jones'
    default_profile = 'advised'

    # Factors for the sample advise
    profiles = {'efficient': 0.5,
                'advised': 1.0,
                'conservative': 1.2}

    t_sur = 1  # Cost in seconds of a surrogate model prediction

    def __init__(self, worklow_analysis: WorkflowAnalysis, kadmos: KadmosInterface, account_for_profiling=False):
        self.sample_advisor = self.sample_advisors[self.default_advisor]
        self.profile = self.profiles[self.default_profile]

        self.account_for_profiling = account_for_profiling

        self.kadmos = kadmos

        self.workflow_analysis = worklow_analysis
        self.workflow_analysis.score()

        self.disciplines = self.workflow_analysis.disciplines

        self.opt_time_budget = None  # Optimization budget in seconds
        self.opt_iteration_budget = None  # Optimization budget in iterations (points)

        self._fixed = ''  # Switch to determine which parameter will be leading. Either 'time' or 'iter'

        self.strategies = {}

    def get_goal(self):
        return self._fixed

    def set_sample_advisor(self, sample_advisor):
        assert sample_advisor in self.sample_advisors, "Please provide an implemented sample advisor."
        self.sample_advisor = self.sample_advisors[sample_advisor]

    def set_profile(self, profile):
        assert profile in self.profiles, "Please provide a valid profile."
        self.profile = self.profiles[profile]

    def set_optimization_time_budget(self, time: float):
        self._fixed = 'time'
        self.opt_time_budget = time
        self.opt_iteration_budget = math.floor(time / self.workflow_analysis.runtime_per_point)

    def set_optimization_iteration_budget(self, iterations: int):
        self._fixed = 'iter'
        self.opt_iteration_budget = iterations
        self.opt_time_budget = iterations * self.workflow_analysis.runtime_per_point

    def get_discipline(self, uid):
        discipline = [disc for disc in self.disciplines if disc.uid == uid or disc.id == uid]

        assert len(discipline) == 1, "Duplicate UID's in discipline list. Should be only one."
        return discipline[0]

    def analyze_strategies(self, candidates: list[tuple]):
        strategies = {}
        t_wf_original = self.workflow_analysis.runtime_per_point
        for candidate in candidates:
            combined_normalized_runtime = 0
            combined_training_time = 0
            n_var = 0
            expected_iter = math.inf
            currently_available_samples = None

            if 'Converger' in candidate:
                converged = True
            else:
                converged = False

            inputs, outputs = self.kadmos.get_io_for_replaced_disciplines(candidate, converged=converged,
                                                                          only_non_const=True)
            n_var = len(inputs)

            # Calculate consequences for replacement
            for idx, discipline_id in enumerate(candidate):
                if discipline_id == 'Converger':
                    continue

                discipline = self.get_discipline(discipline_id)
                discipline_score = self.workflow_analysis.get_discipline_score(discipline=discipline)
                discipline_analysis = self.workflow_analysis.get_discipline_analysis(discipline=discipline)

                combined_normalized_runtime += discipline_score['normalized_runtime']

                # If multiple disciplines with several iterations number are combined, it means the higher
                # iterations feedback loop MUST be fully replaced with SM. Otherwise this would not be possible
                expected_iter = min([expected_iter, discipline_score['mean_iterations']])

                # For the training time, iterations are important. If feedback loop occurs in DoE, this will have to be
                # converged.
                combined_training_time += discipline_analysis.mean_runtime * discipline_score['mean_iterations']

                if currently_available_samples is None:
                    currently_available_samples = discipline.n_available_samples
                else:
                    currently_available_samples = min([currently_available_samples, discipline.n_available_samples])
            if not converged:  # Non-converged workflows don't need iterations for a sample
                combined_training_time = combined_training_time / expected_iter

            if not converged:
                t_wf_new = t_wf_original * (1 - combined_normalized_runtime) + expected_iter * self.t_sur
            else:
                # For a converged candidate, the convergence loop is removed so no iterations occur
                t_wf_new = t_wf_original*(1-combined_normalized_runtime)+self.t_sur

            self.strategies[candidate] = dict(t_s=combined_training_time,
                                              t_wf_new=t_wf_new,
                                              n_var=n_var,
                                              currently_available_samples=currently_available_samples)

    def get_top_n_strategies(self, advisor, profile, n):
        sample_percentage = str(int(self.profiles[profile]*100))
        if self._fixed == 'time':
            data = self.advise_data[advisor]['d_n_obj']
            sorted_data = data.sort_values(by=sample_percentage, axis=0, ascending=False)
        if self._fixed == 'iter':
            data = self.advise_data[advisor]['d_t_opt']
            sorted_data = data.sort_values(by=sample_percentage, axis=0, ascending=True)
        else:
            raise AssertionError("Please fix either 'time' or 'iter'.")

        return sorted_data

    def get_n_s_for_strategy(self, advisor, percentage, candidate):
        if isinstance(percentage, int) or isinstance(percentage, float):
            percentage = str(int(percentage))

        data = self.advise_data[advisor]['n_s']
        subdata = data.loc[data['candidate'] == ''.join(candidate)]
        return subdata.iloc[0][percentage]

    def build_advise(self, candidates: list[tuple]):
        """Take the generated advise and build panda dataframes for strategy determination

        :param candidates:
        :return:
        """
        self.analyze_strategies(candidates)
        columns = [0.25, 0.5, 0.75, 1.0, 1.25, 1.50]
        names = ['25', '50', '75', '100', '125', '150']

        if self.account_for_profiling:
            t_profiling = self.workflow_analysis.total_runtime
        else:
            t_profiling = 0

        self.advise_data = dict()
        for advisor, advise in self.sample_advisors.items():
            self.advise_data[advisor] = dict()
            data_n_s = pd.DataFrame(columns=['candidate'] + names)
            data_d_n_obj = pd.DataFrame(columns=['candidate'] + names)
            data_d_t_opt = pd.DataFrame(columns=['candidate'] + names)
            data_t_training = pd.DataFrame(columns=['candidate'] + names)
            data_t_comb = pd.DataFrame(columns=['candidate'] + names)
            for candidate in self.strategies:
                strategy = self.strategies[candidate]
                advised_samples = advise(strategy['n_var'])
                row_n_s = dict(candidate=[''.join(candidate)])
                row_d_n_obj = dict(candidate=[''.join(candidate)])
                row_d_t_opt = dict(candidate=[''.join(candidate)])
                row_d_t_training = dict(candidate=[''.join(candidate)])
                row_t_comb = dict(candidate=[''.join(candidate)])
                for idx, column in enumerate(columns):
                    row_n_s[names[idx]] = column*advised_samples
                    if self.account_for_profiling:
                        t_training = strategy['t_s']*(row_n_s[names[idx]]-strategy['currently_available_samples'])
                    else:
                        t_training = strategy['t_s'] * (row_n_s[names[idx]])
                    row_d_t_training[names[idx]] = t_training
                    row_d_n_obj[names[idx]] = (self.opt_time_budget-t_training-t_profiling)/strategy['t_wf_new']-self.opt_iteration_budget
                    row_t_comb[names[idx]] = strategy['t_wf_new'] * self.opt_iteration_budget + t_training + t_profiling
                    row_d_t_opt[names[idx]] = row_t_comb[names[idx]] - self.opt_time_budget


                data_n_s = pd.concat([data_n_s, pd.DataFrame.from_dict(row_n_s)])
                data_d_n_obj = pd.concat([data_d_n_obj, pd.DataFrame.from_dict(row_d_n_obj)])
                data_d_t_opt = pd.concat([data_d_t_opt, pd.DataFrame.from_dict(row_d_t_opt)])
                data_t_training = pd.concat([data_t_training, pd.DataFrame.from_dict(row_d_t_training)])
                data_t_comb = pd.concat([data_t_comb, pd.DataFrame.from_dict(row_t_comb)])

            self.advise_data[advisor]['n_s'] = data_n_s
            self.advise_data[advisor]['t_training'] = data_t_training
            self.advise_data[advisor]['d_n_obj'] = data_d_n_obj
            self.advise_data[advisor]['d_t_opt'] = data_d_t_opt
            self.advise_data[advisor]['t_comb'] = data_t_comb

    def get_strategy_metrics(self, strategy, n_samples):
        if not self.strategies:
            self.analyze_strategies()

        return self.strategies[strategy][n_samples]

    def get_strategy_metric(self, strategy, n_samples, metric):
        return self.get_strategy_metrics(strategy, n_samples)[metric]

    def advise(self, candidates, sample_advisor='jones', n_strategies=3):
        if not self.strategies:
            self.analyze_strategies(candidates)

        top_n = {}
        for profile in self.profiles:
            top_n[profile] = []

        for discipline in self.strategies:
            strategy = self.strategies[discipline]
            advised_samples = strategy['sample_advise'][sample_advisor]

            for profile in self.profiles:
                net_samples = math.ceil(self.profiles[profile] * advised_samples)
                result = strategy['choices'][net_samples]

                # Add the result to the top_n candidates, sort, and only keep top N
                top_n[profile].append(dict(strategy=discipline,
                                           advised_samples=net_samples,
                                           obj_func_calls=result['obj_func_calls'],
                                           balance=result['balance']))

                top_n[profile] = sorted(top_n[profile], key=lambda d: d['balance'], reverse=True)

                if len(top_n[profile]) > n_strategies:
                    top_n[profile] = top_n[profile][0:n_strategies]

        self.visualize(['D1', 'D2'])

        return top_n

    def visualize(self, strategies_to_plot: Union[str, list]):
        if isinstance(strategies_to_plot, str):
            strategies_to_plot = [strategies_to_plot]

        fig = plt.figure()
        ax = fig.add_subplot(111)

        for strategy in strategies_to_plot:
            n_s = []
            obj_func_calls = []
            for n_samples in self.strategies[strategy]['choices']:
                n_s.append(n_samples)
                obj_func_calls.append(self.strategies[strategy]['choices'][n_samples]['obj_func_calls'])

            ax.plot(n_s, obj_func_calls, label=f'{strategy} ($N_v$={self.strategies[strategy]["n_var"]})')
            color = ax.lines[-1].get_color()

            for advisor in self.strategies[strategy]['sample_advise']:
                n_samples_advise = self.strategies[strategy]['sample_advise'][advisor]
                ax.axvline(n_samples_advise, color=color, linestyle='--')
                ax.text(n_samples_advise, 0, advisor, rotation=90)

        ax.axhline(y=self.standard_optimization_iteration_budget, color='r', linestyle='--', label='Without SM')
        ax.legend()
        ax.set_ylabel('Objective Function Calls')
        ax.set_xlabel('$N_s$')
        ax.set_title('Pareto Front: Amount of DoE samples vs. optimization obj. function calls')

        plt.show()

        '''
        pos = np.arange(len(labels))
        ax.set_xticks(pos)
        ax.set_xticklabels(labels)
        ax.bar(pos, data)
        ax.set_ylim([0, min(data) * 3])
        ax.set_title('RMSE for different models for AeroAnalysis discipline')
        ax.set_ylabel('RMSE')'''
