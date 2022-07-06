function perf_cpacs(cpacs_in, cpacs_out)
addpath(genpath('storage'))

% Extracting CPACS Values
dataSchema = readstruct(cpacs_in);

% if C_D_wing < 0 || C_L_wing < 0
%     disp('C_D_wing < 0 || C_L_wing < 0!')
%     fail_perf(dataSchema, cpacs_out)
%     return
% end

L_D = dataSchema.wing.L_D;

range_cruise = dataSchema.performance.range_cruise;
C_T = dataSchema.performance.C_T;
V_cruise = dataSchema.performance.V_cruise;

w_fuel = dataSchema.weights.fuel;
w_str_wing = dataSchema.weights.str_wing;

% if w_str_wing < 0 || w_fuel < 0
%     disp('w_str_wing < 0 || w_fuel < 0')
%     fail_perf(dataSchema, cpacs_out)
%     return
% end

w_aw = dataSchema.weights.a_w;

w_to_max = w_fuel + w_str_wing + w_aw;

try
    % Performance calculations
    W_ratio = exp(range_cruise*(C_T/V_cruise)*(1/L_D));
    W_fuel = (1-0.938*1/W_ratio)*w_to_max;
    
    % Saving output to CPACS
    if W_fuel < 0
        disp('w_fuel < 0!')
        fail_perf(dataSchema, cpacs_out)
        return
    else
        dataSchema.weights.fuel = W_fuel;
    end
catch
    disp('Exception when calculating w_fuel')
    fail_perf(dataSchema, cpacs_out)
    return
end
dataSchema.errorFlags.fuel = 0;
writestruct(dataSchema, cpacs_out, 'StructNodeName', 'dataSchema');
cd ..
cd ..
end

function fail_perf(dataSchema, cpacs_out)
    original_schema = readstruct('prepared_mtom_cpacs.xml');
    warning('Something went wrong! Setting fuel weight to original value')
    dataSchema.weights.fuel = original_schema.weights.fuel;
    dataSchema.errorFlags.fuel = 1;
    writestruct(dataSchema, cpacs_out, 'StructNodeName', 'dataSchema');
    cd ..
    cd ..
end
