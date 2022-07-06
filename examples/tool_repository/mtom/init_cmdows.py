from kadmos.cmdows import CMDOWS
from datetime import datetime
import os

def build_cmdows():
    cmdows = CMDOWS()

    matlab_executable_path = r"C:\Program Files\MATLAB\R2021a\bin\matlab.exe"

    timestamp = datetime.now()

    disciplines = {'StructuralAnalysis': {'script': 'EMWET_cpacs',
                                          'mode': None},
                   'AeroAnalysis': {'script': 'Q3D_cpacs',
                                    'mode': '1'},
                   'Denormalizer': {'script': 'denormalize',
                                    'mode': None},
                   'LoadAnalysis': {'script': 'Q3D_cpacs',
                                    'mode': '0'},
                   'PerformanceAnalysis': {'script': 'perf_cpacs',
                                           'mode': None},
                   'WeightAnalysis': {'script': 'W_to_max_cpacs',
                                      'mode': None},
                   'FuelConstraint': {'script': 'fuel_constraint',
                                      'mode': None},
                   'WingloadingConstraint': {'script': 'load_constraint',
                                      'mode': None}}

    cmdows.add_header(creator='Costijn de Priester',
                      description='CMDOWS file of the MTOM optimization problem',
                      timestamp=timestamp.strftime("%d/%m/%Y, %H:%M:%S"),
                      fileVersion='0.1')

    cmdows.add_contact(name='Costijn de Priester',
                       uid='cdepriester',
                       email='c.l.a.depriester@student.tudelft.nl',
                       company='TU Delft',
                       department='Flight Performance and Propulsion',
                       function='MSc student')

    for discipline in disciplines:
        cmdows.add_dc(uid=discipline,
                      id=discipline,
                      mode_id='1',
                      instance_id=1,
                      version='1.0',
                      label=discipline
                      )

        script = disciplines[discipline]['script']
        script_call = f'{script}' + "('cpacs_in/cpacs_in.xml', 'cpacs_out/cpacs_out.xml'"

        mode = disciplines[discipline]['mode']
        if mode is not None:
            script_call += f', {mode})'
        else:
            script_call += ')'

        command = 'cd ${dir:tool} \n\r'
        command += f'"{matlab_executable_path}" -batch "{script_call}; exit"'

        venv_path = os.path.join(os.environ['VIRTUAL_ENV'], 'Scripts', 'activate.bat')

        cmd_str = f"""call "{venv_path}"\n\r"""
        cmd_str += 'python "${dir:tool}/mtom_python_wrapper.py" -t ${dir:tool}' + f' -d {discipline}'

        cmdows.add_dc_execution_details(dc_uid=discipline,
                                        operating_system='Windows',
                                        integration_platform='RCE',
                                        command=cmd_str,
                                        software_requirements='Matlab installed on executing PC')

    cmdows.save(file_path='init_cmdows_mtom.xml', pretty_print=True)


if __name__ == '__main__':
    build_cmdows()
