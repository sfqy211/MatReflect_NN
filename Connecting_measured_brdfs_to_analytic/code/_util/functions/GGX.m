function brdf = GGX(rho, alpha, ior)
    persistent L V N H NdotH VdotH NdotL NdotV NdotH2 NdotLTan2 NdotVTan2
    if isempty(L) || isempty(V)
        load 'directions.mat' L V;
       
        L = normr(L);
        V = normr(V);
        H = normr(L + V);
        N = zeros(size(L));
        N(:, 3) = 1;

        NdotH = dot(N, H, 2);
        VdotH = dot(V, H, 2);
        NdotL = dot(N, L, 2);
        NdotV = dot(N, V, 2);
        NdotH2 = NdotH .^ 2;
        NdotLTan2 = abs((1 - NdotL .^ 2) ./ (NdotL .^ 2));
        NdotVTan2 = abs((1 - NdotV .^ 2) ./ (NdotV .^ 2));

    end
    
    alpha2 = alpha .^ 2;
    D = alpha2 ./ (pi * (1 + NdotH2 * (alpha2 - 1)) .^ 2);
    G = 4 ./ ((1 + sqrt(1 + NdotLTan2 * alpha2)) .* (1 + sqrt(1 + NdotVTan2 * alpha2)));
    g = sqrt(ior .^ 2 - 1 + VdotH .^ 2);
    F = 0.5 * ((g - VdotH) ./ (g + VdotH)) .^ 2 .* (1 + ((VdotH .* (g + VdotH) - 1) ./ (VdotH .* (g - VdotH) + 1)) .^ 2);
    
    brdf = abs(rho .* D .* G .* F ./ (4 * NdotL .* NdotV));
    % brdf(NdotL < 0, :) = 0;
    % brdf(NdotV < 0, :) = 0;
end