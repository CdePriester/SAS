from kadmos.cmdows import CMDOWS
from kadmos import graph
from kadmos.graph import RepositoryConnectivityGraph, FundamentalProblemGraph
from datetime import datetime
from sas.core.variable import Variable
from sas.core.discipline import Discipline
from sas.kadmos_interface.cpacs import PortableCpacs
from typing import Union

import copy
import os


def return_to_compatible_version(filename):
    """RCE doesn't work with CMDOWS 0.9. Manually set back to 0.8. Remove when fixed"""
    xml = PortableCpacs(cpacs_in=filename)

    xml.update_value('/cmdows/header/cmdowsVersion', 0.8)
    xml.update_value('/cmdows/header/updates/update/cmdowsVersion', 0.8)
    xml.save(filename)


class KadmosInterface:
    def __init__(self, cmdows_opt_file: str):
        self.cmdows_opt_file = cmdows_opt_file
        self.cmdows = CMDOWSExtension(cmdows_opt_file)

        opt_problem = graph.load(cmdows_opt_file,
                                 check_list=['consistent_root', 'invalid_leaf_elements'])

        assert len(opt_problem) == 2, f"Please provide MDG, currently {type(opt_problem)} is provided."

        self.mdg = opt_problem[0]
        self.mpg = opt_problem[1]

        self.build_fpg_from_mdg()

    def build_fpg_from_mdg(self):
        process_order = self.mpg.get_process_order()
        rcg = RepositoryConnectivityGraph(self.mdg)

        fpg = rcg.get_fpg_by_function_nodes(process_order)

        # Extract existing problem formulation, and apply to FPG
        problem_formulation = copy.deepcopy(self.mdg.graph['problem_formulation'])
        fpg.graph['problem_formulation'] = problem_formulation

        design_variables = self.cmdows.get_design_variables()

        for design_var in design_variables:
            fpg.mark_as_design_variable(node=design_var.parameter_uid,
                                        lower_bound=design_var.minimal_value,
                                        upper_bound=design_var.maximal_value,
                                        nominal_value=design_var.nominal_value)

        objective = self.cmdows.get_problem_role_variables('objective')
        fpg.mark_as_objective(objective[0])

        constraints = self.cmdows.get_problem_role_variables('constraint')

        for constraint in constraints:
            operator, reference = self.cmdows.get_constraint_details(constraint)
            fpg.mark_as_constraint(node=constraint,
                                   operator=operator,
                                   reference_value=reference)

        fpg.remove_unused_nodes()

        for node in fpg.variable_nodes:
            if 'architectureNodes' in node:
                if 'related_parameter_u_i_d' in fpg.nodes[node]:
                    related_node = fpg.nodes[node]['related_parameter_u_i_d']

                    targets = fpg.get_targets(node)
                    sources = fpg.get_sources(node)

                    for target in targets:
                        fpg.remove_edge(node, target)
                        fpg.add_edge(related_node, target)
                    for source in sources:
                        fpg.remove_edge(source, node)
                        fpg.add_edge(source, related_node)

                fpg.remove_node(node)

        fpg.add_function_problem_roles()
        fpg.make_all_variables_valid()

        self.fpg = fpg

    def get_level_for_discipline(self, process_hierarchy, discipline):
        if not isinstance(process_hierarchy, list):
            return None

        if discipline in process_hierarchy:
            return process_hierarchy

        for process in process_hierarchy:
            level = self.get_level_for_discipline(process, discipline)
            if level:
                return level

        return None

    def get_io_for_replaced_disciplines(self, disciplines: Union[list[str], tuple[str], str], converged=True,
                                        only_non_const=False):
        if isinstance(disciplines, list) or isinstance(disciplines, tuple):
            considered_disciplines = [discipline for discipline in disciplines if not discipline == 'Converger']
        else:
            considered_disciplines = [disciplines]
            #input = self.get_io_for_discipline(disciplines, 'in')
            #output = self.get_io_for_discipline(disciplines, 'out')
            #return input, output

        combined_inputs = []
        combined_outputs = []

        for idx, discipline in enumerate(considered_disciplines):
            inputs = self.get_io_for_discipline(discipline, 'in')

            for input_var in inputs:
                sources = self.mdg.get_sources(input_var)
                for source in sources:
                    if converged:
                        discipline_limit = considered_disciplines
                    else:
                        discipline_limit = considered_disciplines[0:idx]

                    if source not in discipline_limit and input_var not in combined_inputs:
                        if only_non_const and 'Coordinator' not in source:
                            combined_inputs.append(input_var)
                            break
                        elif not only_non_const:
                            combined_inputs.append(input_var)
                            break

            outputs = self.get_io_for_discipline(discipline, 'out')
            for output_var in outputs:
                targets = self.mdg.get_targets(output_var)
                for target in targets:
                    if target not in considered_disciplines[idx:] and output_var not in combined_outputs:
                        combined_outputs.append(output_var)
                        break

        return combined_inputs, combined_outputs

    def build_new_opt_files(self, surrogate_model, tool_repo, build_dsm=False):
        cmdows_settings = dict(file_type='cmdows',
                               destination_folder=tool_repo,
                               creator='Surrogate Advisory System',
                               version='0.1',
                               pretty_print=True,
                               integrity=False)

        dsm_settings = dict(destination_folder=tool_repo,
                            keep_tex_file=False,
                            compile_pdf=True,
                            summarize_vars=False
                            )

        self.build_io_files(surrogate_model, tool_repo)

        new_rcg = RepositoryConnectivityGraph(self.fpg)
        new_rcg_filename = os.path.join(cmdows_settings['destination_folder'], 'updated_rcg.xml')
        new_rcg.save(file_name='updated_rcg', **cmdows_settings)

        new_rcg_cmdows = CMDOWSExtension(new_rcg_filename)

        new_rcg_cmdows.add_dc(uid=surrogate_model.uid,
                              id=surrogate_model.uid,
                              mode_id='1',
                              instance_id=1,
                              version=str(surrogate_model.version),
                              label=surrogate_model.uid)

        new_rcg_cmdows.add_dc_general_info(dc_uid=surrogate_model.uid,
                                           description=surrogate_model.description,
                                           status=surrogate_model.status)

        new_rcg_cmdows.save(file_path=new_rcg_filename,
                            pretty_print=True)

        new_rcg = graph.load(new_rcg_filename, file_type='cmdows')

        current_tool_order = self.mpg.get_process_order()

        sur_model_disciplines = [discipline.uid for discipline in surrogate_model.disciplines]

        new_tool_order = []
        for tool in current_tool_order:
            if tool in sur_model_disciplines:
                if surrogate_model.uid not in new_tool_order:
                    new_tool_order.append(surrogate_model.uid)
            else:
                new_tool_order.append(tool)

        fpg = new_rcg.get_fpg_by_function_nodes(new_tool_order)

        # Extract existing problem formulation, and change the function order
        if fpg.check_for_coupling(new_tool_order, only_feedback=True):
            problem_formulation = copy.deepcopy(self.mdg.graph['problem_formulation'])
            problem_formulation['function_order'] = new_tool_order
            fpg.graph['problem_formulation'] = problem_formulation
        else:
            mdao_formulation = 'unconverged-OPT'
            fpg.add_problem_formulation(mdao_formulation, new_tool_order)

        design_variables = self.cmdows.get_design_variables()

        for design_var in design_variables:
            fpg.mark_as_design_variable(node=design_var.parameter_uid,
                                        lower_bound=design_var.minimal_value,
                                        upper_bound=design_var.maximal_value,
                                        nominal_value=design_var.nominal_value)

        objective = self.cmdows.get_problem_role_variables('objective')
        fpg.mark_as_objective(objective[0])

        constraints = self.cmdows.get_problem_role_variables('constraint')

        for constraint in constraints:
            operator, reference = self.cmdows.get_constraint_details(constraint)
            fpg.mark_as_constraint(node=constraint,
                                   operator=operator,
                                   reference_value=reference)

        fpg.add_function_problem_roles()
        fpg.make_all_variables_valid()

        new_fpg_filename = os.path.join(cmdows_settings['destination_folder'], 'updated_fpg.xml')
        fpg.save(file_name='updated_fpg', **cmdows_settings)

        mdg, mpg = fpg.impose_mdao_architecture()

        new_mdg_filename = os.path.join(cmdows_settings['destination_folder'], 'updated_mdg.xml')
        mdg.save('updated_mdg.xml', mpg=mpg, **cmdows_settings)

        if build_dsm:
            mdg.create_dsm('XDSM_mdg', mpg=mpg, **dsm_settings)

        return_to_compatible_version(new_mdg_filename)
        return new_mdg_filename

    def build_io_files(self, surrogate_model, tool_repo):
        input_cpacs = PortableCpacs()
        for input_var in surrogate_model.all_input_variables:
            input_cpacs.update_value(input_var, 0)
        input_cpacs.save(os.path.join(tool_repo, f"{surrogate_model.uid}-input.xml"))

        output_cpacs = PortableCpacs()
        for output_var in surrogate_model.output_variables:
            output_cpacs.update_value(output_var, 0)
        output_cpacs.save(os.path.join(tool_repo, f"{surrogate_model.uid}-output.xml"))

    def rebuild_cmdows_with_surrogate(self, surrogate_model, output_file, new_rcg_file=None):
        new_rcg = RepositoryConnectivityGraph(self.fpg)
        self.fpg.load_cmdows(self.cmdows,
                             check_list=['consistent_root', 'invalid_leaf_elements'])

        self.cmdows.add_dc(uid=surrogate_model.uid,
                           id=surrogate_model.uid,
                           mode_id='1',
                           instance_id=1,
                           version=str(surrogate_model.version),
                           label=surrogate_model.uid)

        self.cmdows.add_dc_general_info(dc_uid=surrogate_model.uid,
                                        description=surrogate_model.description,
                                        status=surrogate_model.status)

        for input_variable in surrogate_model.input_variables:
            inputs_element = self.cmdows.get_element_of_uid(input_variable)
            self.cmdows.add_dc_inputs_element(dc_uid=surrogate_model.uid,
                                              inputs_element=inputs_element)
        for output_variable in surrogate_model.output_variables:
            output_variable = self.cmdows.get_element_of_uid(output_variable)
            self.cmdows.add_dc_outputs_element(dc_uid=surrogate_model.uid,
                                               outputs_element=output_variable)

        print('Stop')

    def flatten_process_hierarchy(self, process_hierarchy):
        """Workaround for KADMOS inconsistency. The process hierarchy function promises to deliver hierarchy in:
        [COOR, [OPT, [CONV, D1, D2], F1, G1, G2]]. But instead delivers in:
        [COOR, [[OPT, [[CONV, [D1, D2]], F1, G1, G2]]]].
        Fixing within KADMOS causes underlying problems, which are difficult to trace.

        This function reverts to old format.


        :param process_hierarchy: dict
        :return: corrected process_hierarchy
        """
        if not isinstance(process_hierarchy, list):
            return process_hierarchy

        flattened_subcycle = self.flatten_process_hierarchy(process_hierarchy[1][0])

        new_list = [process_hierarchy[0], flattened_subcycle]
        if len(process_hierarchy[1]) > 1:
            new_list += self.flatten_process_hierarchy(process_hierarchy[1][1:])

        return new_list

    def get_process_hierarchy(self):
        """Method to assess the hierarchy of the process based on the process lines in a ProcessGraph.

        :return: nested list with process hierarchy, e.g. [COOR, A, [OPT, [CONV, D1, D2], F1, G1, G2]]
        :rtype: list
        """
        # Find the step 0 node
        start_nodes = self.mpg.find_all_nodes(attr_cond=['process_step', '==', 0])
        assert len(start_nodes) == 1, 'There can only be one start node with process step number 0.'
        start_node = start_nodes[0]

        # Get the simple cycles in a set/list
        cycles = self.mpg.get_ordered_cycles()

        # Start process hierarchy object
        process_hierarchy = self.get_process_list_iteratively(start_node, cycles)
        return process_hierarchy

    def get_process_list_iteratively(self, cycle_node, cycles):
        """Method to obtain the process list of a collection of cycles given an iterative cycle_node. The process is
        iterative, since for every subcycle found the method is called again.

        :param cycle_node: the node that is starting and closing the cycle (e.g. coordinator, optimizer, etc.)
        :type cycle_node: str
        :param cycles: collection of cycles found in the graph
        :type cycles: list
        :return: the process list
        :rtype: list

        .. note:: Example of a process list:
            [COOR, A, [OPT, [CONV, D1, D2], F1, G1, G2]]
        """
        sub_list = [cycle_node, []]
        current_cycles = [cycle for cycle in cycles if cycle_node in cycle]
        other_cycles = [cycle for cycle in cycles if cycle_node not in cycle]
        subcycle_nodes = []
        for current_cycle in current_cycles:
            cycle_nodes = [node for node in current_cycle if node != cycle_node]
            for node in cycle_nodes:
                node_in_other_subcycles = False
                for other_cycle in other_cycles:
                    if node in other_cycle and cycle_node not in other_cycle:
                        node_in_other_subcycles = True
                # If node is in other subcycles, perform function iteratively
                # First filter out all cycles that contain the cycle_node -> filtered_cycles
                # sublist[1].append(get_process_list_iteratively(node, filtered_cycles)
                if node_in_other_subcycles:
                    if node not in subcycle_nodes:
                        filtered_cycles = list(cycles)
                        for cycle in list(filtered_cycles):
                            if cycle_node in cycle:
                                filtered_cycles.remove(cycle)
                        subcycle_nodes.append(node)
                        sub_list[1].append(self.get_process_list_iteratively(node, filtered_cycles))
                # If node is not in any other cycles, simply add to this one (at the right location based on the
                # process_step number)
                else:
                    if node not in sub_list[1]:
                        if len(sub_list[1]) == 0:  # append if list still empty
                            sub_list[1].append(node)
                        elif isinstance(sub_list[1][-1], list):  # append if last entry is a list instance
                            sub_list[1].append(node)
                        elif self.mpg.nodes[sub_list[1][-1]]['process_step'] <= self.mpg.nodes[node]['process_step']:
                            # append if last entry has equal or lower step number
                            sub_list[1].append(node)
                        else:  # insert if last entry has a higher step number
                            for i in reversed(range(len(sub_list[1]))):
                                if not isinstance(sub_list[1][i], list):
                                    if self.mpg.nodes[sub_list[1][i]]['process_step'] <= self.mpg.nodes[node][
                                        'process_step']:
                                        sub_list[1].insert(i + 1, node)
                                        break
                                    elif i == 0:
                                        sub_list[1].insert(i, node)
                                else:
                                    sub_list[1].insert(i + 1, node)
                                    break

        second_list = sub_list[1]
        sub_list.pop(1)
        sub_list = sub_list + second_list
        return sub_list

    def get_all_possible_surrogates_groups(self, allowed_complete_loops = False):
        # Determine which drivers may be replaced with SM
        candidates = list()
        allowed_drivers = ['Converger']
        forbidden_drivers = ['Optimizer', 'DoE']
        drivers = forbidden_drivers

        process_order = self.mpg.get_process_order()
        process_hierarchy = self.get_process_hierarchy()

        for discipline in process_order:
            candidates.append(tuple([discipline]))

            # Disciplines coming after current discipline automatically become candidates
            level = self.get_level_for_discipline(process_hierarchy, discipline)
            group_candidates = level[level.index(discipline) + 1:]

            if ['Converger'] + [discipline] + group_candidates == level:
                candidates.append(tuple(['Converger'] + [discipline] + group_candidates))

            # Extract first non-driver discipline in level
            idx = 0
            current_disc = level[idx]
            while current_disc in drivers:
                idx += 1
                current_disc = level[idx]

            # If this first non-driver discipline in level is current discipline, also consider level above this one
            # Is this actually true? Most likely not... You cannot break out-of-an feedback loop.
            if current_disc == discipline:
                upper_level = self.get_level_for_discipline(process_hierarchy, level)
                disciplines_to_add = upper_level[upper_level.index(level) + 1:]
                if disciplines_to_add:
                    print('Skipped')
                    # group_candidates += disciplines_to_add

            current_group = [discipline]
            for group_candidate in group_candidates:
                if isinstance(group_candidate, list):
                    if not allowed_complete_loops:
                        break
                    if not group_candidate[0] in forbidden_drivers:
                        if group_candidate[0] in drivers:
                            start_idx = 1
                        else:
                            start_idx = 0
                        current_group += group_candidate[start_idx:]
                        candidates.append(tuple(current_group))
                    else:
                        break
                else:
                    current_group.append(group_candidate)
                    candidates.append(tuple(current_group))

        return candidates

    def get_disciplines(self):
        """Extract all disciplines and assign them to a discipline object.

        :return List containing all disciplines from the cmdows file
        :rtype list[Discipline]
        """

        return self.cmdows.get_disciplines()

    def get_design_variables(self):
        """Extract design variables and their ranges from the graph

        :return: list with design variables, stored as Variable objects
        :rtype: list[Variable]
        """

        return self.cmdows.get_design_variables()

    def get_io_for_discipline(self, discipline: [str, Discipline], io: str):
        """

        :param discipline: discipline object to find in and outputs for
        :param io: 'in' or 'out': input or output
        :return: list of variables
        """

        if isinstance(discipline, Discipline):
            uid = discipline.uid
        else:
            uid = discipline

        if io == 'in':
            variables = self.cmdows.get_inputs_uids(uid)
        elif io == 'out':
            variables = self.cmdows.get_outputs_uids(uid)
        else:
            raise AssertionError("Please provide 'in' or 'out' to function")

        io_variables = list()

        for var in variables:
            if self.cmdows.is_coupling_var(var) and self.fpg is not None:
                # TODO; make independent on fpg. Maybe do some tricks with this, like create fpg from mdg.
                related_var = self.cmdows.get_related_parameter_uid(var)
                if related_var not in io_variables:
                    io_variables.append(self.cmdows.get_related_parameter_uid(var))
            else:
                if var not in io_variables:
                    io_variables.append(var)

        return io_variables

    def build_doe_for_disciplines(self, disciplines: Union[str, list[str]], output_location: str, build_dsm=True):
        if 'Converger' in disciplines:
            converged = True
        else:
            converged = False

        output_folder = os.path.join(output_location, "".join(tuple(disciplines)))
        if not os.path.isdir(output_folder):
            os.makedirs(output_folder)

        dsm_settings = dict(destination_folder=output_folder,
                            keep_tex_file=False,
                            compile_pdf=True,
                            summarize_vars=False
                            )

        rcg = RepositoryConnectivityGraph(self.fpg)
        if isinstance(disciplines, str):
            tool_order = [disciplines]
        else:
            tool_order = [discipline for discipline in disciplines if not discipline == 'Converger']

        rcg.graph['name'] = f'RCG for a DoE, as generated by SAS'
        rcg.graph['description'] = f'RCG for a DoE, as generated by SAS'

        fpg = rcg.get_fpg_by_function_nodes(tool_order)

        # This is currently implemented as a Custom Design Table, because of CMDOWS <-> Limitations
        # A manual function is implemented that 'injects' samples instead of letting RCE generate them
        # See sas.core.sas_core.SAS.deploy_custom_design_table_in_workflow
        doe_settings = dict()
        doe_settings['method'] = 'Custom design table'
        doe_settings['runs'] = 1

        fpg.graph['name'] = f'FPG for a DoE, as generated by SAS'
        fpg.graph['description'] = f'FPG for for a DoE, as generated by SAS'

        input_variables, output_variables = self.get_io_for_replaced_disciplines(tool_order, converged=converged,
                                                                                 only_non_const=True)

        for input_var in input_variables:
            fpg.mark_as_design_variable(input_var, samples=[0])

        for output_variable in output_variables:
            # Situation that occurs in non-converged loop that is surrogated
            # KADMOS cannot handle a variable to both be a design and QOI variable
            if output_variable in input_variables:
                new_node = fpg.copy_node_with_suffix(output_variable, suffix='__QOI', label_extension='__QOI')

                source_output = fpg.get_source(output_variable)
                fpg.add_edge(source_output, new_node)
                fpg.remove_edge(source_output, output_variable)

                for target in fpg.get_targets(output_variable):
                    if target in tool_order[tool_order.index(source_output)+1:]:
                        fpg.add_edge(new_node, target)
                        fpg.remove_edge(output_variable, target)
                fpg.mark_as_qoi(new_node)
            else:
                fpg.mark_as_qoi(output_variable)

        if converged:
            doe_architecture = 'converged-DOE-GS'
        else:
            doe_architecture = 'unconverged-DOE'

        fpg.add_problem_formulation(doe_architecture, tool_order, doe_settings=doe_settings)
        fpg.make_all_variables_valid()

        mdg, mpg = fpg.impose_mdao_architecture()
        cmdows_settings = dict(file_type='cmdows',
                               destination_folder=output_folder,
                               creator='Costijn de Priester',
                               version='0.1',
                               pretty_print=True,
                               integrity=False)

        output_cmdows_name = f'{"".join(tuple(tool_order))}_DoE'

        output_file = os.path.join(output_folder, f'{output_cmdows_name}.xml')
        mdg.save(output_cmdows_name, mpg=mpg, description='DoE generated by SAS', **cmdows_settings)
        mdg.create_dsm('XDSM_mdg', mpg=mpg, **dsm_settings)
        return_to_compatible_version(output_file)

        return output_file

    def apply_labels(self, labels):
        for node_var, node in self.fpg.nodes.items():
            if node_var in labels:
                node['label'] = labels[node_var]
        for node_var, node in self.mdg.nodes.items():
            if node_var in labels:
                node['label'] = labels[node_var]

    def convert_to_doe(self,
                       output_cmdows_folder: str,
                       output_cmdows_name: str,
                       n_samples: int,
                       design_variables: list[Variable],
                       cmdows_fpg_file=None,
                       build_dsm=False):

        cmdows_settings = dict(file_type='cmdows',
                               destination_folder=output_cmdows_folder,
                               creator='Surrogate Advisory System',
                               version='0.1',
                               pretty_print=True,
                               integrity=False)

        dsm_settings = dict(destination_folder=output_cmdows_folder,
                            keep_tex_file=False,
                            compile_pdf=True,
                            summarize_vars=False
                            )

        if self.fpg is None and cmdows_fpg_file is None:
            raise AssertionError("Please provide an FPG file to generate DoE files")

        doe_architecture = 'converged-DOE-GS-LH'
        process_order = self.mpg.get_process_order()

        now = datetime.now()
        timestamp = now.strftime("%d/%m/%Y, %H:%M:%S")

        # Nasty workaround due to bug in KADMOS
        # KADMOS does not process copied variables right the first time, reprocesses them correctly when reloading
        # Not doing this leads to file unable to be loaded into RCE

        fpg_filename = f'{output_cmdows_name}_fpg'
        fpg_file = os.path.join(output_cmdows_folder, f'{fpg_filename}.xml')
        self.fpg.save(fpg_filename, **cmdows_settings)
        doe_fpg = FundamentalProblemGraph(graph.load(file_name=fpg_file,
                                                     check_list=['consistent_root', 'invalid_leaf_elements']))

        doe_fpg.graph['name'] = f'FPG - {doe_architecture}'
        doe_fpg.graph['description'] = 'Automatically generated DoE based on the MPG, MDG and FPG of the file: {}' \
                                       f'Generated by the Surrogate Assistance System, on {timestamp}.'

        # Hardcoded now. Make dependent on the selected PIDO
        doe_settings = dict()
        doe_settings['method'] = 'Latin hypercube design'
        doe_settings['seed'] = 5
        doe_settings['runs'] = n_samples

        # Design variables stay design variables in the DoE
        for design_var in design_variables:
            doe_fpg.mark_as_design_variable(node=design_var.parameter_uid,
                                            lower_bound=design_var.minimal_value,
                                            upper_bound=design_var.maximal_value,
                                            nominal_value=design_var.nominal_value)

        # Constraints and objective value become QOI's in DoE
        constraint_variables = self.cmdows.get_problem_role_variables('constraint')
        objective_variables = self.cmdows.get_problem_role_variables('objective')

        for var in (constraint_variables + objective_variables):
            doe_fpg.mark_as_qoi(var)

        doe_fpg.add_problem_formulation(doe_architecture, process_order, doe_settings=doe_settings)


        mdg, mpg = doe_fpg.impose_mdao_architecture()

        mdg.graph['name'] = 'DoE - Generated by SAS'
        mdg.graph['description'] = 'First automatically generated DoE by SAS!'

        mdg_file = os.path.join(output_cmdows_folder, f'{output_cmdows_name}.xml')
        mdg.save(output_cmdows_name, mpg=mpg, description='First DoE generated by SAS', **cmdows_settings)
        return_to_compatible_version(mdg_file)

        if build_dsm:
            mdg.create_dsm(output_cmdows_name, mpg=mpg, **dsm_settings)

