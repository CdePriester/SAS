function [res] = read_EMWET(name)
%Functions reads .weight file for EMWET
%   parameter: name = name of weight file

text = fileread([name '.weight']);
raw = strsplit(text, '\n')';

res.output = [];
% Switch. If turned on, datapart in file from thereon
data = 0;

for line = 1:length(raw)
    % Trim line of unwanted char's
    trimmed = strtrim(raw{line});
    
    % Datapart of file
    if data
       out_str = strsplit(trimmed);
       % Check if line is in right format
       if length(out_str) ~= 6
           continue
       end
       
       % Add data to output
       for n = 1:length(out_str)
           if n == 1
               res.output(end+1, n) = str2double(out_str{n});
           else
               res.output(end, n) = str2double(out_str{n});
           end
       end
    end
    
    % Weight part of file
    if contains(trimmed, 'Wing total weight(kg)')
        splitted = strsplit(trimmed, ' ');
        res.weight = str2double(splitted(end));
    elseif contains(trimmed, 'y/(b/2)')
        % From this point on data starts
        data = 1;
    end
    
end

end

