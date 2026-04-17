function [diff, spec] = diffSpecOpt(rhoAve, diffAnalytic, specAnalytic, alpha, beta)
    persistent cosMap brdfValNum
    if isempty(cosMap)
        load 'cosMap.mat' cosMap;
        load 'directions.mat' L;
        brdfValNum = size(L, 1);
    end
    
    if iscell(rhoAve)
        rhoAve = reshape(cell2mat(rhoAve), [], 1);
    end
    if iscell(diffAnalytic)
        diffAnalytic = reshape(cell2mat(diffAnalytic), [], 1);
    end
    if iscell(specAnalytic)
        specAnalytic = reshape(cell2mat(specAnalytic), [], 1);
    end
    
    cvx_begin
        variable x(2 * brdfValNum);
        minimize(norm(cosMap .* (x(1:brdfValNum) + x(1+brdfValNum:2*brdfValNum) - rhoAve), 1) ...
                 + alpha * norm(cosMap .* (x(1:brdfValNum) - diffAnalytic), 1) ...
                 + beta * norm(cosMap .* (x(1+brdfValNum:2*brdfValNum) - specAnalytic), 1));
        subject to
            x >= 0;
    cvx_end
    
    diff = x(1:brdfValNum);
    spec = x(brdfValNum+1:2*brdfValNum);
end

