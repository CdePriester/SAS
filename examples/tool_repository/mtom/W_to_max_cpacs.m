function W_to_max_cpacs(cpacs_in, cpacs_out)

dataSchema = readstruct(cpacs_in);

% Extract parameters
W_fuel = dataSchema.weights.fuel;
W_aw = dataSchema.weights.a_w;
W_str_wing = dataSchema.weights.str_wing;

% Objective calculation
W_to_max = W_fuel + W_aw + W_str_wing;

% Initial value
original_schema = readstruct('prepared_mtom_cpacs.xml');
W_to_max_og = original_schema.weights.to_max;

% Write output
dataSchema.weights.to_max = W_to_max/W_to_max_og;

writestruct(dataSchema, cpacs_out, 'StructNodeName', 'dataSchema');
cd ..
cd ..
end

