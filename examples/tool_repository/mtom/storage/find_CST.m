function [U] = find_CST(coord, n_points)
U_0 = ones(1, n_points);
U_0(n_points/2+1:end) = U_0(n_points/2+1:end) * -1;

fun = @(x) score_cst_foil(x, coord);

options = optimset('Display', 'iter', 'Algorithm', 'sqp');
opt_time_start = now();
[U, ~, ~, ~] = fmincon(fun, U_0, [], [], [], [], [], [], [], options);
opt_time_end = now()-opt_time_start;


if false
    Au = U(1:6);
    Al = U(7:12);
    
    % Circle distribution for nicer plotting figure
    X = linspace(0, pi, 999)';
    X = (cos(X)+1)./2;
    
    [Xtu,Xtl,C] = D_airfoil2(Au,Al,X);

    figure
    hold on
    plot(Xtu(:,1),Xtu(:,2),'b');    %plot upper surface coords
    plot(Xtl(:,1),Xtl(:,2),'b');    %plot lower surface coords
    axis([0,1,-1.5,1.5]);
    plot(coord(:, 1),coord(:,2),'r*');    %plot upper surface coords
end

end


