function [] = init_EMWET(options, wing, foils)
%Functions writes .init file for EMWET
%   For detailed explanation see the user manual of EMWET
%   Takes struct as input where all options should be defined


fid = fopen(['EMWET/' options.name '.init'], 'w');

fprintf(fid, '%.0f %.0f\n', options.MTOW, options.ZFW);
fprintf(fid, '%.1f\n', options.n);
fprintf(fid, '%.2f %.2f %.0f %.0f\n', options.S, options.b ,options.n_plan ,options.n_foils);

foil_names = fieldnames(options.airfoils);

for i = 1:length(foil_names)
    name = foil_names{i};
    fprintf(fid, '%.4f %s\n', options.airfoils.(name), name);
end

for i = 1:length(options.sections(:, 1))
    if length(options.sections) ~= 6
       error('Check EMWET section input data') 
    end    
    fprintf(fid, '%s %s %s %s %s %s \n', string(options.sections(i, :)));
end

fprintf(fid, '%.2f %.2f\n',options.fueltank);
fprintf(fid, '%.0f\n',options.n_engines);
fprintf(fid, '%.3f %.0f\n',options.engine_data);

% One material for complete foil, so constant
for i = 1:4
    fprintf(fid, '%d %d %d %d\n', options.material);
end

fprintf(fid, '%.2f %.1f\n', options.eta_panel, options.rib_pitch);
fprintf(fid, '%.0f', options.display);
fclose(fid);

% Prepare results so they start at 0 end at 1

% Open and write Loads file for EMWET
fid = fopen(['EMWET/' options.name '.load'], 'w'); 

% Extrapolate data to be usable for EMWET (Start at 0, end at 1)
Yst_interp = linspace(0, options.b/2, 14)';
ccl_interp = interp1(wing.Yst,wing.ccl,Yst_interp, 'linear', 'extrap');
cm_c4_interp = interp1(wing.Yst,wing.cm_c4,Yst_interp, 'linear', 'extrap');

for i = 1:length(wing.Yst)
    span = Yst_interp(i)/(options.b/2);
    lift = ccl_interp(i)*0.5*options.rho*options.V^2;
    moment = cm_c4_interp(i)*0.5*options.rho*options.V^2*options.MAC;
    fprintf(fid, '%.4f %d %d\n', span, lift, moment);
end    
fclose(fid);

% Open and create Geo files for EMWET

index = 'a';
% Use cosine spacing for more accurate nose and tail describtion

X = linspace(0, pi, 40)';
X = (cos(X)+1)./2;

% Loop over each defined foil
for i = 1:length(foils(:, 1))
    Au = foils(i, 1:6);
    Al = foils(i, 7:12);
    
    % Use standard function to convert from Bernstein to coordinate
    [Xtu,Xtl,~] = D_airfoil2(Au,Al,X);
    
    % Format
    output_data = [Xtu; flipud(Xtl(1:end-1, :))];
    
    % Write data to file
    fid = fopen(['EMWET/' options.name index '.dat'], 'w');
    for n = 1:length(output_data(:, 1))
        fprintf(fid, '%d %d\n', output_data(n, 1), output_data(n, 2));
    end
    fclose(fid);
    
    % TO DO: Nasty hardcode! 
    index = 'b';
end

end

