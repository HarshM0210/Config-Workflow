import yaml
import sys

def update_cfg_file(yaml_path):
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    cfg_path = data['cfg_path']
    new_options = data['options']

    lines = []
    with open(cfg_path, 'r') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('%'):
                key = line.split('=')[0].strip()
                if key in new_options:
                    val = new_options[key]
                    lines.append(f"{key} = {val}\n")
                    continue
            lines.append(line)

    with open(cfg_path, 'w') as f:
        f.writelines(lines)

if __name__ == "__main__":
    update_cfg_file(sys.argv[1])
