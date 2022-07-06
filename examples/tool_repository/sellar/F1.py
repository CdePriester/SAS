from sellarCPACS import SellarCPACS
import math


def main():
    cpacs = SellarCPACS()
    print('test')
    x1 = cpacs.get_value('x1')
    y2 = cpacs.get_value('y2')
    z2 = cpacs.get_value('z2')
    y1 = cpacs.get_value('y1')

    f = round(x1*x1 + z2 + y1 + math.exp(-1*y2), 5)
    print(f'f = {f}')
    cpacs.update_value('f', f)
    cpacs.save_cpacs()


if __name__ == '__main__':
    main()