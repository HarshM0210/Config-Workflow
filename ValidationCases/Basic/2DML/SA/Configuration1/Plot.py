import pyvista as pv
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os
import argparse

def parse_arguments():
    """Parse command line arguments from the workflow"""
    parser = argparse.ArgumentParser(description='SU2 Validation Plotting')
    parser.add_argument('--category', required=True, help='Validation case category')
    parser.add_argument('--case-code', required=True, help='Validation case code')
    parser.add_argument('--turbulence-model', required=True, help='Turbulence model')
    parser.add_argument('--configuration', required=True, help='Configuration name')
    parser.add_argument('--main-path', required=True, help='Main repository path')
    return parser.parse_args()

# Configuration - will be set based on arguments
args = parse_arguments()
base_dir = os.path.join(args.main_path, args.category, args.case_code, 
                       args.turbulence_model, args.configuration)

# Mesh directories - should be detected automatically
def get_mesh_directories():
    """Detect mesh directories automatically"""
    mesh_dirs = []
    for item in os.listdir(base_dir):
        if os.path.isdir(os.path.join(base_dir, item)) and item.isdigit():
            mesh_dirs.append(item)
    return sorted(mesh_dirs, key=lambda x: int(x))

mesh_dirs = get_mesh_directories()
if not mesh_dirs:
    raise ValueError(f"No mesh directories found in {base_dir}")

# Experimental parameters (case-specific - for 2DML)
U1 = 22.40  # m/s
deltaU = 19.14  # m/s
delta_omega = {1:5.236, 50:8.8583, 200:13.771, 650:35.894, 950:50.547}  # mm
x_positions_mm = sorted(delta_omega.keys())
x_positions_m = [x/1000 for x in x_positions_mm]

def load_exp_data():
    """Load experimental data from the configuration directory"""
    exp_data = {}
    exp_file = os.path.join(base_dir, "exp_data.dat")
    
    if not os.path.exists(exp_file):
        raise FileNotFoundError(f"Experimental data file not found: {exp_file}")
    
    try:
        with open(exp_file, 'r') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        current_x = None
        current_data = []
        
        for line in lines:
            if "ZONE T=" in line:
                if current_x is not None and current_data:
                    exp_data[current_x] = pd.DataFrame(current_data, 
                                                     columns=["Y_mm", "U_m_s", "U_norm"])
                try:
                    current_x = int(float(line.split('"')[-2].split('=')[-1].replace('mm','')))
                except:
                    continue
                current_data = []
            elif "VARIABLES" not in line:
                try:
                    parts = list(map(float, line.split()))
                    if len(parts) >= 5:
                        current_data.append([parts[1], parts[2], parts[4]])
                except ValueError:
                    continue
        
        if current_x is not None and current_data:
            exp_data[current_x] = pd.DataFrame(current_data, 
                                             columns=["Y_mm", "U_m_s", "U_norm"])
            
        print(f"Loaded experimental data for x-positions: {list(exp_data.keys())}")
        return exp_data
        
    except Exception as e:
        raise ValueError(f"Error loading experimental data: {str(e)}")

def process_simulation_data():
    """Process simulation results from all mesh directories"""
    results = {}
    for mesh in mesh_dirs:
        path = os.path.join(base_dir, mesh, "vol_solution.vtu")
        print(f"Processing: {path}")
        
        try:
            mesh_data = pv.read(path)
            velocity = mesh_data['Velocity']
            mesh_data['U'] = velocity[:, 0]
            mesh_data['U_norm'] = (mesh_data['U'] - U1)/deltaU
            
            results[mesh] = {}
            for x_m, x_mm in zip(x_positions_m, x_positions_mm):
                profile = mesh_data.sample_over_line(
                    pointa=(x_m, -0.05, 0),
                    pointb=(x_m, 0.05, 0),
                    resolution=300
                )
                y_vals = profile.points[:, 1] * 1000  # mm
                y_norm = y_vals / delta_omega[x_mm]
                u_norm = profile['U_norm']
                
                results[mesh][x_mm] = {
                    'y_norm': y_norm,
                    'u_norm': u_norm
                }
                
        except Exception as e:
            print(f"Error processing {mesh}: {str(e)}")
            continue
    return results

def create_plots(exp_data, sim_results):
    """Generate validation plots"""
    output_dir = "plots"  # Changed to match workflow expectations
    os.makedirs(output_dir, exist_ok=True)
    
    mesh_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    exp_style = {'marker':'.', 'color':'k', 's':10, 'linewidths':1.5, 'zorder':10}
    
    for x_mm in x_positions_mm:
        plt.figure(figsize=(10, 6))
        
        # Plot simulation results
        for mesh, color in zip(mesh_dirs, mesh_colors):
            if mesh in sim_results and x_mm in sim_results[mesh]:
                data = sim_results[mesh][x_mm]
                plt.plot(data['u_norm'], data['y_norm'],
                        label=f"Mesh {mesh}",
                        color=color,
                        linewidth=2,
                        alpha=0.8)
        
        # Plot experimental data
        if x_mm in exp_data:
            exp_df = exp_data[x_mm]
            plt.scatter(exp_df['U_norm'], 
                       exp_df['Y_mm']/delta_omega[x_mm],
                       label='Experimental',
                       **exp_style)
            print(f"Plotting {len(exp_df)} experimental points for x={x_mm}mm")
        
        plt.xlabel(r"$(U-U_1)/\Delta U$", fontsize=12)
        plt.ylabel(r"$y/\delta_\omega$", fontsize=12)
        plt.title(f"Mixing Layer Profile at x = {x_mm} mm")
        plt.grid(True, linestyle=':', alpha=0.5)
        plt.legend(fontsize=10, framealpha=1)
        
        output_path = os.path.join(output_dir, f"profile_x{x_mm}mm.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved: {output_path}")

if __name__ == "__main__":
    print(f"Starting plotting for {args.category}/{args.case_code}/"
          f"{args.turbulence_model}/{args.configuration}")
    
    print("Loading experimental data...")
    try:
        exp_data = load_exp_data()
    except Exception as e:
        print(f"Fatal error loading experimental data: {e}")
        exit(1)
    
    print("\nProcessing simulation data...")
    sim_results = process_simulation_data()
    
    print("\nGenerating plots...")
    create_plots(exp_data, sim_results)
    
    print("\nAll plots generated successfully!")