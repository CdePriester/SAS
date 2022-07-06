clear dataSchema;

%% Overall dataschema

dataSchema = struct();

dataSchema.description.name = 'A300';
dataSchema.description.comments = 'Selected from old MDO project 19/20';

% Constants
constants.E_al = 70E9;
constants.sig_yield_tens = 295E6;
constants.sig_yield_comp = 295E6;
constants.rho_al = 2800;
constants.n_max = 0;
constants.n_cruise = 0;
constants.rib_pitch = 0.5;
constants.eta_panel = 0.96;
constants.rho_fuel = 0.81715E3;
constants.f_tank = 0.93;
constants.h_cruise = 0;
constants.T_cruise = 0;
constants.rho_cruise = 0;
constants.visc_kin_cruise = 0;
constants.c_sound = 0;
dataSchema.constants.C_D_aw = 0;

dataSchema.constants = constants;

section.foil.b_1 = 0;
section.sweep = 0;
section.twist = 0;
section.chord = 0;
section.dihedral = 0;
section.span = 0;


dataSchema.wing.inner = section;
dataSchema.wing.outer = section;
dataSchema.wing.C_L = 0;
dataSchema.wing.C_D = 0;

%dataSchemma.wing.area = 0;

% Weights
weights.to_max = 0;
weights.a_w = 0;
weights.fuel = 0;
weights.str_wing = 0;
weights.des = 0;

dataSchema.weights = weights;

% Performance
performance.range = 0;
performance.V_cruise = 0;
performance.V_max = 0;
performance.C_T = 0;

dataSchema.performance = performance;

% Constraints
constraints.constants.initial_load = 0;
constraints.load = 0;
constraints.fuel = 0;

dataSchema.constraints = constraints;
writestruct(dataSchema, 'empty_mtom_cpacs.xml', 'StructNodeName', 'dataSchema')

%% Tool specific cpacs
% StructuralAnalysis_in
name = 'StructuralAnalysis-input.xml';
dataSchema = struct();
dataSchema.weights.fuel = 0;
dataSchema.weights.str_wing = 0;
dataSchema.weights.a_w = 0;
dataSchema.constants.n_max = 0;

dataSchema.wing.inner.span = 0;
dataSchema.wing.inner.sweep = 0;
dataSchema.wing.inner.chord = 0;
dataSchema.wing.outer.span = 0;
dataSchema.wing.outer.sweep = 0;
dataSchema.wing.outer.chord = 0;

dataSchema.wing.cm_c4 = 0;
dataSchema.wing.ccl = 0;
dataSchema.wing.Yst = 0;

dataSchema.constants.E_al = 0;
dataSchema.constants.rho_al = 0;
dataSchema.constants.sig_yield_tens = 0;
dataSchema.constants.sig_yield_comp = 0;

dataSchema.constants.eta_panel = 0;
dataSchema.constants.rib_pitch = 0;

dataSchema.performance.V_max = 0;
dataSchema.constants.rho_cruise = 0;

n_coeff = 12;
for idx_coeff = 1:n_coeff
     fieldname = strcat('b_', num2str(idx_coeff));
     
     dataSchema.wing.inner.foil.(fieldname) = 0;
     dataSchema.wing.outer.foil.(fieldname) = 0;
end
writestruct(dataSchema, name, 'StructNodeName', 'dataSchema')

% StructuralAnalysis_out
name = 'StructuralAnalysis-output.xml';
dataSchema = struct();
dataSchema.weights.str_wing = 0;
dataSchema.errorFlags.struct = 0;
writestruct(dataSchema, name, 'StructNodeName', 'dataSchema')

% AeroAnalysis
name = 'AeroAnalysis-input.xml';
dataSchema = struct();

dataSchema.constants.C_D_aw = 0;
dataSchema.constants.C_D_aw_area = 0;

dataSchema.wing.inner.span = 0;
dataSchema.wing.inner.sweep = 0;
dataSchema.wing.inner.chord = 0;

dataSchema.wing.mid.twist = 0;

dataSchema.wing.outer.span = 0;
dataSchema.wing.outer.sweep = 0;
dataSchema.wing.outer.chord = 0;
dataSchema.wing.outer.twist = 0;


dataSchema.weights.fuel = 0;
dataSchema.weights.str_wing = 0;
dataSchema.weights.a_w = 0;

dataSchema.constants.c_sound = 0;

n_coeff = 12;
for idx_coeff = 1:n_coeff
     fieldname = strcat('b_', num2str(idx_coeff));
     
     dataSchema.wing.inner.foil.(fieldname) = 0;
     dataSchema.wing.outer.foil.(fieldname) = 0;
end

dataSchemaLoad = dataSchema; % Until here both have same inputs

dataSchema.performance.V_cruise = 0;
dataSchema.constants.rho_cruise = 0;
dataSchema.constants.h_cruise = 0;
dataSchema.constants.visc_kin_cruise = 0;
dataSchema.constants.n_cruise = 0;
writestruct(dataSchema, name, 'StructNodeName', 'dataSchema')

