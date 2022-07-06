function load_constraint(cpacs_in, cpacs_out)

dataSchema = readstruct(cpacs_in);

% Extract parameters
fuel_flag = dataSchema.errorFlags.fuel;
aero_flag = dataSchema.errorFlags.aero;
str_flag = dataSchema.errorFlags.struct;

if fuel_flag || aero_flag || str_flag
    disp('There are errors in the calculations')
    fail_load_constraint(dataSchema, cpacs_out)
    return
end


initial_load = dataSchema.constraints.constants.initial_load;

inner_chord = dataSchema.wing.inner.chord;
inner_sweep = dataSchema.wing.inner.sweep;
inner_span = dataSchema.wing.inner.span;

outer_span = dataSchema.wing.outer.span;
outer_chord = dataSchema.wing.outer.chord;

% Calculate area
mid_chord = inner_chord-sin(inner_sweep*(pi/180))*inner_span;
wing_area = 2*(0.5*(inner_chord+mid_chord)*inner_span + 0.5*(mid_chord+outer_chord)*outer_span);

% Calculate mass
W_fuel = dataSchema.weights.fuel;
W_aw = dataSchema.weights.a_w;
W_str_wing = dataSchema.weights.str_wing;

W_to_max = W_fuel + W_aw + W_str_wing;

% Do calculations
load_const = W_to_max/wing_area - initial_load;

% Write results
dataSchema.constraints.load = load_const;

writestruct(dataSchema, cpacs_out, 'StructNodeName', 'dataSchema');
cd ..
cd ..
end

function fail_load_constraint(dataSchema, cpacs_out)
    warning('Invalid values passed to constraint. Constraint set to positive value')
    dataSchema.constraints.load = 100;
    writestruct(dataSchema, cpacs_out, 'StructNodeName', 'dataSchema');
    cd ..
    cd ..
end

