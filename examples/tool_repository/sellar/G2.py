from sellarCPACS import SellarCPACS


def main():
    cpacs = SellarCPACS()

    y2 = cpacs.get_value('y2')

    g2 = round(1-y2/24, 5)

    cpacs.update_value('g2', g2)
    cpacs.save_cpacs()


if __name__ == '__main__':
    main()