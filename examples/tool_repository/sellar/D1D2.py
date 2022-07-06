from sellarCPACS import SellarCPACS
import sys
import time
import math


def main():
    cpacs = SellarCPACS()

    c = cpacs.get_value('c')
    z1 = cpacs.get_value('z1')
    x1 = cpacs.get_value('x1')
    z2 = cpacs.get_value('z2')
    y2 = cpacs.get_value('y2')
    print('Testje')
    y1 = c*(z1*z1 + x1 + z2 - 0.2*y2)
    y2 = c*(math.sqrt(y1) + z1 + z2)
    #time.sleep(8)

    cpacs.update_value('y1', y1)
    cpacs.update_value('y2', y2)
    cpacs.save_cpacs()


if __name__ == '__main__':
    print("\nArguments passed:", end=" ")
    n = len(sys.argv)
    for i in range(1, n):
        print(sys.argv[i], end=" ")

    main()