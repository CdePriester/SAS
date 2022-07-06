from kadmos.cmdows import CMDOWS
from kadmos import graph
from kadmos.graph import FundamentalProblemGraph, MdaoDataGraph, MdaoProcessGraph


opt_cmdows_file = r"Graphs/CMDOWS/RCE_prepped.xml"
rcg_cmdows_file = r"Graphs/CMDOWS/RCG.xml"
fpg_cmdows_file = r"Graphs/CMDOWS/FPG_MDO.xml"

opt_cmdows = CMDOWS(file_path=opt_cmdows_file)
rcg_cmdows = CMDOWS(file_path=rcg_cmdows_file)
fpg_cmdows = CMDOWS(file_path=fpg_cmdows_file)

rcg = graph.load(rcg_cmdows_file,
               check_list=['consistent_root', 'invalid_leaf_elements'])

fpg = graph.load(fpg_cmdows_file,
               check_list=['consistent_root', 'invalid_leaf_elements'])

new_fpg = FundamentalProblemGraph(rcg)
newly_fpg = FundamentalProblemGraph(fpg)

newly_fpg.graph['name'] = 'FPG - DoE'
newly_fpg.graph['description'] = 'Fundamental problem graph to solve the Sellar test case ' \
                               'problem for the architecture type: {}'.format('DoE')

opt_problem = graph.load(opt_cmdows_file)

mdg = opt_problem[0]
mpg = opt_problem[1]

function_order = mpg.get_process_order()

mdao_definition_fpg = 'converged-DOE-GS-CT'

# Define settings of the problem formulation. This overwrites anything that already exists in the FPG!
newly_fpg.add_problem_formulation(mdao_definition_fpg, function_order)



print('stop!')



# Get design variables, mark again as design variables with sample set

# Get objective variables, mark as QOI's

# Paar problemen. Hoe doen we het met de conflicten die al zijn opgelost in de FPG?

# Wat we ook kunnen doen... Import FPG, remove problem definition and replace with something else



cmdows = CMDOWS(file_path=cmdows_in_file)
opt_problem = graph.load(cmdows_in_file)

opt_problem_MDG = opt_problem[0]
opt_problem_MPG = opt_problem[1]



architecture_nodes = opt_problem_MPG.find_all_nodes(category='architecture element')

# Now it is called an FPG, but is essentially still an MDG. Optimizers, workflow etc are all still present
fpg_problem = opt_problem_MDG.deepcopy_as(FundamentalProblemGraph)

# What happens if we add a DoE Problem formulation to this graph

fpg = fpg_problem.get_subgraph_by_function_nodes(function_order, copy_type='deep')

mdao_definition = 'converged-DOE-GS'

# Define settings of the problem formulation
fpg.graph['problem_formulation'] = problem_formulation = dict()
fpg.add_problem_formulation(mdao_definition, function_order)
mdao_architecture = problem_formulation['mdao_architecture']



test = fpg.get_mdg()

print('Stoppert!')
