from sas.kadmos_interface.cpacs import PortableCpacs
import math
import getopt
import sys
import numpy as np

@np.vectorize
def mishra_constraint(x, y):
     return (x+5)**2 + (y+5)**2 - 25


if __name__ == '__main__':
    argument_list = sys.argv[1:]

    # print(argument_list)

    # Mandatory arguments
    short_options = "i:o:"
    long_options = ["input=", "output="]

    try:
        arguments, values = getopt.getopt(argument_list, short_options, long_options)
    except getopt.error as err:
        # Output error, and return with an error code
        print(str(err))
        sys.exit(2)

    input_cpacs = None
    output_cpacs = None

    # print(arguments)

    # Evaluate given options
    for current_argument, current_value in arguments:
        # print(f'current_argument = {current_argument}')
        # print(current_value)
        if current_argument in ("-i", "--input"):
            input_cpacs = current_value
        elif current_argument in ("-o", "--output"):
            output_cpacs = current_value

    cpacs = PortableCpacs(input_cpacs)

    x = cpacs.get_value('/dataSchema/x')
    y = cpacs.get_value('/dataSchema/y')

    c = mishra_constraint(x, y)
    cpacs.update_value('/dataSchema/c', c)
    cpacs.save(cpacs_out=output_cpacs)