# Surrogate Advisory System (SAS)

## Remark: Alpha phase; code-cleanup is needed

This module will contain the full application, as it eventually will be distributed. Several submodules are found:

- [cmdows](cmdows/): Contains the interface to the CMDOWS file format. The implementation, found in `cmdows.cmdowsInterface.CMDOWSInterface`, inherits from `kadmos.cmdows.CMDOWS` and adds support operations required for working with surrogate models.
- [pido_interface](pido_interface/): Contains general abstract base class for PIDO interfaces, `pido_interface.pidoInterface.PIDOInterface`, as well as actual implementations such as `pido_interface.rceInterface.RCEInterface`.

Will be extended. Logbooks belonging to individual modules are found in their subsequent folders.

## Logbook
- 16/11/2021:
    - Created readme.md and setup structure
    - Played around a bit in Controller.py, can be seen as a 'sketchbook' for now.
- 06/01/2021:
    - Serious progress is being made. RCE has been almost figured out. One problem seems to be very difficult to work around though, which is that the loading of cmdows files in RCE stills seems to be a bit buggy. Probably best to discuss with Gianfranco or Anne-Liza. If that is figured out, rest should be straightforward. 
    - GUI is taking shape. Design to be found in `designs` folder, back-end is following suit with front-end.
    - Example tool problem and Sellar benchmark have been included in `tool_repository` and made compatible with RCE.
    - Overall SAS class is gradually being extended with basic CMDOWS interfacing and funtionalities.
      - Disciplines are extracted and assigned their own `Discipline` objects. From these objects, the surrogate model will be generated.
      - Variables are extracted and design variables are assigned a `Variable` object. Might need to be extended into a `Variable` class for all variables, and a `DesignVariable` child that accounts for the design variables. Check if necessary.
    - ...
- 10/01/2022:
    - Some design choices will have to be made:
        - *Where to store the design databases?*
          - Seems like there might be need for a 'sas workspace' folder. Could be used to dump the intermediate RCE files, create design databases for the tools and save overall SAS configuration.
          - Could be user specified, but might be an option to 'claim' C:\Users\USERNAME\.sas for this purpose. Is in line with .rce folder location
          - **Done.**  
        - *Which format?*
            - Probably easiest to adopt the json format. Scales well, intuitively human readable and language of choice for NoSQL databases such as MongoDB.
            - MongoDB also an option and it philosopy suits the problem at hand very well. However, likely unnecessarily complicated and reduces portability of application.
            - However, still more feasible than to implement relational DB's such as MSSQL or MySQL. Their structure probably does not lend itself very well for this problem.

- 22/02/2022:
    - Good intentions to keep this log more updated! 
    - MTOM and CMDOWS DoE deployment are up. 
    - KADMOS bug fixed. When splitting variables, the instance of the 'original' variable did not get set back to instance=0, causing problems later
        - Symptoms: variable names got 'cut-off': for example, `dataSchema/weights/str_wing` became `dataSchema/weights/str_`
        - Reason: due to non-0 (or 1 in the cmdows graph, bit of unclarity there) instance, tries to remove suffix (__v1 or __v2 etc) from name, but does this non-adaptive and cuts of original uid.
    
