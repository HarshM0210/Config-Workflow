import sys
import os
import yaml

def parse_su2_config(path):
    options = {}
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line == "" or line.startswith("%") or "=" not in line:
                continue
            key, val = map(str.strip, line.split("=", 1))
            options[key] = val
    return options

if __name__ == "__main__":
    cfg_path = sys.argv[1]
    parts = cfg_path.split(os.sep)
    category = parts[1]
    case_code = parts[2]

    data = {
        'category': category,
        'case_code': case_code,
        'cfg_path': cfg_path,
        'options': parse_su2_config(cfg_path)
    }

    print(yaml.dump(data, sort_keys=False))
