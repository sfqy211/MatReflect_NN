function [diffParam, specParam1, specParam2, diffColor, specColor] = naiveFit_Full(rho, initVal, metric)
    persistent cosMap volumnWeight epsilon
    if isempty(cosMap)
       load 'cosMap.mat' cosMap;
       load 'volumnWeight.mat' volumnWeight;
       epsilon = 1e-3;
    end
    
    if iscell(rho)
        rho = reshape(cell2mat(rho), [], 3);
    end

    if iscell(initVal)
        initVal = reshape(cell2mat(initVal), [], 1);
    end

    function d = logOne(x, y)
        d = mean2( abs(log(x .* cosMap + epsilon) - log(y .* cosMap + epsilon)) );
    end

    function d = logTwo(x, y)
        d = mean2( (log(x .* cosMap + epsilon) - log(y .* cosMap + epsilon)) .^ 2 );
    end

    function d = linearOne(x, y)
        d = mean2( abs(x - y) .* cosMap );
    end

    function d = cubicRoot(x, y)
        d = mean2((abs(x - y) .* cosMap) .^ (2. / 3));
    end

    function d = weightSquare(x, y)
        d = mean2(volumnWeight .* ((x - y) .* cosMap) .^ 2);
    end

    diffParamNum = 1;
    diffParamLb = [0];
    diffParamUb = [1];
    diffFun = @lambertian;

    specParamNum = 3;
    specParamLb = [0; 0.001; 1.3];
    specParamUb = [1; 1; 10];
    specFun = @GGX;

    totalParamNum = diffParamNum + 2 * specParamNum;

    colorParamNum = 6;
    colorParamLb = [0; 0; 0; 0; 0; 0];
    colorParamUb = [1; 1; 1; 1; 1; 1] * 3;
    Aeq = [zeros(1, totalParamNum), ones(1, 3), zeros(1, 3); zeros(1, totalParamNum), zeros(1, 3), ones(1, 3)];
    beq = ones(2, 1) * 3;

    switch metric
        case 'log1'
            brdfMetric = @logOne;
        case 'log2'
            brdfMetric = @logTwo;
        case 'linear1'
            brdfMetric = @linearOne;
        case 'cubicRoot'
            brdfMetric = @cubicRoot;
        case 'weightSquare'
            brdfMetric = @weightSquare;
    end

    function [funVal] = fun(x)
        diffParamCell = num2cell(x(1:diffParamNum));
        specParamCell1 = num2cell(x(diffParamNum+1:diffParamNum+specParamNum));
        specParamCell2 = num2cell(x(diffParamNum+specParamNum+1:diffParamNum+2*specParamNum));
        funVal = brdfMetric(rho, diffFun(diffParamCell{:}) * x(totalParamNum+1:totalParamNum+3)' + (specFun(specParamCell1{:}) + specFun(specParamCell2{:})) * x(totalParamNum+4:totalParamNum+6)');
    end
    
    lb = [diffParamLb; specParamLb; specParamLb; colorParamLb];
    ub = [diffParamUb; specParamUb; specParamUb; colorParamUb];

    x = fmincon(@fun, initVal, [], [], Aeq, beq, lb, ub, []);
    diffParam = x(1:diffParamNum);
    specParam1 = x(diffParamNum+1:diffParamNum+specParamNum);
    specParam2 = x(diffParamNum+specParamNum+1:diffParamNum+2*specParamNum);
    diffColor = x(totalParamNum+1:totalParamNum+3);
    specColor = x(totalParamNum+4:totalParamNum+6);

end
