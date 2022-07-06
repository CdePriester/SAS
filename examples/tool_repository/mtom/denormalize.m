function denormalize(cpacs_in, cpacs_out)
% Take an input cpacs and denormalize it using the initial values
dataSchema_initial = readstruct('prepared_mtom_cpacs.xml');
dataSchema_in = readstruct(cpacs_in);
dataSchema_out = dataSchema_in;

cmdows_in = readstruct("CMDOWS\MDG-MDF-GS_new.xml");
design_vars = cmdows_in.problemDefinition.problemRoles.parameters.designVariables.designVariable;

design_var_list = {};
for idx = 1:length(design_vars)
    design_var_list{end+1} = design_vars(idx).parameterUID;
end

for idx_var = 1:length(design_vars)
    design_var = design_var_list{idx_var};
    
    path = strsplit(design_var, '/');
    path = cellstr(path(3:end));
    
    initial_value = getfield(dataSchema_initial, path{2:end});
    normalized_value = getfield(dataSchema_in, path{:});
    if ~contains(design_var, 'twist')
        dataSchema_out = setfield(dataSchema_out, path{2:end}, initial_value*normalized_value);
    else
        dataSchema_out = setfield(dataSchema_out, path{2:end}, 11.6667*normalized_value-11.6667);
    end
end    

writestruct(dataSchema_out, cpacs_out, 'StructNodeName', 'dataSchema')
cd ..
cd ..
end