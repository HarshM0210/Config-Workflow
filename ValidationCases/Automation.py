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
        print(f"Error running command: {cmd}")
        print(f"Error: {e.stderr}")
        return None

def copy_files_mesh(mesh_path, main_path, config_name):
    """Copy mesh files to main repo"""
    mesh_config_path = Path(mesh_path)
    main_config_path = Path(main_path) / config_name
    
    if not mesh_config_path.exists():
        print(f"Mesh path not found: {mesh_config_path}")
        return False
    
    if not main_config_path.exists():
        print(f"Main path not found: {main_config_path}")
        return False
    
    # Find all mesh folders
    for mesh_folder in mesh_config_path.iterdir():
        if mesh_folder.is_dir() and not mesh_folder.name.startswith('.'):
            target_mesh_folder = main_config_path / mesh_folder.name
            
            if target_mesh_folder.exists():
                print(f"Copying files to {target_mesh_folder}")
                
                # Copy mesh file
                mesh_files = list(mesh_folder.glob("*.su2"))
                for mesh_file in mesh_files:
                    shutil.copy2(mesh_file, target_mesh_folder)
            else: 
                print(f"Error: Target folder does not exist — {target_mesh_folder}") 
                return False
    
    return True

def copy_files_restart(restart_path, main_path, config_name):
    """Copy restart files to main repo"""
    restart_config_path = Path(restart_path) / config_name
    main_config_path = Path(main_path) / config_name

    if not restart_config_path.exists():
        print(f"Restart path not found: {restart_config_path}")
        return False

    if not main_config_path.exists():
        print(f"Main path not found: {main_config_path}")
        return False
    
    # Find all restart folders
    for mesh_folder in restart_config_path.iterdir():
        if mesh_folder.is_dir() and not mesh_folder.name.startswith('.'):
            target_mesh_folder = main_config_path / mesh_folder.name
            
            if target_mesh_folder.exists():
                print(f"Copying files to {target_mesh_folder}")
                
                # Copy restart file
                restart_files = list(mesh_folder.glob("*.dat"))
                for restart_file in restart_files:
                    shutil.copy2(restart_file, target_mesh_folder)
            else: 
                print(f"Error: Target folder does not exist — {target_mesh_folder}") 
                return False
    
    return True

def copy_config_to_meshes(config_path, mesh_folders):
    """Copy configuration file to all mesh folders"""
    config_file = config_path / "Config.cfg"
    
    if not config_file.exists():
        print(f"Config file not found: {config_file}")
        return False
    
    for mesh_folder in mesh_folders:
        if mesh_folder.is_dir() and not mesh_folder.name.startswith('.'):
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
    
    # Run SU2_CFD
    cmd = f"SU2_CFD Config.cfg"
    result = run_command(cmd, cwd=mesh_folder)
    
    if result is not None:
        print(f"  Simulation completed for {mesh_folder.name}")
        return True
    else:
        print(f"  Simulation failed for {mesh_folder.name}")
        return False

def run_plot_script(config_path):
    """Run Plot.py script to generate validation plots"""
    plot_script = config_path / "Plot.py"
    
    if not plot_script.exists():
        print(f"Plot.py not found in {config_path}")
        return False
    
    print(f"Running Plot.py in {config_path}")
    cmd = f"python3 Plot.py"
    result = run_command(cmd, cwd=config_path)
    
    if result is not None:
        print("  Plots generated successfully")
        return True
    else:
        print("  Plot generation failed")
        return False


def collect_results(config_path, output_path):
    """Collect all results and organize them"""
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all mesh folders
    mesh_folders = [d for d in config_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    # Copy results from each mesh folder
    for mesh_folder in mesh_folders:
        mesh_result_dir = output_dir / mesh_folder.name
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
    parser.add_argument('--mesh-path', required=True, help='Mesh repository path')
    parser.add_argument('--restart-path', required=True, help='Restart repository path')
    parser.add_argument('--main-path', required=True, help='Main repository path')
    parser.add_argument('--output-path', required=True, help='Output path for results')
    
    args = parser.parse_args()
    
    # Construct paths
    config_path = Path(args.main_path) / args.configuration
    
    print(f"Starting SU2 validation for {args.category}/{args.case_code}/{args.turbulence_model}/{args.configuration}")

    # Step 1: Copy Mesh files from Google Drive
    print("Step 1: Copying Mesh files...")
    if not copy_files_mesh(args.mesh_path, args.main_path, args.configuration):
        print("Failed to copy files from Mesh repository")
        return 1
    
    # Step 2: Copy Restart from Google Drive
    print("Step 2: Copying Restart files...")
    if not copy_files_restart(args.restart_path, args.main_path, args.configuration):
        print("Failed to copy files from Restart repository")
        return 1
    
    # Step 3: Copy config to mesh folders
    print("Step 3: Copying configuration to mesh folders...")
    mesh_folders = [d for d in config_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
    if not copy_config_to_meshes(config_path, mesh_folders):
        print("Failed to copy configuration files")
        return 1
    
    # Step 4: Run SU2 simulations
    print("Step 4: Running SU2 simulations...")
    simulation_success = True
    for mesh_folder in mesh_folders:
        if not run_su2_simulation(mesh_folder):
            simulation_success = False
    
    if not simulation_success:
        print("Some simulations failed.")
        return 1
    
    # Step 5: Generate plots
    print("Step 5: Generating plots...")
    if not run_plot_script(config_path):
        print("Plot generation failed, but continuing...")
    
    # Step 6: Collect results
    print("Step 6: Collecting results...")
    collect_results(config_path, args.output_path)
    
    print("SU2 Validation Automation Completed Successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())