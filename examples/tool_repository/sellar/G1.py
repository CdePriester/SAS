from sellarCPACS import SellarCPACS


def main():
    cpacs = SellarCPACS()

    y1 = cpacs.get_value('y1')

    g1 = round(y1/3.16-1, 5)

    cpacs.update_value('g1', g1)
    cpacs.save_cpacs()


if __name__ == '__main__':
    main()