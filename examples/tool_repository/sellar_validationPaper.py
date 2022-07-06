from sas.core.sas_core import SAS

from sas.kadmos_interface.cpacs import PortableCpacs
import time
import math
import os
import pickle


def main():
    surrogate_options = dict(mode='fixed_type',
                             selection=['KRG'],
                             training_set='validated')

    sas = SAS(
        cmdows_opt_file=r'C:\Dev\Thesis\surrogateassistancesystem\sas\examples/tool_repository/sellar/Graphs/CMDOWS/Mdao_MDF-GS.xml',
        initial_cpacs=r'C:\Dev\Thesis\surrogateassistancesystem\sas\examples\tool_repository\sellar\sellar_cpacs_in.xml')

    sas.init_pido(pido_path=r"\Dev\Thesis\rce\rce.exe",
                  test_connection=False)

    sas.deploy_all_disciplines(tool_folder=r"C:\Dev\Thesis\surrogateassistancesystem\sas\examples\tool_repository\sellar",
                               overwrite=True,
                               cpacs_input_folder='ToolInput',
                               cpacs_input_file='cpacs_in.xml',
                               cpacs_output_folder='ToolOutput',
                               cpacs_output_file='cpacs_out.xml',
                               )

    n_iter_opt = 42  # NUmber of iterations for full optimization

    full_wf_opt_file = r'C:\Users\Costijn\.rce\default\workspace\ThesisSellarFinal\Mdao_MDF-GS.wf'
    full_wf_doe_file = r'C:\Users\Costijn\.rce\default\workspace\ThesisSellarFinal\Full_sellar.wf'
    obj_variable = '/dataSchema/analyses/f'

    SM_strategies = [['D1', 'D2'], ['Converger', 'D1', 'D2'], ['D1']]
    doe_files = [r'C:\Users\Costijn\.rce\default\workspace\ThesisSellarFinal\D1D2_DoE.wf',
                 r'C:\Users\Costijn\.rce\default\workspace\ThesisSellarFinal\ConvD1D2_DoE.wf',
                 r'C:\Users\Costijn\.rce\default\workspace\ThesisSellarFinal\D1_DoE.wf']

    opt_files = [r'C:\Users\Costijn\.rce\default\workspace\ThesisSellarFinal\D1D2_opt.wf',
                 r'C:\Users\Costijn\.rce\default\workspace\ThesisSellarFinal\ConvD1D2_opt.wf',
                 r'C:\Users\Costijn\.rce\default\workspace\ThesisSellarFinal\D1_opt.wf']

    #sas.generate_doe('SellarDoE', build_dsm=True)

    percentages = [0.5, 0.75, 1, 1.25, 1.5]
    percentages_text = [str(int(percentage * 100)) for percentage in percentages]

    t = time.time()
    sas.full_exploratory_run(doe_file=full_wf_doe_file, n_samples=3)
    profiling_time = time.time() - t

    custom_range = {'/dataSchema/variables/x1': [0, 10],
                    '/dataSchema/variables/z1': [-10, 10],
                    '/dataSchema/variables/z2': [0, 10],
                    '/dataSchema/analyses/y1': [0, 80],
                    '/dataSchema/analyses/y2': [0, 35]}


    full_opt = {}
    t = time.time()
    opt_run_id = sas.run_pido(wf_file=full_wf_opt_file)
    full_opt['t'] = time.time() - t
    full_opt_cpacs = sas.get_final_cpacs(run_id=opt_run_id)
    full_opt['opt_des'] = sas.build_sampling_point_from_cpacs(full_opt_cpacs)
    cpacs = PortableCpacs(full_opt_cpacs)
    full_opt['obj_val'] = cpacs.get_value(obj_variable)
    sas.database.delete_run(run_id=opt_run_id)  # Clean database for later analysis

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
        for percentage, percentage_text in zip(percentages, percentages_text):
            print(f'Starting run for {percentage_text}%')

            # Build samples, get n_s
            sm_key = sas.init_surrogate_model(disciplines=strategy)
            advisor = sas.give_advise(optimization_budget=n_iter_opt, budget_type='iter')
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
            opt_sample = sas.database.get_last_sample_in_run(run_id=run_id_opt, tool_name='F1')
            obj_values.append(opt_sample['output'][obj_variable])
            combined_time.append(time.time() - t_combined)

            # Check validity of final result
            wf_file_check = sas.deploy_samples_into_workflow(full_wf_doe_file, design_vectors[-1])
            run_id_check = sas.run_pido(wf_file=wf_file_check)
            opt_sample_check = sas.database.get_last_sample_in_run(run_id=run_id_check, tool_name='F1')
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
        combined_data['full_opt'] = full_opt

        output_folder = r"C:\Dev\Thesis\surrogateassistancesystem\validation_data"
        output_file = os.path.join(output_folder, "".join(strategy) + ".pickle")
        with open(output_file, 'w+b') as f:
            pickle.dump(combined_data, f)


if __name__ == '__main__':
    main()
