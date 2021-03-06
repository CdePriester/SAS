function pre_calcs(cpacs_in, cpacs_out)
% Run from CMD:
% "C:\Program Files\MATLAB\R2021a\bin\matlab.exe" -batch "pre_calcs('mtom_cpacs_in.xml', 'test_out.xml'); exit"

addpath('storage')

%run init_cpacs.m

%cpacs = xml2struct(cpacs_in);
dataSchema = readstruct(cpacs_in);

%% Initial values in CPACS
% All values will be hardcoded for the A300
dataSchema.constants.h_cruise = 10668;
dataSchema.constants.T_cruise = 208.8;
dataSchema.constants.n_max = 2.5;
dataSchema.constants.n_cruise = 1;
dataSchema.constants.visc_kin_cruise = 3.80524E-5;
dataSchema.constants.rho_cruise = 0.379597;

dataSchema.constants.C_D_aw = 0;
dataSchema.constants.C_D_aw_area = 0;

kappa = 1.4;
R = 287;
T_cruise = dataSchema.constants.T_cruise;
dataSchema.constants.c_sound = sqrt(kappa*R*T_cruise);

dataSchema.performance.V_cruise =  450*0.5144;
dataSchema.performance.V_max = 480 * 0.5144;
dataSchema.performance.range_cruise = 4000*1852;
dataSchema.performance.C_T = 1.8639E-4;

dataSchema.wing.inner.chord = 9.4; % Root chord
dataSchema.wing.inner.span = 9.06; % Root span
dataSchema.wing.inner.sweep = 22.05;

dataSchema.wing.mid.twist = 0;

dataSchema.wing.outer.chord = 2.75; % Tip chord
dataSchema.wing.outer.span = 13.36;
dataSchema.wing.outer.sweep = 30.5;
dataSchema.wing.outer.twist = 0;

% Calculate area
mid_chord = dataSchema.wing.inner.chord-sin(dataSchema.wing.inner.sweep*(pi/180))*dataSchema.wing.inner.span;
wing_area = 2*(0.5*(dataSchema.wing.inner.chord+mid_chord)*dataSchema.wing.inner.span + 0.5*(mid_chord+dataSchema.wing.outer.chord)*dataSchema.wing.outer.span);

dataSchema.weights.to_max = 170500*9.81; % From data

% Initial guesses
dataSchema.weights.str_wing = 23853*9.81;
dataSchema.weights.fuel = 56330*9.81; 

%% Calculate initial airfoil
input_airfoil = 'storage/withcomb135.dat';
standard_coord = read_airfoil_dat(input_airfoil);

% Scale to 14% and 8% root and tip thicknesses respectively
[root_coord, tip_coord] = scale_airfoil(standard_coord, 0.12, 0.08);

n_coeff = 12;
cst_root = find_CST(root_coord, n_coeff);
cst_tip = find_CST(tip_coord, n_coeff);

for idx = 1:n_coeff
    dataSchema.wing.inner.foil.(strcat('b_', num2str(idx))) = cst_root(idx);
    dataSchema.wing.outer.foil.(strcat('b_', num2str(idx))) = cst_tip(idx);
end

temp_file = 'temp/temp_cpacs.xml';
temp_file_res = 'temp/temp_cpacs_out.xml';

error_fuel = 1;
error_W_str = 1;

%% Converge loads, weights and structurals for initial guess
while error_fuel > 0.002 || error_W_str > 0.002
    % Store to find convergence
    W_str_wing_prev = dataSchema.weights.str_wing;
    
    % Derive W_a_w from guesses for fuel and str_wing
    W_a_w = dataSchema.weights.to_max-dataSchema.weights.fuel-dataSchema.weights.str_wing;
    dataSchema.weights.a_w = W_a_w;
    
    %% Run sequence
    writestruct(dataSchema, temp_file, 'StructNodeName', 'dataSchema');
    Q3D_cpacs(temp_file, temp_file_res, 0);
    cd C:\Dev\Thesis\surrogateassistancesystem\tool_repository\mtom
    dataSchema = readstruct(temp_file_res);

    writestruct(dataSchema, temp_file, 'StructNodeName', 'dataSchema');
    EMWET_cpacs(temp_file, temp_file_res);
    cd C:\Dev\Thesis\surrogateassistancesystem\tool_repository\mtom
    dataSchema = readstruct(temp_file_res);

    writestruct(dataSchema, temp_file, 'StructNodeName', 'dataSchema');
    Q3D_cpacs(temp_file, temp_file_res, 1);
    cd C:\Dev\Thesis\surrogateassistancesystem\tool_repository\mtom
    dataSchema = readstruct(temp_file_res);
    
    %% Extract parameters to calculate C_D of structure
    
    C_L_wing = dataSchema.wing.C_L;
    C_D_wing = dataSchema.wing.C_D;
    
    % CL/CD is assumed to be constant at 16, which gives:
    C_D_aw = (C_L_wing-16*C_D_wing)/16;
    C_D = (C_D_aw+C_D_wing);
    
    %% Calculate weights
    
    range_cruise = dataSchema.performance.range_cruise;
    C_T = dataSchema.performance.C_T;
    V_cruise = dataSchema.performance.V_cruise;
    
    W_ratio = exp(range_cruise*C_T/V_cruise*C_D/C_L_wing);
    W_fuel = (1-0.938*1/W_ratio)*dataSchema.weights.to_max;
    
    % Calculate error based on convergence between old and new W_fuel value
    error_fuel = abs(W_fuel-dataSchema.weights.fuel)/W_fuel;
    error_W_str = abs(W_str_wing_prev-dataSchema.weights.str_wing)/W_str_wing_prev;
    
    % Write new values to CPACS
    dataSchema.constants.C_D_aw_area = wing_area;
    dataSchema.constants.C_D_aw = C_D_aw;
    dataSchema.weights.fuel = W_fuel;
    dataSchema.weights.a_w = W_a_w;
    
    dataSchema.constraints.constants.initial_load = dataSchema.weights.to_max/wing_area;
end

%Init normalized variables
normalized = struct();
% for idx_coeff = 1:n_coeff
%      fieldname = strcat('b_', num2str(idx_coeff));
%      normalized.wing.inner.foil.(fieldname) = 1;
%      normalized.wing.outer.foil.(fieldname) = 1;
% end
normalized.wing.inner.sweep = 1;
normalized.wing.inner.chord = 1;
normalized.wing.mid.twist = 1;
normalized.wing.outer.span = 1;
normalized.wing.outer.twist=1;
normalized.wing.outer.chord = 1;
normalized.wing.outer.sweep = 1;

for idx = 1:n_coeff
    normalized.wing.inner.foil.(strcat('b_', num2str(idx))) = 1;
    normalized.wing.outer.foil.(strcat('b_', num2str(idx))) = 1;
end

dataSchema.normalized = normalized;

% Finished. Values have converged, now a gues for W_a_w has been made
writestruct(dataSchema, cpacs_out, 'StructNodeName', 'dataSchema');

end