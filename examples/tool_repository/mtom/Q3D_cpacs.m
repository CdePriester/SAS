function Q3D_cpacs(cpacs_in, cpacs_out, mode)
%Q3D_CPACS Run Q3D for a certain cpacs input file
%   Run Q3D in different modes.
%   Modes:  - 0: Maximum loads calculation
%                   - Inviscid
%                   - V = V_max
%                   - N = N_max
%                   - W = W_to
%           - 1: Aero cruise calculation
%                   - Viscid
%                   - V = V_cruise
%                   - N = N_cruise
%                   - W = W_des


%% Extracting and deriving parameters
%% Extracting and deriving parameters
dataSchema = readstruct(cpacs_in);

if mode == 1
    [ds_low, ds_high] = create_trust_region(dataSchema, 0.01);

    dataSchemas = cell(3, 1);
    dataSchemas{1} = ds_low;
    dataSchemas{2} = dataSchema;
    dataSchemas{3} = ds_high;

    results = cell(3, 1);
    fail_res = boolean([0, 0, 0]);
    res.CLwing = [];
    res.CDwing = [];
    res.L_D = [];
    parfor idx = 1:length(results)
        [result{idx}, fail_res(idx)] = execute_Q3D(dataSchemas{idx}, mode);
    end
    for idx = 1:length(results)
        res.CLwing(idx) = result{idx}.CLwing;
        res.CDwing(idx) = result{idx}.CDwing;
        res.L_D(idx) = result{idx}.L_D;
    end
    failed = any(fail_res);
    res.CLwing = mean(res.CLwing);
    res.CDwing = mean(res.CDwing);
    res.L_D = mean(res.L_D);
else
   res = execute_Q3D(dataSchema, mode); 
end
if mode == 0
    fields = fieldnames(res.Wing);

    for idx = 1:length(fields)
        fn = fields{idx};
        dataSchema.wing.(fn) = res.Wing.(fn);
    end
elseif mode == 1
    if isnan(res.L_D) || failed
        if failed
            warning('Some sections failed to converge, so:')
        end
        warning('Setting L_D to = -1')
        dataSchema.wing.L_D = -1;
        dataSchema.errorFlags.aero = 1;
    else
        dataSchema.wing.L_D = res.L_D;
        dataSchema.wing.C_L = res.CLwing;
        dataSchema.wing.C_D = res.CDwing;
        dataSchema.errorFlags.aero = 0;
    end
end
writestruct(dataSchema, cpacs_out, 'StructNodeName', 'dataSchema');
cd ..
cd ..
end

function [res, failed] = execute_Q3D(dataSchema, mode)
job_id = get(getCurrentTask(), 'ID');
stor_path = sprintf('storage%d', job_id);
addpath(genpath(stor_path))

C_D_aw = dataSchema.constants.C_D_aw;
C_D_aw_area = dataSchema.constants.C_D_aw_area;

inner_span = dataSchema.wing.inner.span;
inner_sweep = dataSchema.wing.inner.sweep;
inner_chord = dataSchema.wing.inner.chord;
inner_twist = 0;

mid_twist = dataSchema.wing.mid.twist;

x_mid_wing = inner_span*tan(inner_sweep*(pi/180));
y_mid_wing = inner_span;

outer_span = dataSchema.wing.outer.span;
outer_sweep = dataSchema.wing.outer.sweep;
outer_chord = dataSchema.wing.outer.chord;
outer_twist = dataSchema.wing.outer.twist;

x_tip = x_mid_wing + outer_span*tan(outer_sweep*(pi/180));
y_tip = y_mid_wing+outer_span;

% Added sinus term. Was missing. Geometry is quite clear on this
mid_chord = inner_chord-sin(inner_sweep*(pi/180))*inner_span;

wing_area = 2*(0.5*(inner_chord+mid_chord)*inner_span + 0.5*(mid_chord+outer_chord)*outer_span);
taper_ratio = outer_chord/inner_chord;

MAC = inner_chord*2/3*(2/3)*((1+taper_ratio+taper_ratio^2)/(1+taper_ratio));

n_coeff = numel(fieldnames(dataSchema.wing.outer.foil));

cst_root = zeros(1, n_coeff);
cst_tip = zeros(1, n_coeff);

for idx_coeff = 1:n_coeff
    fieldname = strcat('b_', num2str(idx_coeff));

    cst_root(idx_coeff) = dataSchema.wing.inner.foil.(fieldname);
    cst_tip(idx_coeff) = dataSchema.wing.outer.foil.(fieldname);
end

%% Setting up Q3D

AC.Wing.Geom = [0           0           0   inner_chord inner_twist;
                x_mid_wing  y_mid_wing  0   mid_chord   mid_twist;
                x_tip       y_tip       0   outer_chord outer_twist];

% Wing incidence angle (degree)
AC.Wing.inc = 0;

% Airfoil coefficients input matrix
AC.Wing.Airfoils = [cst_root;
                    cst_tip];

AC.Wing.eta = [0;1];  % Spanwise location of the airfoil sections

w_fuel = dataSchema.weights.fuel;
w_str_wing = dataSchema.weights.str_wing;
w_aw = dataSchema.weights.a_w;

w_to_max = w_fuel + w_str_wing + w_aw;

