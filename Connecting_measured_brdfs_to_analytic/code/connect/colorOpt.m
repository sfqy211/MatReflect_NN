function [colors] = colorOpt(rho, lobes, x0, metric)
    persistent renderSlice
    if isempty(renderSlice)
       load 'renderSlice.mat' renderSlice;
    end
    
    channelNum = 3;
    if iscell(rho)
        rho = reshape(cell2mat(rho), [], channelNum);
    else
        rho = reshape(rho, [], channelNum);
    end
    if iscell(lobes)
        lobes = reshape(cell2mat(lobes), size(rho, 1), []);
    else
        lobes = reshape(lobes, size(rho, 1), []);
    end
    lobeNum = size(lobes, 2);
    lobeImages = renderSlice * lobes;
    if iscell(x0)
        x0 = reshape(cell2mat(x0), [], 1);
    else
        x0 = reshape(x0, [], 1);
    end
    
    brdfHsiWrap = wrapHsi(rgb2hsi(rho));
    imageHsiWrap = wrapHsi(rgb2hsi(renderSlice * rho));
    
    function [funVal] = brdf1Hsi(x)
        hsiWrapRecon = wrapHsi(rgb2hsi(lobes * reshape(x, channelNum, lobeNum)'));
%         funVal = sum(sum((brdfHsiWrap(:, 1:2) - hsiWrapRecon(:, 1:2)) .^ 2)) + sum((brdfHsiWrap(:, 2) .* diffAngle(brdfHsiWrap(:, 3) - hsiWrapRecon(:, 3))) .^ 2);
        funVal = sum(abs(hsiWrapRecon(:) - brdfHsiWrap(:)));
    end

    function [funVal] = brdf2Hsi(x)
        hsiWrapRecon = wrapHsi(rgb2hsi(lobes * reshape(x, channelNum, lobeNum)'));
%         funVal = sum(sum((brdfHsiWrap(:, 1:2) - hsiWrapRecon(:, 1:2)) .^ 2)) + sum((brdfHsiWrap(:, 2) .* diffAngle(brdfHsiWrap(:, 3) - hsiWrapRecon(:, 3))) .^ 2);
        funVal = sum((hsiWrapRecon(:) - brdfHsiWrap(:)) .^ 2);
    end

    function [funVal] = image1Hsi(x)
        hsiWrapRecon = wrapHsi(rgb2hsi(lobeImages * reshape(x, channelNum, lobeNum)'));
%         funVal = sum(sum((imageHsiWrap(:, 1:2) - hsiWrapRecon(:, 1:2)) .^ 2)) + sum((imageHsiWrap(:, 2) .* diffAngle(imageHsiWrap(:, 3) - hsiWrapRecon(:, 3))) .^ 2);
        funVal = sum(abs(hsiWrapRecon(:) - imageHsiWrap(:)));
    end

    function [funVal] = image2Hsi(x)
        hsiWrapRecon = wrapHsi(rgb2hsi(lobeImages * reshape(x, channelNum, lobeNum)'));
%         funVal = sum(sum((imageHsiWrap(:, 1:2) - hsiWrapRecon(:, 1:2)) .^ 2)) + sum((imageHsiWrap(:, 2) .* diffAngle(imageHsiWrap(:, 3) - hsiWrapRecon(:, 3))) .^ 2);
        funVal = sum((hsiWrapRecon(:) - imageHsiWrap(:)) .^ 2);
    end

    switch metric
        case 'brdf1'
            colorMetric = @brdf1Hsi;
        case 'brdf2'
            colorMetric = @brdf2Hsi;
        case 'image1'
            colorMetric = @image1Hsi;
        case 'image2'
            colorMetric = @image2Hsi;
    end

    lb = zeros(channelNum*lobeNum, 1);
    ub = ones(channelNum*lobeNum, 1) * channelNum;
    Aeq = kron(eye(lobeNum), ones(1, channelNum));
    beq = ones(lobeNum, 1) * channelNum;
    options = optimoptions('fmincon','MaxFunctionEvaluations', 10000, 'MaxIterations', 3000);
    
    colors = fmincon(colorMetric, x0, [], [], Aeq, beq, lb, ub, [], options);
end

function [hsival] = rgb2hsi(rgbval)
	I = mean(rgbval, 2);
	S = 1 - min(rgbval, [], 2) ./ I;
    S(isnan(S)) = 0;
	RminusG = rgbval(:, 1) - rgbval(:, 2);
	RminusB = rgbval(:, 1) - rgbval(:, 3);
    GminusB = rgbval(:, 2) - rgbval(:, 3);
    H = atan2(sqrt(3) / 2 * GminusB, 0.5 * (RminusG + RminusB));
    hsival = [I, S, H];
end

function [hsiWrap] = wrapHsi(hsival)
    hsiWrap = [hsival(:, 2) .* cos(hsival(:, 3)), hsival(:, 2) .* sin(hsival(:, 3))];
    % hsiWrap = [hsival(:, 1) .* hsival(:, 2) .* cos(hsival(:, 3)), hsival(:, 1) .* hsival(:, 2) .* sin(hsival(:, 3))];
    % hsiWrap = [hsival(:, 1) .^ (1. / 3) .* hsival(:, 2) .* cos(hsival(:, 3)), hsival(:, 1) .^ (1. / 3) .* hsival(:, 2) .* sin(hsival(:, 3))];
    % hsiWrap = [hsival(:, 1), hsival(:, 1) .* hsival(:, 2), hsival(:, 3)];
end

function ret = diffAngle(deltaAngle)
    ret = mod(deltaAngle + pi, 2 * pi) - pi;
end