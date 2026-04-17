function [diffParam, specParam, diffAnalytic, specAnalytic] = analyticOpt(rhoAve, diffModel, specModel, metric)
    persistent cosMap volumnWeight epsilon
    if isempty(cosMap)
       load 'cosMap.mat' cosMap;
       load 'volumnWeight.mat' volumnWeight;
       epsilon = 1e-3;
    end
    
    if iscell(rhoAve)
        rhoAve = reshape(cell2mat(rhoAve), [], 1);
    end

    function d = logOne(x, y)
        d = mean( abs(log(x .* cosMap + epsilon) - log(y .* cosMap + epsilon)) );
    end

    function d = logTwo(x, y)
        d = mean( (log(x .* cosMap + epsilon) - log(y .* cosMap + epsilon)) .^ 2 );
    end

    function d = linearOne(x, y)
        d = mean( abs(x - y) .* cosMap );
    end

    function d = cubicRoot(x, y)
        d = mean((abs(x - y) .* cosMap) .^ (2. / 3));
    end

    function d = weightSquare(x, y)
        d = mean(volumnWeight .* ((x - y) .* cosMap) .^ 2);
    end

    switch diffModel
        case 'Lambertian'
            diffParamNum = 1;
            diffParamInit = [0.5];
            diffParamLb = [0];
            diffParamUb = [1];
            diffFun = @lambertian;
        otherwise
            fprintf('Wrong diffuse model\n');
    end
    switch specModel
        case 'GGX'
            specParamNum = 3;
            specParamInit = [0.5; 0.02; 1.8];
            specParamLb = [0; 0.001; 1.3];
            specParamUb = [1; 1; 5];
            specFun = @GGX;
        case 'CookTorrance'
            specParamNum = 3;
            specParamInit = [0.5; 0.02; 0.3];
            specParamLb = [0; 0.001; 0];
            specParamUb = [1; 1; 1];
            specFun = @cookTorrance;
        otherwise
            fprintf('Wrong specular model\n');
    end
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
        specParamCell = num2cell(x(diffParamNum+1:end));
        funVal = brdfMetric(rhoAve, diffFun(diffParamCell{:}) + specFun(specParamCell{:}));
    end
    
    x0 = [diffParamInit; specParamInit];
    lb = [diffParamLb; specParamLb];
    ub = [diffParamUb; specParamUb];

    x = fmincon(@fun, x0, [], [], [], [], lb, ub, []);
    diffParam = x(1:diffParamNum);
    specParam = x(diffParamNum+1:end);
    diffParamCell = num2cell(diffParam);
    specParamCell = num2cell(specParam);
    diffAnalytic = diffFun(diffParamCell{:});
    specAnalytic = specFun(specParamCell{:});

end
