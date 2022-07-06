function s = prepare_struct(s_in)

fn = fieldnames(s_in);

for idx_f = 1:numel(fn)
    if strcmp(fn{idx_f}, 'Text') 
        s = str2double(s_in.(fn{idx_f}));
    elseif ~isstruct(s_in.(fn{idx_f}))
        if isstring(s_in.(fn{idx_f}))
            s.(fn{idx_f}) = str2double(s_in.(fn{idx_f}));
        elseif iscell()
            s.(fn{idx_f}) = s_in.(fn{idx_f});
        end
    else
        s.(fn{idx_f}) = prepare_struct(s_in.(fn{idx_f}));
    end
end

