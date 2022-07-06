function [obj] = score_cst_foil(U, coord)
% Find the error between a CST airfoil and a coordinate set

X = coord(1:37, 1);

upper_surf = coord(1:37, :);
lower_surf = flipud(coord(37:end, :));

% Interpolate to match dimensions

Au = U(1:length(U)/2);
Al = U((length(U)/2+1):end);

[Xtu,Xtl,~] = D_airfoil2(Au,Al,X);

obj = sum((Xtu(:, 2)-upper_surf(:, 2)).^2) + sum((Xtl(:, 2)-lower_surf(:, 2)).^2);

end

