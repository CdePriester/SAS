import matlab.engine
import os
import time
import sys
import getopt

def connect_to_matlab(matlab_session_name='matlabToPythonSession',
                      matlab_exec_path=r"C:\Program Files\MATLAB\R2021b\bin\matlab.exe"):
    """ Find if a Matlab session with specified session name is available, and create if not available

    :param matlab_session_name: session name for specific matlab instanc
    :return: matlab engine object
    """

    command = fr'"{matlab_exec_path}" -r ' + f"matlab.engine.shareEngine('{matlab_session_name}')"

    available_sessions = matlab.engine.find_matlab()

    if matlab_session_name in available_sessions:
        try:
            eng = matlab.engine.connect_matlab(matlab_session_name)
            return eng
        except matlab.engine.EngineError as e:
            print('Could not connect to existing Matlab session. Try to initiate new session.')

    os.system(command)
    while matlab_session_name not in matlab.engine.find_matlab():
        print('Cannot find Matlab Session. Waiting to start up!')
        time.sleep(5)

    eng = matlab.engine.connect_matlab(matlab_session_name)

    return eng


def run_mtom_discipline(discipline, tool_path):
    matlab_eng = connect_to_matlab(matlab_session_name=f'{discipline}_session')
    matlab_eng.cd(tool_path)

    cpacs_in_file = 'cpacs_in/cpacs_in.xml'
    cpacs_out_file = 'cpacs_out/cpacs_out.xml'

    functions = dict(AeroAnalysis=lambda: matlab_eng.Q3D_cpacs(cpacs_in_file, cpacs_out_file, 1, nargout=0),
                     LoadAnalysis=lambda: matlab_eng.Q3D_cpacs(cpacs_in_file, cpacs_out_file, 0, nargout=0),
                     StructuralAnalysis=lambda: matlab_eng.EMWET_cpacs(cpacs_in_file, cpacs_out_file, nargout=0),
                     PerformanceAnalysis=lambda: matlab_eng.perf_cpacs(cpacs_in_file, cpacs_out_file, nargout=0),
                     WeightAnalysis=lambda: matlab_eng.W_to_max_cpacs(cpacs_in_file, cpacs_out_file, nargout=0),
                     FuelConstraint=lambda: matlab_eng.fuel_constraint(cpacs_in_file, cpacs_out_file, nargout=0),
                     WingloadingConstraint=lambda: matlab_eng.load_constraint(cpacs_in_file, cpacs_out_file, nargout=0),
                     Denormalizer=lambda: matlab_eng.denormalize(cpacs_in_file, cpacs_out_file, nargout=0),
                     )

    functions[discipline]()


if __name__ == '__main__':
    # Retrieve arguments from command line
    argument_list = sys.argv[1:]

    #print(argument_list)

    # Mandatory arguments
    short_options = "d:t:"
    long_options = ["discipline=", "tool_path="]

    try:
        arguments, values = getopt.getopt(argument_list, short_options, long_options)
    except getopt.error as err:
        # Output error, and return with an error code
        print(str(err))
        sys.exit(2)

    discipline = None
    tool_path = None

    #print(arguments)

    # Evaluate given options
    for current_argument, current_value in arguments:
        #print(f'current_argument = {current_argument}')
        #print(current_value)
        if current_argument in ("-d", "--discipline"):
            discipline = current_value
        elif current_argument in ("-t", "--tool_path"):
            tool_path = current_value

    run_mtom_discipline(discipline, tool_path)