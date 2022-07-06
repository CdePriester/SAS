import time
import os
import shutil
import pickle
import math
import copy
from sas.kadmos_interface.cpacs import PortableCpacs

from sas.core.sas_core import SAS
from mtom.mtom_python_wrapper import connect_to_matlab
from sas.gui.advise_visualization import AdviseVisualization
from sas.gui.analysis_visualization import AnalysisVisualization


def main():
    accuracy_validation = False
    strategy_validation = False
    make_closest_validation = False
    full_opt_training = True

    labels = {'/dataSchema/wing/inner/sweep': r'$\Lambda_{inner, LE}$',
              '/dataSchema/wing/inner/chord': r'$c_{root}$',
              '/dataSchema/wing/mid/twist': r'$\epsilon_{mid}$',
              '/dataSchema/wing/outer/twist': r'$\epsilon_{tip}$',
              '/dataSchema/wing/outer/sweep': r'$\Lambda_{outer, LE}$',
              '/dataSchema/wing/outer/chord': r'$c_{tip}$',
              '/dataSchema/wing/outer/span': r'$b_{outer}$',
              '/dataSchema/weights/str_wing': r'$+W_{str}$',
              '/dataSchema/weights/fuel': r'$+W_{F}$'
              }

    sas = SAS(
        cmdows_opt_file=r'mtom/CMDOWS/MDG-MDF-GS.xml',
        cmdows_fpg_file=r'mtom/CMDOWS/FPG-MDF-GS.xml',
        initial_cpacs=r'mtom\prepared_mtom_cpacs.xml')

    #sas.apply_labels_in_graphs(labels)
    sas.generate_doe(filename='TestjeOoke', build_dsm=True)

    sas.init_pido(pido_path=r"\Dev\Thesis\rce\rce.exe", test_connection=False)

    sas.build_doe_for_disciplines(disciplines=['LoadAnalysis', 'StructuralAnalysis', 'AeroAnalysis', 'PerformanceAnalysis'])

    aero_discipline = sas.get_discipline('AeroAnalysis')
    aero_discipline.add_hidden_constraint(flags={'/dataSchema/errorFlags/aero': 1},
                                          actions=[{'action': 'set_variable_to_value',
                                                    '/dataSchema/wing/L_D': -1,
                                                    '/dataSchema/errorFlags/aero': 1}],
                                          ignore_in_training=True)

    structural_discipline = sas.get_discipline('StructuralAnalysis')
    structural_discipline.add_hidden_constraint(flags={'/dataSchema/errorFlags/struct': 1},
                                                actions=[{'action': 'set_variables_to_value_from_file',
                                                          'filename': r'C:\Dev\Thesis\surrogateassistancesystem\tool_repository\mtom\prepared_mtom_cpacs.xml',
                                                          'variables_to_reset': ['/dataSchema/weights/str_wing']},
                                                         {'action': 'set_variable_to_value',
                                                          '/dataSchema/errorFlags/struct': 1}
                                                         ])

    performance_discipline = sas.get_discipline('PerformanceAnalysis')
    performance_discipline.add_hidden_constraint(flags={'/dataSchema/errorFlags/fuel': 1},
                                                 actions=[{'action': 'set_variables_to_value_from_file',
                                                           'filename': r'C:\Dev\Thesis\surrogateassistancesystem\tool_repository\mtom\prepared_mtom_cpacs.xml',
                                                           'variables_to_reset': ['/dataSchema/weights/fuel']},
                                                          {'action': 'set_variable_to_value',
                                                           '/dataSchema/errorFlags/fuel': 1}
                                                          ])
    # Start Matlab sessions to prevent first sample to take unreasonably long
    disciplines = [disc.id for disc in sas.disciplines]
    for disc in disciplines:
        connect_to_matlab(matlab_session_name=f'{disc}_session')

    sas.deploy_all_disciplines(tool_folder=r"C:\Dev\Thesis\surrogateassistancesystem\tool_repository\mtom",
                               overwrite=True)

    custom_range = {'/dataSchema/wing/inner/sweep': [15.4350, 28.6650],
                    '/dataSchema/wing/inner/chord': [6.5800, 12.2200],
                    '/dataSchema/wing/mid/twist': [-3.500, 3.5],
                    '/dataSchema/wing/outer/twist': [-3.500, 3.5],
                    '/dataSchema/wing/outer/sweep': [21.3500, 39.6500],
                    '/dataSchema/wing/outer/chord': [1.9250, 3.5750],
                    '/dataSchema/wing/outer/span': [9.3520, 17.3680],
                    '/dataSchema/weights/str_wing': [99000, 210000],
                    '/dataSchema/weights/fuel': [464993, 588563]
                    }

    full_wf_doe_file = r'C:\Users\Costijn\.rce\default\workspace\ThesisMTOM\ThesisMTOMValidation.wf'

    surrogate_options = dict(mode='fixed_type',
                             selection=['KRG'],
                             training_set='validated')

    SM_strategies = [['LoadAnalysis', 'StructuralAnalysis', 'AeroAnalysis', 'PerformanceAnalysis'],
                     ['AeroAnalysis'],
                     ['Converger', 'LoadAnalysis', 'StructuralAnalysis', 'AeroAnalysis', 'PerformanceAnalysis']]

    doe_files = [r'C:\Users\Costijn\.rce\default\workspace\ThesisMTOM\SM1_DoE.wf',
                 r'C:\Users\Costijn\.rce\default\workspace\ThesisMTOM\SM2_DoE.wf',
                 r'C:\Users\Costijn\.rce\default\workspace\ThesisMTOM\SM3_DoE.wf']

    opt_files = [r'C:\Users\Costijn\.rce\default\workspace\ThesisMTOM\SM1_opt.wf',
                 r'C:\Users\Costijn\.rce\default\workspace\ThesisMTOM\SM2_opt.wf',
                 r'C:\Users\Costijn\.rce\default\workspace\ThesisMTOM\SM3_opt.wf']

    full_wf_opt_file = r'C:\Users\Costijn\.rce\default\workspace\ThesisMTOM\full_opt.wf'

    percentages = [0.25, 0.5, 0.75, 1, 1.25, 1.5]
    percentages_text = [str(int(percentage * 100)) for percentage in percentages]
    obj_variable = '/dataSchema/weights/to_max'

    if False:
        full_opt = {}
        t = time.time()
        opt_run_id = sas.run_pido(wf_file=full_wf_opt_file)
        full_opt['t'] = time.time() - t
        full_opt_cpacs = sas.get_final_cpacs(run_id=opt_run_id)
        full_opt['opt_des'] = sas.build_sampling_point_from_cpacs(full_opt_cpacs)
        cpacs = PortableCpacs(full_opt_cpacs)
        full_opt['obj_val'] = cpacs.get_value(obj_variable)
        sas.database.delete_run(run_id=opt_run_id)  # Clean database for later analysis

    t = time.time()
    #sas.full_exploratory_run(doe_file=full_wf_doe_file, n_samples=4)
    sas.analyse_run(run_id='a0443c1d-d478-40f5-b848-a67fc8dbb55c')
    profiling_time = time.time() - t
    profile_runtimes = sas.workflow_analysis.get_discipline_metric('AeroAnalysis', 'discipline_call_runtimes')
    for strategy, doe_file, opt_file in zip(SM_strategies, doe_files, opt_files):
        n_s = []
        sur_error = []
        doe_time = []
        sur_training_time = []
        opt_time = []
        cpacs_results = []
        design_vectors = []
        obj_values = []
        real_obj_values = []
        combined_time = []
        error_loo = []
        aero_runtime = []
        for percentage, percentage_text in zip(percentages, percentages_text):
            print(f'Starting run for {percentage_text}%')

            # Build samples, get n_s
            sm_key = sas.init_surrogate_model(disciplines=strategy)
            advisor = sas.give_advise(optimization_budget=59, budget_type='iter', account_for_profiling=False)
            n_s_full = advisor.get_n_s_for_strategy(advisor='jones',
                                                    percentage=percentage_text,
                                                    candidate=tuple(strategy))

            n_s_corrected = math.ceil(n_s_full)
            n_s.append(n_s_corrected)

            # Build DoE and execute in PIDO
            t_combined = time.time()
            sampling_plan = sas.generate_samples(n_samples=n_s_corrected, disciplines=strategy, seed=1,
                                                 surrogate_model=sas.surrogate_models[sm_key],
                                                 custom_range=custom_range,
                                                 make_closest=True)
            new_wf_file = sas.deploy_samples_into_workflow(wf_file=doe_file, sampling_plan=sampling_plan)
            t_doe = time.time()
            run_id_doe = sas.run_pido(new_wf_file)  # Execute the DoE
            doe_time.append(time.time() - t_doe)
            sas.analyse_run(run_id=run_id_doe)
            runtimes = copy.deepcopy(sas.workflow_analysis.get_discipline_metric('AeroAnalysis', 'discipline_call_runtimes'))
            aero_runtime.append(runtimes)
            sas.workflow_analysis.remove_timeline(run_id=run_id_doe)
            # Train SM and deploy in workflow
            t_training = time.time()
            new_mdg_file = sas.deploy_surrogate(disciplines=strategy, **surrogate_options)
            sur_error.append(sas.surrogate_models[sm_key].error)
            sur_training_time.append(time.time() - t_training)

            # Optimize with SM
            t_opt = time.time()
            run_id_opt = sas.run_pido(wf_file=opt_file)
            opt_time.append(time.time() - t_opt)

            # Process optim results
            cpacs_results.append(sas.get_final_cpacs(run_id=run_id_opt))
            design_vectors.append(sas.build_sampling_point_from_cpacs(cpacs=cpacs_results[-1]))
            opt_sample = sas.database.get_last_sample_in_run(run_id=run_id_opt, tool_name='WeightAnalysis')
            obj_values.append(opt_sample['output'][obj_variable])
            combined_time.append(time.time() - t_combined)

            # Check validity of final result
            wf_file_check = sas.deploy_samples_into_workflow(full_wf_doe_file, design_vectors[-1])
            run_id_check = sas.run_pido(wf_file=wf_file_check)
            opt_sample_check = sas.database.get_last_sample_in_run(run_id=run_id_check, tool_name='WeightAnalysis')
            real_obj_values.append(opt_sample_check['output'][obj_variable])

            error_loo.append(sas.surrogate_models[sm_key].validate(method='leave-one-out'))

            # Clean DB for next run
            sas.database.delete_run(run_id=run_id_doe)
            sas.database.delete_run(run_id=run_id_opt)
            sas.database.delete_run(run_id=run_id_check)

            sas.surrogate_models.pop(sm_key)

        combined_data = {}
        combined_data['n_s'] = n_s
        combined_data['sur_error'] = sur_error
        combined_data['doe_time'] = doe_time
        combined_data['sur_training_time'] = sur_training_time
        combined_data['opt_time'] = opt_time
        combined_data['cpacs_results'] = cpacs_results
        combined_data['design_vectors'] = design_vectors
        combined_data['obj_values'] = obj_values
        combined_data['real_obj_values'] = real_obj_values
        combined_data['combined_time'] = combined_time
        combined_data['error_loo'] = error_loo
        combined_data['profiling_time'] = profiling_time
        combined_data['profile_runtimes'] = profile_runtimes
        combined_data['full_opt'] = full_opt
        combined_data['aero_runtime'] = aero_runtime

        output_folder = r"C:\Dev\Thesis\surrogateassistancesystem\validation_data"
        output_file = os.path.join(output_folder, "".join(strategy) + ".pickle")
        with open(output_file, 'w+b') as f:
            pickle.dump(combined_data, f)

if __name__ == '__main__':
    main()