from kadmos import graph
from kadmos.graph import FundamentalProblemGraph
from sas.kadmos_interface.cpacs import PortableCpacs

import os


def return_to_compatible_version(filename):
    xml = PortableCpacs(cpacs_in=filename)

    xml.update_value('/cmdows/header/cmdowsVersion', 0.8)
    xml.update_value('/cmdows/header/updates/update/cmdowsVersion', 0.8)
    xml.save(filename)


def build_mtom_mdao():
    tool_cmdows_repo = 'init_cmdows_mtom.xml'
    cmdows_out_folder = 'CMDOWS'
    dsm_out_folder = 'DSM'

    compile_pdf = True

    dsm_settings = dict(destination_folder=dsm_out_folder,
                        keep_tex_file=not compile_pdf,
                        compile_pdf=compile_pdf,
                        summarize_vars=False
                        )

    cmdows_settings = dict(file_type='CMDOWS',
                           destination_folder=cmdows_out_folder,
                           creator='Costijn de Priester',
                           version='0.1',
                           pretty_print=True,
                           integrity=False)

    # Loading the Tool Repository and creating the RCG
    rcg = graph.load(tool_cmdows_repo, check_list=['consistent_root', 'invalid_leaf_elements'])

    tool_order = ['Denormalizer',
                  'LoadAnalysis',
                  'StructuralAnalysis',
                  'AeroAnalysis',
                  'PerformanceAnalysis',
                  'WeightAnalysis',
                  'FuelConstraint',
                  'WingloadingConstraint']

    rcg.graph['name'] = 'Minimum Take-Off Mass Optimization problem'
    rcg.graph['description'] = 'RCG of the MTOM problem. Generated for the Surrogate Assistance System.'

    rcg.create_dsm(file_name='RCG', function_order=tool_order, **dsm_settings)
    rcg.save(file_name='RCG-MTOM',
             description='Repository Connectivity Graph of the MTOM problem.',
             **cmdows_settings)

    # Imposing the MDAO architecture on the RCG.
    fpg = FundamentalProblemGraph(rcg)

    mdao_architecture = 'MDF-GS'
    #mdao_architecture = 'IDF'

    fpg.graph['name'] = 'FPG of the MTOM problem'
    fpg.graph['description'] = f'FPG of the MTOM problem. Optimization using the {mdao_architecture} architecture.'

    # Using the prepared (converged) cpacs file to determine variable bounds
    design_variables = ['/dataSchema/normalized/wing/inner/chord',
                        '/dataSchema/normalized/wing/outer/chord',
                        '/dataSchema/normalized/wing/inner/sweep',
                        '/dataSchema/normalized/wing/outer/sweep',
                        '/dataSchema/normalized/wing/outer/span',
                        '/dataSchema/normalized/wing/outer/twist',
                        '/dataSchema/normalized/wing/mid/twist'
                        ]

    include_airfoil = False
    if include_airfoil:
        n_bernstein = 12

        for idx in range(1, n_bernstein+1):
            # Matlab to Python confusion. Bernsteins start at 1, not 0
            design_variables.append(f'/dataSchema/normalized/wing/inner/foil/b_{str(idx)}')
            design_variables.append(f'/dataSchema/normalized/wing/outer/foil/b_{str(idx)}')

    '''
    cpacs_prepared = 'prepared_mtom_cpacs.xml'
    cpacs = PortableCpacs(cpacs_in=cpacs_prepared)

    nominal_values = cpacs.get_values(design_variables)
    lower_bounds = [val - 0.3*abs(val) for val in nominal_values]
    upper_bounds = [val + 0.3*abs(val) for val in nominal_values]
    '''

    #fpg.merge_functions(['LoadAnalysis', 'StructuralAnalysis'])

    fpg.mark_as_design_variables(nodes=design_variables,
                                 lower_bounds=0.7,
                                 upper_bounds=1.3,
                                 nominal_values=1)

    fpg.mark_as_constraints(nodes=['/dataSchema/constraints/load',
                                   '/dataSchema/constraints/fuel'],
                            operators='<=',
                            reference_values=0)

    fpg.mark_as_objective(node='/dataSchema/weights/to_max')

    fpg.add_problem_formulation(mdao_definition=mdao_architecture,
                                function_order=tool_order)
    fpg.add_function_problem_roles()

    problematic_variables = ['/dataSchema/weights/fuel', '/dataSchema/weights/str_wing']

    fpg.make_all_variables_valid()
    fpg.remove_unused_outputs()
    #fpg.split_variables(problematic_variables)

    fpg_name = f'FPG-{mdao_architecture}'
    mdg_name = f'MDG-{mdao_architecture}'

    fpg.create_dsm(fpg_name, **dsm_settings)
    fpg.save(fpg_name, **cmdows_settings)

    # Actually imposing architectures and generating mdg and mpg
    mdg, mpg = fpg.impose_mdao_architecture()
    mdg.create_dsm(mdg_name, mpg=mpg, **dsm_settings)
    mdg.save(mdg_name, mpg=mpg, description='MDG CMDOWS File for the MTOM problem', **cmdows_settings)

    return_to_compatible_version(os.path.join(cmdows_out_folder, f'{mdg_name}.xml'))

    # Testing a workaround for cmdows file that does not work in RCE
    fpg_file = os.path.join(cmdows_out_folder, f'{fpg_name}.xml')
    fpg = FundamentalProblemGraph(graph.load(file_name=fpg_file,
                                             check_list=['consistent_root', 'invalid_leaf_elements']))

    fpg.mark_as_design_variables(nodes=design_variables,
                                 lower_bounds=0.7,
                                 upper_bounds=1.3,
                                 nominal_values=1)

    fpg.mark_as_constraints(nodes=['/dataSchema/constraints/load',
                                   '/dataSchema/constraints/fuel'],
                            operators='<=',
                            reference_values=0)

    fpg.mark_as_objective(node='/dataSchema/weights/to_max')

    fpg.add_problem_formulation(mdao_definition=mdao_architecture,
                                function_order=tool_order)
    fpg.add_function_problem_roles()

    mdg, mpg = fpg.impose_mdao_architecture()
    mdg.save(f'{mdg_name}_new', mpg=mpg, description='Updated MDG CMDOWS File for the MTOM problem', **cmdows_settings)
    return_to_compatible_version(os.path.join(cmdows_out_folder, f'{mdg_name}_new.xml'))
    print(rcg)

if __name__ == '__main__':
    build_mtom_mdao()
