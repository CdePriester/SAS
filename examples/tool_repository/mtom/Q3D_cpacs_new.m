n_points = 30;
span = linspace(13, 14, n_points);

cpacs_in = 'prepared_mtom_cpacs.xml';

C_L = [];
C_D = [];
parfor idx = 1:length(span)
    disp(idx)
    s = span(idx);
    [L, D] = Q3D_cpacs(cpacs_in, s);
    C_L(idx) = L;
    C_D(idx) = D;
end

L_D = C_L./C_D;

idx_Nan = ~isnan(L_D);

figure
hold on;
plot(span_30, L_D_30, 'DisplayName', '30 samples')
plot(span_60, L_D_60, 'DisplayName', '60 samples')
plot(span_300, L_D_300, 'DisplayName', '300 samples')
plot(span, L_D, 'DisplayName', '100 samples (small range)');
legend()
title('Q3D: L/D for given span')
xlabel('Outer span [m]')
ylabel('L/D wing [-]')

function [C_L, C_D] = Q3D_cpacs(cpacs_in, span)
mode = 1;
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
dataSchema = readstruct(cpacs_in);
dataSchema.wing.outer.span = span;

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
    
    parfor idx = 1:length(results)
        [result{idx}, fail_res(idx)] = execute_Q3D(dataSchemas{idx}, mode);
    end
    for idx = 1:length(results)
        res.CLwing(idx) = result{idx}.CLwing;
        res.CDwing(idx) = result{idx}.CDwing;
    end
    failed = any(fail_res);
    res.CLwing = mean(res.CLwing);
    res.CDwing = mean(res.CDwing);
else
   res = execute_Q3D(dataSchema, mode); 
end
if mode == 0
    fields = fieldnames(res.Wing);

    for idx = 1:length(fields)
        fn = fields{idx};
        dataSchema.wing.(fn) = res.Wing.(fn);
    end
    dataSchema.wing.area = wing_area;
elseif mode == 1
    
    dataSchema.wing.C_L = res.CLwing;
    
    C_L = res.CLwing;
    C_D = res.CDwing;

    if isnan(res.CDwing) || failed
        if failed
            warning('Some sections failed to converge, so:')
        end
        warning('Setting CDwing to = -10')
        dataSchema.wing.C_D = -10;
        dataSchema.errorFlags.aero = 1;
    else
        dataSchema.errorFlags.aero = 0;
        dataSchema.wing.C_D = res.CDwing;
    end

end
end

function [res, failed] = execute_Q3D(dataSchema, mode)
job_id = get(getCurrentTask(), 'ID');
stor_path = sprintf('storage%d', job_id);
addpath(genpath(stor_path))


inner_span = dataSchema.wing.inner.span;
inner_sweep = dataSchema.wing.inner.sweep;
inner_chord = dataSchema.wing.inner.chord;
inner_twist = dataSchema.wing.inner.twist;
inner_twist = 0;

mid_twist = dataSchema.wing.mid.twist;
mid_twist = 0;

x_mid_wing = inner_span*tan(inner_sweep*(pi/180));
y_mid_wing = inner_span;

outer_span = dataSchema.wing.outer.span;
outer_sweep = dataSchema.wing.outer.sweep;
outer_chord = dataSchema.wing.outer.chord;
outer_twist = dataSchema.wing.outer.twist;
outer_twist = 0;

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
    
    failed = false;
    if contains(lastwarn, 'Attention!:2D aerodynamic analysis did not converge in section')
        failed = true;
    end

    lastwarn('')
catch
    warning('Something failed!')
end
end

function [dataSchema_low, dataSchema_high] = create_trust_region(dataSchema, delta)                    
    design_vars = {'/dataSchema/wing/inner/twist', ...
                    '/dataSchema/wing/inner/sweep', ...
                    '/dataSchema/wing/inner/chord', ...
                    '/dataSchema/wing/mid/twist', ...
                    '/dataSchema/wing/outer/twist', ...
                    '/dataSchema/wing/outer/sweep', ...
                    '/dataSchema/wing/outer/chord', ...
                    '/dataSchema/wing/outer/span', ...
                    '/dataSchema/weights/fuel', ...
                    '/dataSchema/weights/str_wing'};
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
