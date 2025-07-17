import os
import subprocess
import argparse


def run_su2_simulation(mesh_dir):
    cfg_path = os.path.join(mesh_dir, "Config.cfg")
    if os.path.exists(cfg_path):
        print(f"\n[INFO] Running SU2_CFD in: {mesh_dir}")
        result = subprocess.run(["SU2_CFD", cfg_path], cwd=mesh_dir)
        if result.returncode != 0:
            print(f"[ERROR] SU2_CFD failed in {mesh_dir}")
        else:
            print(f"[INFO] SU2_CFD finished successfully in {mesh_dir}")
    else:
        print(f"[WARNING] Config.cfg not found in {mesh_dir}, skipping...\n")


def run_plot_script(config_path):
    plot_script = os.path.join(config_path, "Plot.py")
    if os.path.exists(plot_script):
        print(f"\n[INFO] Running Plot.py in: {config_path}")
        result = subprocess.run(["python3", plot_script], cwd=config_path)
        if result.returncode != 0:
            print(f"[ERROR] Plot.py failed in {config_path}")
        else:
            print(f"[INFO] Plot.py executed successfully in {config_path}")
    else:
        print(f"[WARNING] Plot.py not found in {config_path}, skipping...\n")


def get_mesh_folders(config_path):
    mesh_dirs = []
    for entry in os.listdir(config_path):
        full_path = os.path.join(config_path, entry)
        if os.path.isdir(full_path) and not entry.startswith('.'):
            mesh_dirs.append(full_path)
    return mesh_dirs


def process_configuration(main_path, configuration):
    config_path = os.path.join(main_path, configuration)
    print(f"\n[INFO] Processing configuration at: {config_path}")
    mesh_dirs = get_mesh_folders(config_path)
    if not mesh_dirs:
        print(f"[WARNING] No mesh directories found in {config_path}\n")
        return

    for mesh_dir in mesh_dirs:
        run_su2_simulation(mesh_dir)

    run_plot_script(config_path)


def main():
    parser = argparse.ArgumentParser(description="Automate SU2 simulation and plotting")
    parser.add_argument('--category', required=True, help='Validation category (e.g., Basic or Extended)')
    parser.add_argument('--case-code', required=True, help='Case code (e.g., 2DML)')
    parser.add_argument('--turbulence-model', required=True, help='Turbulence model (e.g., SA or SST)')
    parser.add_argument('--configuration', required=True, help='Specific Configuration (e.g., Configuration1) or All')
    parser.add_argument('--main-path', required=True, help='Path to base directory inside ValidationCases')
    parser.add_argument('--output-path', required=False, help='Optional path to store outputs')

    args = parser.parse_args()

    if args.configuration == "All":
        for entry in os.listdir(args.main_path):
            config_path = os.path.join(args.main_path, entry)
            if os.path.isdir(config_path) and entry.startswith("Configuration"):
                process_configuration(args.main_path, entry)
    else:
        process_configuration(args.main_path, args.configuration)


if __name__ == "__main__":
    main()