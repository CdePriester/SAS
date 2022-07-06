# PIDO interfaces module
Module that handles all communication between a client and PIDO's. Will include functionalities for:

- Setting up and testing a 'connection' with a PIDO.
- Starting the execution of a workflow as defined in a CMDOWS file.
- Extract results from a run and make it available within the module.
- Extracting performance metrics of the PIDO, such as optimization performance, constraint violations, etc.

## pidoInterface.py: PIDOInterface
The abstract base class for PIDO interfaces. Contains the 'blueprint' for the child implementations, which provides a standardized interface for different PIDO's. Initially, RCE will be implemented.

## rceInterface.py: RCEInterface
Implementation of RCE interface.

Required locations:
- Workspace folder of RCE. Defaults to C:\Users\USERNAME\.rce\default.
- Output folder of intermediate RCE results. Needs to be manually set-up in tools

## Logbook:
- 16/11/2021:
  - Setting up structure of module, initiated readme.md.
  - Investigated possible connections to RCE. Command line interface is available, but it is interactive. However, it is possible to provide all the commands a-priori, avoiding the necessity to work with modules like `subprocess`. `os` module should do the trick, if all the statements can be prepared.
  - Implemented preliminary implementation of PIDO connection test for RCE.
    - *Look up if it is possible to hide pop-up shell, relatively low prio*
- 21/11/2021:
  - To find out requirements for CMDOWS and KADMOS interfacing, integration with RCE has been further investigated. Will not be as straightforward as initially thought, because:
    - It seems that CMDOWS workflows cannot be loaded into RCE from the command line, requiring manual input if an optimization is to be executed.
    - It appears that tools need to be manually 'imported' into RCE, using the 'Import tool' wizard. Again, possibilities to do this using the command line seem to be limited.
  - Possible workaround:
    - Import process of tools seems to boil down to the creation of a config file in the 'workspace' of RCE. For CPACS tools, these end up in *PATH_TO_WORKSPACE\integration\tools\cpacs*.
    - Should be possible to automate this process in Python, making the tools, and more importantly the to-be-generated surrogate models, available in RCE.
    - When the required CMDOWS files have been generated using KADMOS or SAS, they can be manually imported in RCE and workflow ('.wf') files are created.
    - These workflow files are JSON formatted, and should be able to be manipulated using Python, to replace executables in workflows with their surrogate counterparts.
    - The generated .wf files can be executed using the command line, which 'closes the gap'.
  - Ideal solution:
    - Command line functionality of RCE is extended with:
      - Importing of CMDOWS workflows and corresponding generation of .wf files.
      - Importing of tools in the RCE workspace.
  - Conclusion:
    - Integration within RCE is still possible, but the required CMDOWS workflow structures need to be implemented a-priori.
    - Workaround is a bit janky, possibly instable for later RCE releases if conventions change.
    - Discuss possibilities to use other PIDO's, such as OpenMDAO or OPTIMUS.