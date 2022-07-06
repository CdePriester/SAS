function EMWET_cpacs(cpacs_in, cpacs_out)
addpath(genpath('storage'))

%% Extracting all variables from cpacs
dataSchema = readstruct(cpacs_in);


w_fuel = dataSchema.weights.fuel/9.81;
w_str_wing = dataSchema.weights.str_wing/9.81;
w_aw = dataSchema.weights.a_w/9.81;

% if w_fuel < 0 || w_str_wing < 0
%     disp('w_fuel < 0 || w_str_wing < 0!')
%     fail_EMWET(dataSchema, cpacs_out)
%     return
% end

w_to_max = w_fuel + w_str_wing + w_aw;

n = dataSchema.constants.n_max;

inner_span = dataSchema.wing.inner.span;
inner_sweep = dataSchema.wing.inner.sweep;
inner_chord = dataSchema.wing.inner.chord;

outer_span = dataSchema.wing.outer.span;
outer_sweep = dataSchema.wing.outer.sweep;
outer_chord = dataSchema.wing.outer.chord;

% Calculate area
mid_chord = inner_chord-sin(inner_sweep*(pi/180))*inner_span;
S = 2*(0.5*(inner_chord+mid_chord)*inner_span + 0.5*(mid_chord+outer_chord)*outer_span);

E_al = dataSchema.constants.E_al;
rho_al = dataSchema.constants.rho_al;
sig_yield_tens = dataSchema.constants.sig_yield_tens;
sig_yield_comp = dataSchema.constants.sig_yield_comp;

eta_panel = dataSchema.constants.eta_panel;
rib_pitch = dataSchema.constants.rib_pitch;

V_max = dataSchema.performance.V_max;
rho_cruise = dataSchema.constants.rho_cruise;

n_coeff = numel(fieldnames(dataSchema.wing.outer.foil));

cst_root = zeros(1, n_coeff);
cst_tip = zeros(1, n_coeff);

for idx_coeff = 1:n_coeff
    fieldname = strcat('b_', num2str(idx_coeff));

    cst_root(idx_coeff) = dataSchema.wing.inner.foil.(fieldname);
    cst_tip(idx_coeff) = dataSchema.wing.outer.foil.(fieldname);
end

%% Calculating parameters from variables
b = (inner_span + outer_span)*2;

x_mid_wing = inner_span*tan(inner_sweep*(pi/180));
y_mid_wing = inner_span;

% Added sinus term. Was missing. Geometry is quite clear on this
mid_chord = inner_chord-sin(inner_sweep*(pi/180))*inner_span;

x_tip = x_mid_wing + outer_span*tan(outer_sweep*(pi/180));
y_tip = y_mid_wing+outer_span;

taper_ratio = outer_chord/inner_chord;

MAC = inner_chord*2/3*(2/3)*((1+taper_ratio+taper_ratio^2)/(1+taper_ratio));

%% Setting EMWET options
options.name = 'A300'; % TODO: Remove hardcode here
options.MTOW = w_to_max;
options.ZFW = w_to_max-w_fuel;
options.n = n;
options.S = S;
options.b = b;
options.n_plan = 3;
options.n_foils = 2;

% Use struct names for file names
options.airfoils.A300a = 0;
options.airfoils.A300b = 1;

% [chord, x, y, z, front spar, rear spar]
options.sections = [inner_chord 0     0     0     0.15         0.60;
                    mid_chord x_mid_wing y_mid_wing 0 0.15         0.60;
                    outer_chord x_tip y_tip    0     0.15         0.60];
options.fueltank = [0.1 0.9];
options.n_engines = 1;
options.engine_data = [0.359 4273];

% [E_al Rho yield_tensile yield_compression]
options.material = [E_al rho_al sig_yield_tens sig_yield_comp];
options.eta_panel = eta_panel;
options.rib_pitch = rib_pitch;

options.display = 0;

options.V = V_max;
options.rho = rho_cruise;
options.MAC = MAC;

old_folder = cd('storage');
try
    init_EMWET(options, dataSchema.wing, [cst_root; cst_tip])
    eval('EMWET A300')
    EMWET_res = read_EMWET('A300');
catch
    disp('Calculations gave errors')
    fail_EMWET(dataSchema, cpacs_out)
    return
end
cd(old_folder);

if isnan(EMWET_res.weight)
    disp('Weight was NaN')
    fail_EMWET(dataSchema, cpacs_out)
    return
else
    dataSchema.weights.str_wing = EMWET_res.weight * 9.81;
    dataSchema.errorFlags.struct = 0;
end

writestruct(dataSchema, cpacs_out, 'StructNodeName', 'dataSchema');
cd ..
cd ..
end

function fail_EMWET(dataSchema, cpacs_out)
    original_schema = readstruct('prepared_mtom_cpacs.xml');
    warning('Something went wrong! Setting fuel weight to original value')
    dataSchema.weights.str_wing = original_schema.weights.str_wing;

    warning('EMWET failed! Setting weights.str_wing to -1.')
    dataSchema.errorFlags.struct = 1;
    writestruct(dataSchema, cpacs_out, 'StructNodeName', 'dataSchema');
    
    cd ..
    cd ..
end

