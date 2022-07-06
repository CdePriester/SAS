function [root_coord, tip_coord] = scale_airfoil(coord, root_t, tip_t)
% Function to scale coordinates and scale airfoil to thickness
% Input: coordinates read from .dat, required thicknesses root_t and tip_t
    % .dat file splits in two at half.
    split = ceil(length(coord)/2);
    
    % Put upper and lower next to each other and find thickness
    lower_surf = flipud(coord(split:end, :));
    new_coord = [coord(1:split, 1:2), lower_surf(:, 2)];
    difference = (new_coord(:, 2)-new_coord(:, 3));
    [thickness, ~] = max(difference);


    root_ratio = root_t/thickness;
    tip_ratio = tip_t/thickness;
    
    % Adjust coordinates for new thicknesses
    root_coord = [coord(:, 1) coord(:, 2).*root_ratio];
    tip_coord = [coord(:, 1) coord(:, 2).*tip_ratio];
end



