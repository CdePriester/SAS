from kadmos.cmdows import CMDOWS
from kadmos import graph
from kadmos.graph import FundamentalProblemGraph
from datetime import datetime
import os
from sas.kadmos_interface.cpacs import PortableCpacs

def return_to_compatible_version(filename):
    xml = PortableCpacs(cpacs_in=filename)

    xml.update_value('/cmdows/header/cmdowsVersion', 0.8)
    xml.update_value('/cmdows/header/updates/update/cmdowsVersion', 0.8)
    xml.save(filename)

dsm_settings = dict(destination_folder='XDSM',
                        keep_tex_file=False,
                        compile_pdf=True,
                        summarize_vars=False
                        )

cmdows_settings = dict(file_type='CMDOWS',
                       destination_folder='CMDOWS',
                       creator='Costijn de Priester',
                       version='1',
                       pretty_print=True,
                       integrity=False)

cmdows = CMDOWS()
timestamp = datetime.now()
cmdows.add_header(creator='Costijn de Priester',
                      description='CMDOWS file of the Mishra Bird optimization problem',
                      timestamp=timestamp.strftime("%d/%m/%Y, %H:%M:%S"),
                      fileVersion='1')

cmdows.add_contact(name='Costijn de Priester',
                   uid='cdepriester',
                   email='c.l.a.depriester@student.tudelft.nl',
                   company='TU Delft',
                   department='Flight Performance and Propulsion',
                   function='MSc student')

disciplines = ['mishra_bird', 'mishra_constraint']

venv_path = os.path.join(os.environ['VIRTUAL_ENV'], 'Scripts', 'activate.bat')

cmd_line_1 = f"""call "{venv_path}"\n\r"""

for discipline in disciplines:

    cmdows.add_dc(uid=discipline,
                  id=discipline,
                  mode_id='1',
                  instance_id=1,
                  version='1.0',
                  label=discipline
                  )

    cmd_line_2 = rf'python "${{dir:tool}}/{discipline}.py" -i "${{dir:tool}}\cpacs_in\cpacs_in.xml" -o "${{dir:tool}}\cpacs_out\cpacs_out.xml" '

    cmd_str = cmd_line_1+cmd_line_2

    cmdows.add_dc_execution_details(dc_uid=discipline,
                                    operating_system='Windows',
                                    integration_platform='RCE',
                                    command=cmd_str,
                                    software_requirements='Matlab installed on executing PC')

rcg_path = 'mishra_rcg.xml'
cmdows.save(file_path='mishra_rcg.xml', pretty_print=True)
rcg = graph.load(rcg_path, check_list=['consistent_root', 'invalid_leaf_elements'])

fpg = FundamentalProblemGraph(rcg)
architecture = 'unconverged-OPT'
fpg.add_problem_formulation(mdao_definition=architecture,
                            function_order=disciplines)
fpg.mark_as_design_variables(nodes=['/dataSchema/x', '/dataSchema/y'],
                             lower_bounds=[-10, -6.5],
                             upper_bounds=[0, 0],
                             nominal_values=[-5, -3.25])
fpg.mark_as_constraint(node='/dataSchema/c',
                       operator='<=',
                       reference_value=0)

fpg.mark_as_objective(node='/dataSchema/f')

fpg.add_function_problem_roles()
fpg_name = f'FPG-{architecture}'
mdg_name = f'MDG-{architecture}'

fpg.create_dsm(fpg_name, **dsm_settings)
fpg.save(fpg_name, **cmdows_settings)

mdg, mpg = fpg.impose_mdao_architecture()
mdg.create_dsm(mdg_name, mpg=mpg, **dsm_settings)
mdg.save(mdg_name, mpg=mpg, description='MDG CMDOWS File for the Mishra Bird problem', **cmdows_settings)

return_to_compatible_version(os.path.join('CMDOWS', f'{mdg_name}.xml'))
