from sas.core.workflow_analysis import WorkflowAnalysis
from sas.core.sas_core import SAS
from tkinter.filedialog import askopenfilename, askdirectory
from datetime import datetime
import math
import os.path


class InteractiveSession:
    def __init__(self, sas: SAS = None):
        self.sas = sas

    def run(self, mode='interactive'):
        if mode == 'interactive':
            self._run_interactive()

    def _run_interactive(self):
        if not self.sas:
            cmdows_opt_file = askopenfilename(title='Please select CMDOWS optimization file',
                                              filetypes=(('CMDOWS file', '*.xml'),))
            cmdows_fpg_file = askopenfilename(title='Please select CMDOWS fpg file',
                                              filetypes=(('CMDOWS file', '*.xml'),))

            workspace_flag = input('Specify a custom SAS workspace location? [Y/N] Default: C:\\Users\\USER\\.sas\\ ')

            if workspace_flag.upper() == 'Y':
                sas_workspace = askdirectory(title='Please select the SAS workspace folder')
            else:
                sas_workspace = None

            self.sas = SAS(cmdows_opt_file=cmdows_opt_file,
                           cmdows_fpg_file=cmdows_fpg_file,
                           sas_workspace=sas_workspace)

            valid_pidos = ['RCE']
            pido_environment = input(f'Which PIDO is used? Available options: {valid_pidos}')
            while pido_environment not in valid_pidos:
                print('Invalid PIDO environment selected')
                pido_environment = input(f'Which PIDO is used? Available options: {valid_pidos}')

            if pido_environment == 'RCE':
                pido_location = askdirectory(title='Please load the RCE folder')
                while not os.path.isfile(os.path.join(pido_location, 'rce.exe')):
                    print('RCE is not found. Please selection location for RCE!')
                    pido_location = askdirectory(title='Please load the RCE folder')

                pido_path = os.path.join(pido_location, 'rce.exe')

                wf_file = askopenfilename(title='Please select the RCE .wf file for the optimization',
                                          filetypes=(('RCE .wf file', '*.wf'),))
                self.sas.init_pido(pido_path=pido_path, run_file=wf_file)
            else:
                return

        exploratory_flag = input('Investigate provided workflow? [Y/N]')

        if exploratory_flag.upper() == 'Y':
            self._run_workflow_exploration()
        else:
            return

    def _run_workflow_exploration(self):
        method = input('Which method to use? ["Profile"]')

        if method.upper() == "PROFILE":
            now = datetime.now()
            doe_filename = f'{now.strftime("%Y_%m_%d-%H_%M")}_DoE'
            doe_file = self.sas.generate_doe(filename=doe_filename)
            print(f'CMDOWS DoE has been generated ({doe_file}). Please load DoE in RCE and select in next popup.')
            input('Press enter to continue')
            doe_wf_file = askopenfilename(title=f'Please select the {doe_filename} file used for the exploration',
                                          filetypes=(('RCE .wf file', '*.wf'),))

            budget_raw = str(input('What is the available for exploration? Please provide in format: "HH:MM:SS"'))
            budget_raw = budget_raw.replace('"', '')
            budget = datetime.strptime(budget_raw, '%H:%M:%S')

            n_possible_profile_runs = self.sas.initial_exploratory_run(doe_file=doe_wf_file, budget=budget)

            n_runs = input(f"How many runs for exploration? Max: {n_possible_profile_runs} runs to stay within budget.")
            self.sas.full_exploratory_run(doe_wf_file, int(n_runs))

            optimization_budget = float(input(f"What is the budget/expected time for optimization in s?"))

            advisor = self.sas.give_advise(optimization_budget)
            # Select strategy and execute DoE for that strategy
            selected_strategy = str(input('Please select an optimization strategy from the figure'))
            selected_samples = int(input('Please select an amount of samples for the Surrogate Model'))

            doe_file = self.sas.build_doe_for_discipline(selected_strategy)
            print(f'CMDOWS DoE has been generated ({doe_file}). Please load DoE in RCE and select in next popup.')
            input('Press enter to continue')
            doe_wf_file = askopenfilename(title=f'Please select the {doe_file} file used for the DoE',
                                          filetypes=(('RCE .wf file', '*.wf'),))

            self.sas.deploy_custom_design_table_into_workflow(doe_wf_file,
                                                              n_samples=selected_samples,
                                                              method='LHS',
                                                              discipline=self.sas.get_discipline(selected_strategy))

            run_id = self.sas.run_pido(wf_file=doe_wf_file)
            self.sas.replace_discipline_with_surrogate(selected_strategy)

            print(f'Please select the optimization wf file from RCE in the next popup')
            input('Press enter to continue')
            opt_wf_file = askopenfilename(title=f'Please select the optimization file used for the optimization',
                                          filetypes=(('RCE .wf file', '*.wf'),))

            print('Running optimization....')
            self.sas.run_pido(wf_file=opt_wf_file)
            # Process results
        else:
            print(f'{method} is not a valid method!')


if __name__ == '__main__':
    sas = SAS(
        cmdows_opt_file=r'C:\Dev\Thesis\surrogateassistancesystem\tool_repository\mtom\CMDOWS\MDG-MDF-GS.xml',
        cmdows_fpg_file=r'C:\Dev\Thesis\surrogateassistancesystem\tool_repository\mtom\CMDOWS\FPG-MDF-GS.xml')

    sas.init_pido(pido_path=r"\Dev\Thesis\rce\rce.exe",
                  run_file=r"C:\Users\Costijn\.rce\default\workspace\MDG-MDF-GS_new_301\MDG-MDF-GS_new_301.wf")

    sas_engine = InteractiveSession(sas=sas)
    sas_engine.run(mode='interactive')