name = 'AeroAnalysis-output.xml';
dataSchema = struct();
dataSchema.wing.L_D = 0;
dataSchema.errorFlags.aero = 0;
writestruct(dataSchema, name, 'StructNodeName', 'dataSchema')

% LoadAnalysis
name = 'LoadAnalysis-input.xml';
dataSchema = dataSchemaLoad;
dataSchema.performance.V_max = 0;
dataSchema.constants.rho_cruise = 0;
dataSchema.constants.h_cruise = 0;
dataSchema.constants.visc_kin_cruise = 0;
dataSchema.constants.n_max = 0;
writestruct(dataSchema, name, 'StructNodeName', 'dataSchema')

name = 'LoadAnalysis-output.xml';
dataSchema = struct();
dataSchema.wing.cm_c4 = 0;
dataSchema.wing.ccl = 0;
dataSchema.wing.Yst = 0;
writestruct(dataSchema, name, 'StructNodeName', 'dataSchema')

% PerformanceAnalysis
name = 'PerformanceAnalysis-input.xml';
dataSchema = struct();
dataSchema.wing.L_D = 0;
dataSchema.performance.range_cruise = 0;
dataSchema.performance.C_T = 0;
dataSchema.performance.V_cruise = 0;
dataSchema.weights.fuel = 0;
dataSchema.weights.a_w = 0;
dataSchema.weights.str_wing = 0;

writestruct(dataSchema, name, 'StructNodeName', 'dataSchema')

name = 'PerformanceAnalysis-output.xml';
dataSchema = struct();
dataSchema.weights.fuel = 0;
dataSchema.errorFlags.fuel = 0;
writestruct(dataSchema, name, 'StructNodeName', 'dataSchema')

% WeightAnalysis
name = 'WeightAnalysis-input.xml';
dataSchema = struct();
dataSchema.weights.fuel = 0;
dataSchema.weights.a_w = 0;
dataSchema.weights.str_wing = 0;
writestruct(dataSchema, name, 'StructNodeName', 'dataSchema')

name = 'WeightAnalysis-output.xml';
dataSchema = struct();
dataSchema.weights.to_max = 0;
writestruct(dataSchema, name, 'StructNodeName', 'dataSchema');

% DeNormalizer
name = 'Denormalizer-input.xml';
normalized = struct();
normalized.wing.inner.sweep = 0;
normalized.wing.inner.chord = 0;
normalized.wing.mid.twist=0;
normalized.wing.outer.twist=0;
normalized.wing.outer.span = 0;
normalized.wing.outer.chord = 0;
normalized.wing.outer.sweep = 0;
dataSchema = struct();
dataSchema.normalized = normalized;
writestruct(dataSchema, name, 'StructNodeName', 'dataSchema');

name = 'Denormalizer-output.xml';
dataSchema = struct();
dataSchema = normalized;
writestruct(dataSchema, name, 'StructNodeName', 'dataSchema');

% FuelConstraint
name = 'FuelConstraint-input.xml';
dataSchema = struct();
dataSchema.errorFlags.fuel = 0;
dataSchema.errorFlags.aero = 0;
dataSchema.errorFlags.struct = 0;

dataSchema.wing.inner.span = 0;
dataSchema.wing.inner.sweep = 0;
dataSchema.wing.inner.chord = 0;
dataSchema.wing.outer.span = 0;
dataSchema.wing.outer.chord = 0;
n_coeff = 12;
for idx_coeff = 1:n_coeff
     fieldname = strcat('b_', num2str(idx_coeff));
     
     dataSchema.wing.inner.foil.(fieldname) = 0;
     dataSchema.wing.outer.foil.(fieldname) = 0;
end
dataSchema.constants.rho_fuel = 0;
dataSchema.weights.fuel = 0;
writestruct(dataSchema, name, 'StructNodeName', 'dataSchema');

name = 'FuelConstraint-output.xml';
dataSchema = struct();
dataSchema.constraints.fuel = 0;
writestruct(dataSchema, name, 'StructNodeName', 'dataSchema');

% WingloadingConstraint
name = 'WingloadingConstraint-input.xml';
dataSchema = struct();

dataSchema.errorFlags.fuel = 0;
dataSchema.errorFlags.aero = 0;
dataSchema.errorFlags.struct = 0;

dataSchema.wing.inner.chord = 0;
dataSchema.wing.inner.sweep = 0;
dataSchema.wing.inner.span = 0;
dataSchema.wing.outer.span = 0;
dataSchema.wing.outer.chord = 0;

dataSchema.weights.fuel = 0;
dataSchema.weights.a_w = 0;
dataSchema.weights.str_wing = 0;
dataSchema.constraints.constants.initial_load = 0;

writestruct(dataSchema, name, 'StructNodeName', 'dataSchema');

name = 'WingloadingConstraint-output.xml';
dataSchema = struct();
dataSchema.constraints.load = 0;
writestruct(dataSchema, name, 'StructNodeName', 'dataSchema');

