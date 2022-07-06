from kadmos import graph
import os
from sas.kadmos_interface.cpacs import PortableCpacs

from kadmos.graph import FundamentalProblemGraph

def return_to_compatible_version(filename):
    xml = PortableCpacs(cpacs_in=filename)

    xml.update_value('/cmdows/header/cmdowsVersion', 0.8)
    xml.update_value('/cmdows/header/updates/update/cmdowsVersion', 0.8)
    xml.save(filename)

def main():
    base_cmdows_file = os.path.join("cmdows_sellar_basis.xml")

    # Build RCG from tool repository. Looks for fixed filenames in same folder, to determine inputs
    # and outputs of each discipline
    rcg = graph.load(base_cmdows_file,
               check_list=['consistent_root', 'invalid_leaf_elements'])

    compile_pdf = True
    folder_str = 'Graphs'

    dsm_settings = dict(destination_folder=os.path.join(folder_str, '(X)DSM_2'),
                        keep_tex_file=not compile_pdf,
                        compile_pdf=compile_pdf)
    cmdows_settings = dict(file_type='cmdows',
                           destination_folder=os.path.join(folder_str, 'CMDOWS_2'),
                           creator='Imco van Gent',
                           version='0.1',
                           pretty_print=True,
                           integrity=False)

    rcg_order = ['D1', 'D2', 'D1D2', 'F1', 'G1', 'G2']
    order = ['D1D2', 'F1', 'G1', 'G2']

    rcg.graph['name'] = 'Sellar test problem'
    rcg.graph['description'] = 'First try to get the RCG of sellar to work. Goal is to succesfully import in RCE.'

    rcg.create_dsm(file_name='RCG', function_order=rcg_order, **dsm_settings)
    rcg.save('RCG', description='RCG CMDOWS file of the super-sonic business jet test case',
             **cmdows_settings)

    mdao_definition = 'converged-DOE-GS-CT'

    mdao_definition = 'MDF-GS'
    mdao_definition_fpg = mdao_definition
    architecture_type = 'MDO'
    fpg = rcg.get_fpg_by_function_nodes(order)
    fpg.graph['name'] = 'FPG - {}'.format(architecture_type)
    fpg.graph['description'] = 'Fundamental problem graph to solve the Sellar test case ' \
                                   'problem for the architecture type: {}'.format(architecture_type)

    # Define settings of the problem formulation
    fpg.add_problem_formulation(mdao_definition_fpg, order)

    fpg.mark_as_design_variables(['/dataSchema/variables/z1',
                                      '/dataSchema/variables/z2',
                                  '/dataSchema/variables/x1'],
                                 lower_bounds=[-10, 0, 0],
                                 nominal_values=[0.01, 0.01, 1],
                                 upper_bounds=[10, 10, 10])
    fpg.mark_as_objective('/dataSchema/analyses/f')
    fpg.mark_as_constraints(['/dataSchema/analyses/g1', '/dataSchema/analyses/g2'], '>=', 0)

    fpg.add_function_problem_roles()
    fpg.add_problem_formulation(mdao_definition_fpg, order)
    fpg.make_all_variables_valid()
    fpg.create_dsm(file_name='FPG_MDO', **dsm_settings)

    filename_fpg = os.path.join(cmdows_settings['destination_folder'], 'FPG_MDO.xml')

    # Save output files
    fpg.save('FPG_MDO', description='FPG CMDOWS file of the SSBJ test case', **cmdows_settings)

    graph.load(filename_fpg,
               check_list=['consistent_root', 'invalid_leaf_elements'])

    mdg, mpg = fpg.impose_mdao_architecture()
    filename = os.path.join(cmdows_settings['destination_folder'], 'Mdao_{}.xml'.format(mdao_definition))
    mdg.create_dsm(file_name='Mdao_{}'.format(mdao_definition), mpg=mpg, **dsm_settings)

    # Save the Mdao as cmdows (and do an integrity check)
    mdg.save('Mdao_{}'.format(mdao_definition), mpg=mpg,
             description='CMDOWS file of the SSBJ test case solution strategy',
             **cmdows_settings)

    return_to_compatible_version(filename)

if __name__ == "__main__":
    main()