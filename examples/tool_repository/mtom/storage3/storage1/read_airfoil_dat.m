function [coord] = read_airfoil_dat(filepath)
% Reads .dat coordinate file

fid = fopen(filepath, 'r');
coord = fscanf(fid, '%g %g', [2 Inf])';
fclose(fid);



end

