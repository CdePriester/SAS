from sas.core.sas_core import SAS

sas = SAS(
        cmdows_opt_file=r'/examples/tool_repository/sellar/Graphs/CMDOWS/Mdao_MDF-GS.xml',
        cmdows_fpg_file=r'/examples/tool_repository/sellar/Graphs/CMDOWS/FPG_MDO.xml')

sas.init_pido()

sas.deploy_all_disciplines(tool_folder=r"C:\Dev\Thesis\surrogateassistancesystem\tool_repository\sellar",
                           overwrite=True,
                           cpacs_input_folder='ToolInput',
                           cpacs_input_file='cpacs_in.xml',
                           cpacs_output_folder='ToolOutput',
                           cpacs_output_file='cpacs_out.xml',
                           )

#sas.run_pido(wf_file=r"C:\Users\Costijn\.rce\default\workspace\Mdao_MDF-GS-FinalHopefully\Mdao_MDF-GS-FinalHopefully.wf")

doe_file = sas.generate_doe(filename='DoE_sellar')

n_samples = 15
initial_wf_file = r"C:\Users\Costijn\.rce\default\workspace\Sellar_Project_Folder\Sellar_DoE_MDF_GS.wf"

new_wf_file = sas.deploy_custom_design_table_into_workflow(wf_file=initial_wf_file,
                                                           n_samples=n_samples,
                                                           method='LHS',
                                                           seed=4)

#sas.run_pido(wf_file=new_wf_file)

sas.replace_discipline_with_surrogate('D1')

print(f'DoE File exported to: {doe_file}. Please load the file manually and proceed.')
