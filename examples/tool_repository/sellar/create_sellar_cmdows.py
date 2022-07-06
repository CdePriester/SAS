from kadmos.cmdows import CMDOWS
import os

def main():
    cmdows = CMDOWS()

    competences = ["D1D2", "D1", "D2", "F1", "G1", "G2"]

    cmdows.add_header(creator="Costijn de Priester",
                      description="CMDOWS file for testing the Sellar bechmark problem in RCE",
                      timestamp="05-01-2022",
                      fileVersion="0.1")

    for competence in competences:
        cmdows.add_dc(uid=competence,
                      id=competence,
                      mode_id="normal",
                      instance_id= 0,
                      version="0.1",
                      label=f"{competence}")

        cmdows.add_dc_execution_details(dc_uid=competence,
                                        operating_system="Windows",
                                        integration_platform="RCE",
                                        command=f"call \"C:\\Dev\\Thesis\\surrogateassistancesystem\\venv\\Scripts\\activate.bat\" \r\n python " + '"${dir:tool}/' + f'{competence}.py"',
                                        description="")

    cmdows.save(os.path.join('cmdows_sellar_basis.xml'), pretty_print=True)

if __name__ == "__main__":
    main()