class CMDOWSExtension(CMDOWS):
    def __init__(self, file_path=None):
        """Init function as used by super class, but no element can be passed. Should never be used in this app

        :param file_path: file_path to existing CMDOWS file. Get's loaded in if already existing
        :type file_path: str
        """
        CMDOWS.__init__(self, file_path)

    def get_el_contents(self, xpath: str, expected_type: type, root_el=None):
        """Obtain contents of a certain element if it exists, else return empty value for type

        :param xpath: XML path to certain element relative to root
        :type xpath: str
        :param expected_type: expected return type, so a str, int, double, etc.
        :type xpath: type
        :param root_el: root element of the XML Document, xpath is relative from here
        :type root_el: Element

        :returns: value of requested parameter if exists, else '', 0 or 0.0 depending on type
        :rtype: expected_type
        """

        if root_el is not None:
            el = root_el
        else:
            el = self.root

        text_list = el.xpath(f'{xpath} /text()')

        if len(text_list) == 1:
            return expected_type(text_list[0])
        else:
            if expected_type == str:
                return ''
            elif expected_type == float:
                return 0.0
            elif expected_type == int:
                return 0
            else:
                return None

    def get_disciplines(self):
        """Extract all disciplines and assign them to a discipline object.

        TODO: Check if this can be done in a nicer way. KADMOS should have this functionality

        :return List containing all disciplines from the cmdows file
        :rtype list[Discipline]
        """
        from sas.core.discipline import Discipline

        design_comp_uid_list = self.get_design_competences_uids()
        disciplines = list()
        for uid in design_comp_uid_list:
            el = self.get_element_of_uid(uid)

            # id = str(el.xpath('ID/text()')[0])
            id = self.get_el_contents('ID', str, el)
            description = self.get_el_contents('metadata/generalInfo/description', str, el)
            status = self.get_el_contents('metadata/generalInfo/status', str, el)
            command = self.get_el_contents('metadata/executionInfo/localComponentInfo/executionDetails/command', str,
                                           el)
            version = self.get_el_contents('version', float, el)

            disciplines.append(Discipline(kadmos_uid=uid,
                                          id=id,
                                          description=description,
                                          command=command,
                                          version=version,
                                          status=status))

        return disciplines

    def get_design_variables(self):
        """Extract design variables and their ranges from the CMDOWS file

        TODO: Check if this can be done in a nicer way. KADMOS should have this functionality

        :return: list with design variables, stored as Variable objects
        :rtype: list[Variable]
        """
        from sas.core.variable import Variable
        path = '/cmdows/problemDefinition/problemRoles/parameters/designVariables/designVariable'
        des_variable_elements = self.root.xpath(path)

        design_variables = list()

        for el in des_variable_elements:
            design_variables.append(Variable(uid=str(el.attrib['uID']),
                                             parameter_uid=self.get_el_contents('parameterUID', str, el),
                                             nominal_value=self.get_el_contents('nominalValue', float, el),
                                             minimal_value=self.get_el_contents('validRanges/limitRange/minimum', float,
                                                                                el),
                                             maximal_value=self.get_el_contents('validRanges/limitRange/maximum', float,
                                                                                el)
                                             ))

        return design_variables

    def get_header_info(self, field: str):
        """Extract latest information from cmdows header and return.
        Scans the available updates and returns the latest available data

        :param field: requested field to extract from xml, e.g. 'creator' or 'cmdowsVersion'
        :type field: str

        :return: requested header information
        :rtype: str
        """

        base_path = '/cmdows/header'
        base_el = self.root.xpath(base_path)

        assert len(base_el) == 1, "Multiple headers are provided in CMDOWS file. Check file structure!"
        base_el = base_el[0]

        result = base_el.findall(field)

        if len(result) == 1:
            field_data = result[0].text
            return field_data

        return ''
        # TODO: Implement functionality to return latest if needed

    def get_problem_info(self, field):
        """Extract problem definition information from the cmdows file

        :param field: requested field to extract from xml, e.g. 'creator' or 'cmdowsVersion'
        :type field: str

        :return: requested header information
        :rtype: str
        """
        base_path = '/cmdows/problemDefinition/problemFormulation'

        base_el = self.root.xpath(base_path)

        assert len(base_el) == 1, "Multiple architectures are provided in CMDOWS file. Check cmdows structure!"
        base_el = base_el[0]

        result = base_el.findall(field)
        assert len(result) == 1, "Multiple fields available for architecture info. Check cmdows structure!"

        field_data = result[0].text
        return field_data

    def is_coupling_var(self, xpath):
        """Check if provided variable is a coupling (or copy) variable

        TODO: Check if robust enough, might need to be extended

        :param xpath: xpath of variable to be checked
        :type xpath: str
        :return: true if coupling var, valse if not
        :rtype: bool
        """

        return 'architectureNodes' in xpath

    def get_related_parameter_uid(self, var_uid: str):
        """Find the element corresponding to the provided uid, and return its related parameter"""

        el = self.get_element_of_uid(var_uid)

        # assert len(el) == 1, f"Too many or no results ({len(el)}) for var_uid = {var_uid}, expected one result."

        related_uid = self.get_el_contents('relatedParameterUID', str, el)

        return related_uid

    def get_constraint_details(self, constraint_par_uid):
        """Get the constraint operator and reference value for a constraint variable

        :param constraint_par_uid: parameter uid of the constraint to check
        :return: operator, reference_value
        """
        xpath = '/cmdows/problemDefinition/problemRoles/parameters/constraintVariables'

        el = self.root.xpath(xpath)

        for var_el in el[0].iterchildren():
            if self.get_el_contents('parameterUID', str, var_el) == constraint_par_uid:
                operator = self.get_el_contents('constraintOperator', str, var_el)
                reference_value = self.get_el_contents('referenceValue', float, var_el)

                return operator, reference_value

    def get_problem_role_variables(self, var_type: str):
        """Get either the objective variables or the constraint variables from the cmdows file

        :param var_type: problem variable type, either 'objective' or 'constraint'
        :type var_type: str
        :return: list containing uids of the requested variables
        :rtype: list[str]
        """

        xpath = ''
        if var_type == 'objective':
            xpath = '/cmdows/problemDefinition/problemRoles/parameters/objectiveVariables'
        elif var_type == 'constraint':
            xpath = '/cmdows/problemDefinition/problemRoles/parameters/constraintVariables'
        else:
            AssertionError(f'Provide a valid variable type (\'objective\' or \'constraint\'), currently {var_type}')

        el = self.root.xpath(xpath)

        assert len(el) <= 1, '"/cmdows/executableBlocks/designCompetences" is not a unique XPath. ' \
                             'Check given CMDOWS file structure.'

        uid_list = []
        for var_el in el[0].iterchildren():
            uid_list.append(self.get_el_contents('parameterUID', str, var_el))

        return uid_list

