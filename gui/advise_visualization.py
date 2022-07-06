import plotly.graph_objects as go
import tikzplotlib
import os
import matplotlib as mpl
from matplotlib import pyplot as plt

from typing import TYPE_CHECKING
from sas.core.advise import Advisor


class AdviseVisualization:
    def __init__(self, advisor: Advisor):
        self.advisor = advisor

    def build_report_plot(self, advisor, percentage, metric, top_n, basepath, custom_candidate=None):
        filename = os.path.join(basepath, f'{advisor}_{percentage}_{top_n}')
        filename_tikz = f"{filename}.tikz"
        filename_png = f"{filename}.png"

        data = self.advisor.advise_data[advisor][metric]

        data_sorted = data.sort_values(by=percentage, axis=0, ascending=True)

        col_names = data_sorted.columns
        x = [float(col_name) for col_name in col_names[1:]]

        raw_data_top_n = data_sorted.head(n=top_n).values.tolist()
        if custom_candidate:
            raw_data_top_n += data_sorted.loc[data_sorted['candidate'] == custom_candidate].values.tolist()
        candidates = [dat[0] for dat in raw_data_top_n]
        advise_data = [dat[1:] for dat in raw_data_top_n]

        plt.rc('font', family='serif')
        plt.rc('text', usetex=True)
        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(1, 1, 1)
        for idx in range(0, len(raw_data_top_n)):
            plt.plot(x, advise_data[idx][:], label=f'SM{idx+1}', linewidth=2)
        ax.legend()
        ax.set_xlabel('Implied accuracy [\%]')
        ax.set_xticks([25, 50, 75, 100, 125])
        if self.advisor.get_goal() == 'time':
            ax.set_ylabel('$\Delta n_{obj}$ [-]')
        else:
            ax.set_ylabel('$\Delta t_{opt}$ [s]')
        ax.hlines(y=0, linestyles='--', xmin=min(x), xmax=max(x), linewidth=2, color='r')
        plt.grid(True)
        plt.title("Implied accuracy for optimization performance")
        plt.tight_layout()
        plt.savefig(filename_png, dpi=600, format='png')
        tikzplotlib.save(filename_tikz, axis_width=r'\textwidth', axis_height='7.5cm')

    def plot_investments(self, advisor, candidates: list[list], filename):
        data = self.advisor.advise_data[advisor]['t_comb']
        to_plot_data = []

        for candidate in candidates:
            candidate = "".join(candidate)
            to_plot_data += data.loc[data['candidate'] == candidate].values.tolist()

        col_names = data.columns
        x = [float(col_name) for col_name in col_names[1:]]

        advise_data = [dat[1:] for dat in to_plot_data]
        plt.rc('font', family='serif')
        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(1, 1, 1)
        for idx in range(0, len(to_plot_data)):
            plt.plot(x, advise_data[idx][:], label=f'SM{idx + 1}', linewidth=3)
        ax.set_xlabel('Implied accuracy [\%]')
        ax.set_xticks([25, 50, 75, 100, 125])
        ax.set_ylabel('$t_{comb}$ [s]')
        ax.axhline(y=self.advisor.opt_time_budget, linestyle='--', linewidth=2, color='r', label='$t_{opt, est}$')
        ax.axvline(x=100, linestyle='--', linewidth=2, color='g', label='IA (advised)')
        ax.legend()
        plt.grid(True)
        plt.title("Costs for SM strategies")
        plt.tight_layout()
        tikzplotlib.save(filename, axis_width=r'\textwidth', axis_height='7.5cm')

    def build_interactive_plot(self):

        data = self.advisor.advise_data['jia']['advised']

        data_sorted = data.sort_values(by='100', axis=0, ascending=False)

        col_names = data_sorted.columns

        x = [float(col_name) for col_name in col_names[1:]]

        top_n = 3

        raw_data_top_n = data_sorted.head(n=top_n).values.tolist()

        candidates = [dat[0] for dat in raw_data_top_n]
        advise_data = [dat[1:] for dat in raw_data_top_n]

        fig = go.Figure()
        for idx in range(0, top_n):
            fig.add_trace(go.Scatter(x=x,
                                     y=advise_data[idx][:],
                                     mode='lines',
                                     name=candidates[idx]))

        fig.update_layout(title="Effect of surrogate model strategy on objective functions",
                          xaxis_title="Implied accuracy [%]",
                          yaxis_title="\delta n_{obj}",
                          yaxis=dict(range=[-10, 150]),
                          legend_title="SM Strategy")

        fig.show()
        print('Stop')