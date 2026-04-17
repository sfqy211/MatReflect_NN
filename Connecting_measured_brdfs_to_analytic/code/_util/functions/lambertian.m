function brdf = lambertian(rho)
    persistent brdfValNum
    if isempty(brdfValNum)
    	load 'directions.mat' L;
    	brdfValNum = size(L, 1);
    end
    brdf = ones(brdfValNum, 1) * (rho / pi);
end