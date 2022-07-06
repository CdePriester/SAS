from matplotlib import pyplot as plt
import tikzplotlib
import numpy as np
import matplotlib.ticker as mticker


class AnalysisVisualization:
    def __init__(self, workflow_analysis):
        self.workflow_analysis = workflow_analysis
        self.workflow_analysis.score()

    def plot_normalized_runtimes(self, output_filename, type='png'):
        scores = self.workflow_analysis.scores
        normalized_runtimes = [scores[disc]['normalized_runtime']*100 for disc in scores]
        index = np.arange(len(normalized_runtimes))

        plt.rc('font', family='serif')
        plt.rc('text', usetex=True)
        fig = plt.figure(figsize=(7, 5))
        ax = fig.add_subplot(1, 1, 1)
        ax.set_xticks(index)
        ticks_loc = ax.get_xticks().tolist()
        ax.xaxis.set_major_locator(mticker.FixedLocator(ticks_loc))
        ax.set_xticklabels(scores.keys(), rotation=45, ha='right')
        ax.set_ylabel(r'$\tilde{t}_{exec, i}$ [\% of $t_{tot}$]')
        plt.title("Normalized runtimes for disciplines in Sellar workflow")
        plt.bar(index, normalized_runtimes, width=0.8)
        #plt.show()
        plt.tight_layout()
        if type == 'png':
            plt.savefig(output_filename, dpi=600, format='png')
        elif type == 'tikz':
            tikzplotlib.save(output_filename, axis_width=r'\textwidth', axis_height='5cm')

        print('Finished.')