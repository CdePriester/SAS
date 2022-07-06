function fuel_constraint(cpacs_in, cpacs_out)

addpath(genpath('storage'))

dataSchema = readstruct(cpacs_in);
fuel_flag = dataSchema.errorFlags.fuel;
aero_flag = dataSchema.errorFlags.aero;
str_flag = dataSchema.errorFlags.struct;

if fuel_flag || aero_flag || str_flag
    disp('There are errors in the calculations')
    fail_fuel_constraint(dataSchema, cpacs_out)
    return
end


inner_chord = dataSchema.wing.inner.chord;
inner_span = dataSchema.wing.inner.span;
inner_sweep = dataSchema.wing.inner.sweep;

outer_chord = dataSchema.wing.outer.chord;
outer_span = dataSchema.wing.outer.span;

n_coeff = numel(fieldnames(dataSchema.wing.outer.foil));

cst_root = zeros(1, n_coeff);
cst_tip = zeros(1, n_coeff);

for idx_coeff = 1:n_coeff
    fieldname = strcat('b_', num2str(idx_coeff));

    cst_root(idx_coeff) = dataSchema.wing.inner.foil.(fieldname);
    cst_tip(idx_coeff) = dataSchema.wing.outer.foil.(fieldname);
end

rho_fuel = dataSchema.constants.rho_fuel;
W_fuel = dataSchema.weights.fuel;

if W_fuel < 0
    disp('w_fuel < 0')
    fail_fuel_constraint(dataSchema, cpacs_out)
    return
end

mid_chord = inner_chord-sin(inner_sweep*(pi/180))*inner_span;

tank_vol = tank_volume( cst_root,...
                        cst_tip,...
                        [inner_chord, mid_chord, outer_chord],...
                        [inner_span, outer_span]);

tank_vol = tank_vol*0.93 + 10; % Assume 93% efficiency in tank, and 10 m^3 fuel tank in fuselage
                    
fuel_vol = W_fuel/(rho_fuel*9.81);

dataSchema.constraints.fuel = fuel_vol-tank_vol;

writestruct(dataSchema, cpacs_out, 'StructNodeName', 'dataSchema');
cd ..
cd ..
end

function fail_fuel_constraint(dataSchema, cpacs_out)
    warning('Failing fuel constraint; setting value to 100.')
    dataSchema.constraints.fuel = 100;
    writestruct(dataSchema, cpacs_out, 'StructNodeName', 'dataSchema');
    cd ..
    cd ..
end
