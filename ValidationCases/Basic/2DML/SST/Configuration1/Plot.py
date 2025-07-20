import pyvista as pv
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os
import sys
from pathlib import Path

# Define delta_omega at module level so it's accessible everywhere
DELTA_OMEGA = {1:5.236, 50:8.8583, 200:13.771, 650:35.894, 950:50.547}

def load_exp_data(config_path):
    exp_data = {}
    exp_file = config_path / "exp_data.dat"
    
    if not exp_file.exists():
        print(f"Error: Experimental data file not found at {exp_file}")
        return None
        
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
                    # More robust x-position extraction
                    x_str = line.split('"')[-2].split('=')[-1].replace('mm','').strip()
                    current_x = int(float(x_str))
                except Exception as e:
                    print(f"Warning: Couldn't parse x-position from line: {line}")
                    continue
                current_data = []
            elif "VARIABLES" not in line:
                try:
                    parts = list(map(float, line.split()))
                    if len(parts) >= 5:
                        # Store all relevant data points
                        current_data.append({
                            "Y_mm": parts[1],
                            "U_m_s": parts[2],
                            "U_norm": parts[4]
                        })
                except ValueError:
                    continue
        
        if current_x is not None and current_data:
            exp_data[current_x] = pd.DataFrame(current_data)
            
        print(f"Loaded experimental data for x-positions: {list(exp_data.keys())}")
        return exp_data
        
    except Exception as e:
        print(f"Error loading experimental data: {str(e)}")
        return None

def process_simulation_data(config_path, mesh_dirs):
    results = {}
    x_positions_mm = [1, 50, 200, 650, 950]
    x_positions_m = [x/1000 for x in x_positions_mm]
    
    for mesh in mesh_dirs:
        path = config_path / mesh / "vol_solution.vtu"
        print(f"Processing: {path}")
        
        if not path.exists():
            print(f"Warning: Solution file not found at {path}")
            continue
            
        try:
            mesh_data = pv.read(path)
            if 'Velocity' not in mesh_data.array_names:
                print(f"Warning: Velocity data not found in {path}")
                continue
                
            velocity = mesh_data['Velocity']
            mesh_data['U'] = velocity[:, 0]
            mesh_data['U_norm'] = (mesh_data['U'] - 22.40)/19.14
            
            results[mesh] = {}
            for x_m, x_mm in zip(x_positions_m, x_positions_mm):
                profile = mesh_data.sample_over_line(
                    pointa=(x_m, -0.05, 0),
                    pointb=(x_m, 0.05, 0),
                    resolution=300
                )
                y_vals = profile.points[:, 1] * 1000  # Convert to mm
                y_norm = y_vals / DELTA_OMEGA[x_mm]
                u_norm = profile['U_norm']
                
                results[mesh][x_mm] = {
                    'y_norm': y_norm,
                    'u_norm': u_norm
                }
                
        except Exception as e:
            print(f"Error processing {mesh}: {str(e)}")
            continue
            
    return results

def create_plots(exp_data, sim_results, output_dir):
    mesh_dirs = list(sim_results.keys())
    x_positions_mm = [1, 50, 200, 650, 950]
    mesh_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    exp_style = {'marker':'o', 'color':'k', 's':20, 'linewidths':1, 'zorder':10, 'facecolors':'none'}
    
    os.makedirs(output_dir, exist_ok=True)
    
    for x_mm in x_positions_mm:
        plt.figure(figsize=(10, 6))
        
        # Plot simulation results first
        for mesh, color in zip(mesh_dirs, mesh_colors):
            if mesh in sim_results and x_mm in sim_results[mesh]:
                data = sim_results[mesh][x_mm]
                plt.plot(data['u_norm'], data['y_norm'],
                        label=f"Mesh {mesh}",
                        color=color,
                        linewidth=2,
                        alpha=0.8)
        
        # Plot experimental data on top
        if exp_data is not None and x_mm in exp_data:
            exp_df = exp_data[x_mm]
            print(f"Experimental data points for x={x_mm}mm:\n{exp_df}")
            
            plt.scatter(exp_df['U_norm'], 
                       exp_df['Y_mm']/DELTA_OMEGA[x_mm],
                       label='Experimental',
                       **exp_style)
        else:
            print(f"Warning: No experimental data for x={x_mm}mm")
        
        plt.xlabel(r"$(U-U_1)/\Delta U$", fontsize=12)
        plt.ylabel(r"$y/\delta_\omega$", fontsize=12)
        plt.title(f"Mixing Layer Profile at x = {x_mm} mm For SST Model", fontsize=14)
        plt.grid(True, linestyle=':', alpha=0.5)
        plt.legend(fontsize=10, framealpha=1)
        
        output_path = os.path.join(output_dir, f"profile_x{x_mm}mm.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved: {output_path}")

if __name__ == "__main__":
    try:
        # Get current directory (config directory)
        config_path = Path(os.getcwd())
        print(f"Current working directory: {config_path}")
        
        # Find all mesh directories
        mesh_dirs = [d.name for d in config_path.iterdir() 
                    if d.is_dir() and not d.name.startswith('.')]
        print(f"Found mesh directories: {mesh_dirs}")
        
        if not mesh_dirs:
            print("Error: No mesh directories found")
            sys.exit(1)
            
        # Load experimental data with more verbose logging
        print("\nLoading experimental data...")
        exp_data = load_exp_data(config_path)
        if exp_data is None:
            print("Warning: Could not load experimental data, will proceed without it")
        else:
            print("Successfully loaded experimental data")
        
        # Process simulation data
        print("\nProcessing simulation data...")
        sim_results = process_simulation_data(config_path, mesh_dirs)
        if not sim_results:
            print("Error: No simulation data processed")
            sys.exit(1)
            
        # Create plots directory
        plots_dir = config_path / "plots"
        
        # Generate plots with more verbose logging
        print("\nGenerating plots...")
        create_plots(exp_data, sim_results, plots_dir)
        
        print("\nAll plots generated successfully!")
        
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)