if mode == 0
    AC.Visc = 0;
    AC.Aero.V = dataSchema.performance.V_max;
    AC.Aero.rho = dataSchema.constants.rho_cruise;         % air density  (kg/m3)
    AC.Aero.alt = dataSchema.constants.h_cruise;
    visc = dataSchema.constants.visc_kin_cruise;
    n = dataSchema.constants.n_max;
    W = w_to_max;
elseif mode == 1    
    AC.Visc = 1;
    AC.Aero.V = dataSchema.performance.V_cruise;
    AC.Aero.rho = dataSchema.constants.rho_cruise;         % air density  (kg/m3)
    AC.Aero.alt = dataSchema.constants.h_cruise;
    visc = dataSchema.constants.visc_kin_cruise;
    n = dataSchema.constants.n_cruise;
    W =  sqrt(w_to_max*(w_to_max-w_fuel)); % W_des
else
    error('Please provide a valid mode (0 or 1) to the Q3D_cpacs function.')
end

AC.Aero.MaxIterIndex = 150;    %Maximum number of Iteration for Q3D convergence
AC.Aero.Re = AC.Aero.V*MAC/visc;        % reynolds number (based on mean aerodynamic chord)
AC.Aero.M = AC.Aero.V/dataSchema.constants.c_sound;           % flight Mach number
AC.Aero.CL = n*(2*W/(AC.Aero.rho*(AC.Aero.V)^2*wing_area));          % lift coefficient - comment this line to run the code for given alpha%

%% Execute solver
try
    q_path = sprintf('%s\\%s', stor_path, 'Q3D');
    old_folder = cd(q_path);
    res = Q3D_solver(AC);
    cd(old_folder)
    
    if mode == 1
        res.CDwing = res.CDwing+C_D_aw*(C_D_aw_area/wing_area);
        res.L_D = res.CLwing/res.CDwing;
    end

    failed = false;
    if contains(lastwarn, 'Attention!:2D aerodynamic analysis did not converge in section')
        failed = true;
    end

    lastwarn('')
catch e
    failed = true;
    if ~exist('res','var')
        res.L_D = NaN;
        res.CDwing = NaN;
        res.CLwing = NaN;
    end
    warning('Something failed!')
    fprintf(1,'The identifier was:\n%s',e.identifier);
    fprintf(1,'There was an error! The message was:\n%s',e.message);
end
end

function [dataSchema_low, dataSchema_high] = create_trust_region(dataSchema, delta)
    include_airfoil = true;
    design_vars = {'/dataSchema/wing/inner/sweep', ...
                    '/dataSchema/wing/inner/chord', ...
                    '/dataSchema/wing/mid/twist', ...
                    '/dataSchema/wing/outer/twist', ...
                    '/dataSchema/wing/outer/sweep', ...
                    '/dataSchema/wing/outer/chord', ...
                    '/dataSchema/wing/outer/span', ...
                    '/dataSchema/weights/fuel', ...
                    '/dataSchema/weights/str_wing'};

    airfoil_vars = {'/dataSchema/wing/inner/foil/b_1', ...
                    '/dataSchema/wing/outer/foil/b_1', ...
                    '/dataSchema/wing/inner/foil/b_2', ...
                    '/dataSchema/wing/outer/foil/b_2', ...
                    '/dataSchema/wing/inner/foil/b_3', ...
                    '/dataSchema/wing/outer/foil/b_3', ...
                    '/dataSchema/wing/inner/foil/b_4', ...
                    '/dataSchema/wing/outer/foil/b_4', ...
                    '/dataSchema/wing/inner/foil/b_5', ...
                    '/dataSchema/wing/outer/foil/b_5', ...
                    '/dataSchema/wing/inner/foil/b_6', ...
                    '/dataSchema/wing/outer/foil/b_6', ...
                    '/dataSchema/wing/inner/foil/b_7', ...
                    '/dataSchema/wing/outer/foil/b_7', ...
                    '/dataSchema/wing/inner/foil/b_8', ...
                    '/dataSchema/wing/outer/foil/b_8', ...
                    '/dataSchema/wing/inner/foil/b_9', ...
                    '/dataSchema/wing/outer/foil/b_9', ...
                    '/dataSchema/wing/inner/foil/b_10', ...
                    '/dataSchema/wing/outer/foil/b_10', ...
                    '/dataSchema/wing/inner/foil/b_11', ...
                    '/dataSchema/wing/outer/foil/b_11', ...
                    '/dataSchema/wing/inner/foil/b_12',...
                    '/dataSchema/wing/outer/foil/b_12'};
    
    if include_airfoil
        design_vars = [design_vars, airfoil_vars];
    end

    dataSchema_low = dataSchema;
    dataSchema_high = dataSchema;
                
    for idx_var = 1:length(design_vars)
        design_var = design_vars{idx_var};

        path = strsplit(design_var, '/');
        path = cellstr(path(3:end));
        
        mid_value = getfield(dataSchema, path{:});
        low_value = mid_value - abs(mid_value)*delta;
        high_value = mid_value + abs(mid_value)*delta;
        
        dataSchema_low = setfield(dataSchema_low, path{:}, low_value);
        dataSchema_high = setfield(dataSchema_high, path{:}, high_value);
    end    
end