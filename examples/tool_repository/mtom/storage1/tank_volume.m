function [V] = tank_volume(cst_root, cst_tip, C, b)
resolution = 50;

Au_r = cst_root(1:6);
Al_r = cst_root(7:12);

Au_t = cst_tip(1:6);
Al_t = cst_tip(7:12);

b_1 = b(1);
b_2 = b(2);

C_1 = C(1);
C_2 = C(2);
C_3 = C(3);

% tank starts at 15% and ends at 60%
tank_x = [0.15 0.60];
tank_i = ceil(tank_x.*resolution);
tip = 0.85;
tip_i = ceil(tip*resolution);

x = linspace(0, 1, resolution)'; % Chordwise distribution
y = x; % Spanwise distribution

chord_dist = interp1([0, b_1/sum(b), 1], C, y);

[z_u_r,z_l_r,~] = D_airfoil2(Au_r,Al_r,x);
[z_u_t,z_l_t,~] = D_airfoil2(Au_t,Al_t,x);

foil_matrix_u = zeros(length(x), length(y));
foil_matrix_l = zeros(length(x), length(y));

for chord_coord = 1:length(x)
   foil_matrix_u(chord_coord, :) = interp1([0,1],[z_u_r(chord_coord,2),z_u_t(chord_coord,2)],y);
   foil_matrix_l(chord_coord, :) = interp1([0,1],[z_l_r(chord_coord,2),z_l_t(chord_coord,2)],y);
end

for span_coord = 1:length(y)
   area_u(1, span_coord) = trapz(x(tank_i(1):tank_i(2)), foil_matrix_u(tank_i(1):tank_i(2), span_coord))*chord_dist(span_coord)^2;
   area_l(1, span_coord) = trapz(x(tank_i(1):tank_i(2)), foil_matrix_l(tank_i(1):tank_i(2), span_coord))*chord_dist(span_coord)^2;
end

y = y*(b_1+b_2);
y = y(1:tip_i);

vol_u = trapz(y, area_u(1:tip_i)');
vol_l = trapz(y, area_l(1:tip_i)');

V = 2*(vol_u - vol_l);