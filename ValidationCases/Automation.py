#!/usr/bin/env python3
"""
SU2 Validation Automation Script
Runs SU2 simulations on all meshes in a validation case configuration
"""

import os
import sys
import argparse
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, 
                              capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {cmd}")
        print(f"Exit code: {e.returncode}")
        print(f"Error output:\n{e.stderr}")
        print(f"Standard output:\n{e.stdout}")
        return None

def copy_files_from_vandv(vandv_path, main_path, config_name):
    """Copy mesh and restart files from VandV repo to main repo"""
    vandv_config_path = Path(vandv_path) / config_name
    main_config_path = Path(main_path) / config_name
    
    if not vandv_config_path.exists():
        print(f"VandV path not found: {vandv_config_path}")
        return False
    
    if not main_config_path.exists():
        print(f"Main path not found: {main_config_path}")
        return False
    
    # Find all mesh folders in VandV repo
    for mesh_folder in vandv_config_path.iterdir():
        if mesh_folder.is_dir():
            target_mesh_folder = main_config_path / mesh_folder.name
            
            if target_mesh_folder.exists():
                print(f"Copying files to {target_mesh_folder}")
                
                # Copy restart file
                restart_files = list(mesh_folder.glob("*.dat"))
                for restart_file in restart_files:
                    shutil.copy2(restart_file, target_mesh_folder)
                    print(f"  Copied {restart_file.name}")
                
                # Copy mesh file
                mesh_files = list(mesh_folder.glob("*.su2"))
                for mesh_file in mesh_files:
                    shutil.copy2(mesh_file, target_mesh_folder)
                    print(f"  Copied {mesh_file.name}")
    
    return True

def copy_config_to_meshes(config_path, mesh_folders):
    """Copy configuration file to all mesh folders"""
    config_file = config_path / "Config.cfg"
    
    if not config_file.exists():
        print(f"Config file not found: {config_file}")
        return False
    
    for mesh_folder in mesh_folders:
        if mesh_folder.is_dir():
            target_config = mesh_folder / "Config.cfg"
            shutil.copy2(config_file, target_config)
            print(f"Copied config to {mesh_folder.name}")
    
    return True

def run_su2_simulation(mesh_folder):
    """Run SU2 simulation in a mesh folder"""
    config_file = mesh_folder / "Config.cfg"
    
    if not config_file.exists():
        print(f"Config file not found in {mesh_folder}")
        return False
    
    print(f"Running SU2 simulation in {mesh_folder.name}")
    
    # Run SU2_CFD with full path
    cmd = f"SU2_CFD {config_file}"
    result = run_command(cmd, cwd=mesh_folder)
    
    if result is not None:
        # Verify results were generated
        history_file = mesh_folder / "history.csv"
        solution_file = mesh_folder / "vol_solution.vtu"
        
        if history_file.exists() and solution_file.exists():
            print(f"  Simulation completed successfully for {mesh_folder.name}")
            return True
        else:
            print(f"  Simulation completed but results missing for {mesh_folder.name}")
            return False
    else:
        print(f"  Simulation failed for {mesh_folder.name}")
        return False

def run_plot_script(config_path, args):
    """Run Plot.py script to generate validation plots"""
    plot_script = config_path / "Plot.py"
    
    if not plot_script.exists():
        print(f"Plot.py not found in {config_path}")
        return False
    
    print(f"Running Plot.py in {config_path}")
    cmd = (f"python3 Plot.py --category {args.category} --case-code {args.case_code} "
          f"--turbulence-model {args.turbulence_model} --configuration {args.configuration} "
          f"--main-path {args.main_path}")
    result = run_command(cmd, cwd=config_path)
    
    if result is not None:
        # Verify plots were generated
        plots_dir = config_path / "plots"
        if plots_dir.exists() and any(plots_dir.iterdir()):
            print("  Plots generated successfully")
            return True
        else:
            print("  Plot script ran but no plots were generated")
            return False
    else:
        print("  Plot generation failed")
        return False

def collect_results(config_path, output_path):
    """Collect all results and organize them"""
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all mesh folders
    mesh_folders = [d for d in config_path.iterdir() if d.is_dir() and d.name.startswith(('Mesh', 'mesh', '1', '2', '3', '4', '5'))]
    
    # Copy results from each mesh folder
    for i, mesh_folder in enumerate(mesh_folders, 1):
        mesh_result_dir = output_dir / f"Mesh{i}"
        mesh_result_dir.mkdir(exist_ok=True)
        
        # Copy simulation results
        for pattern in ['*.csv', '*.vtu', '*.cfg', '*.dat', '*.su2']:
            for file in mesh_folder.glob(pattern):
                shutil.copy2(file, mesh_result_dir)
        
        print(f"Collected results from {mesh_folder.name}")
    
    # Copy plots
    plots_dir = config_path / "plots"
    if plots_dir.exists():
        target_plots_dir = output_dir / "plots"
        if target_plots_dir.exists():
            shutil.rmtree(target_plots_dir)
        shutil.copytree(plots_dir, target_plots_dir)
        print("Collected plots")

def main():
    parser = argparse.ArgumentParser(description='SU2 Validation Automation')
    parser.add_argument('--category', required=True, help='Validation case category')
    parser.add_argument('--case-code', required=True, help='Validation case code')
    parser.add_argument('--turbulence-model', required=True, help='Turbulence model')
    parser.add_argument('--configuration', required=True, help='Configuration name')
    parser.add_argument('--vandv-path', required=True, help='VandV repository path')
    parser.add_argument('--main-path', required=True, help='Main repository path')
    parser.add_argument('--output-path', required=True, help='Output path for results')
    
    args = parser.parse_args()
    
    # Construct paths
    config_path = Path(args.main_path) / args.configuration
    
    print(f"Starting SU2 validation for {args.category}/{args.case_code}/{args.turbulence_model}/{args.configuration}")
    
    # Step 1: Copy files from VandV repo
    print("Step 1: Copying files from VandV repository...")
    if not copy_files_from_vandv(args.vandv_path, args.main_path, args.configuration):
        print("Failed to copy files from VandV repository")
        return 1
    
    # Step 2: Copy config to mesh folders
    print("Step 2: Copying configuration to mesh folders...")
    mesh_folders = [d for d in config_path.iterdir() if d.is_dir() and d.name.startswith(('Mesh', 'mesh', '1', '2', '3', '4', '5'))]
    if not copy_config_to_meshes(config_path, mesh_folders):
        print("Failed to copy configuration files")
        return 1
    
    # Step 3: Run SU2 simulations
    print("Step 3: Running SU2 simulations...")
    simulation_success = True
    for mesh_folder in mesh_folders:
        if not run_su2_simulation(mesh_folder):
            simulation_success = False
    
    if not simulation_success:
        print("Warning: Some simulations failed")
    
    # Step 4: Generate plots (only if at least one simulation succeeded)
    print("Step 4: Generating plots...")
    if simulation_success:
        if not run_plot_script(config_path, args):
            print("Plot generation failed")
    else:
        print("Skipping plot generation due to failed simulations")
    
    # Step 5: Collect results
    print("Step 5: Collecting results...")
    collect_results(config_path, args.output_path)
    
    print("SU2 validation automation completed!")
    return 0 if simulation_success else 2  # Return 2 for partial success

if __name__ == "__main__":
    sys.exit(main())