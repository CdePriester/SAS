from sellarCPACS import SellarCPACS
import math
import time

def main():
    cpacs = SellarCPACS()

    c = cpacs.get_value('c')
    z1 = cpacs.get_value('z1')
    z2 = cpacs.get_value('z2')
    y1 = cpacs.get_value('y1')

    if y1 < 0:
        y1 = 0

    y2 = c*(math.sqrt(y1) + z1 + z2)
    #time.sleep(6)
    cpacs.update_value('y2', y2)
    cpacs.save_cpacs()


if __name__ == '__main__':
    main()