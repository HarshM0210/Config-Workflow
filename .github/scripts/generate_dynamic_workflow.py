#!/usr/bin/env python3
"""
Script to generate dynamic GitHub Actions workflow based on SU2 configuration file
"""

import re
import sys
import yaml
from pathlib import Path

def parse_config_file(config_path):
    """Parse SU2 config file and extract all configuration options"""
    options = {}
    
    try:
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Find all configuration lines (not comments, containing =)
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('%') and not line.startswith('#') and '=' in line:
                # Split on first = only
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Skip empty keys
                if key:
                    options[key] = value
    
    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing config file: {e}")
        sys.exit(1)
    
    return options

def generate_workflow_inputs(options):
    """Generate GitHub Actions workflow inputs section"""
    inputs = {
        'category': {
            'description': 'Validation Case Category',
            'required': True,
            'type': 'choice',
            'options': ['Basic', 'Extended']
        },
        'case_name': {
            'description': 'Validation Case Name (e.g., 2D Mixing Layer)',
            'required': True,
            'type': 'string'
        },
        'case_code': {
            'description': 'Validation Case Code (e.g., 2DML)',
            'required': True,
            'type': 'string'
        }
    }
    
    # Add dynamic inputs for each config option
    for key, default_value in options.items():
        inputs[key] = {
            'description': f'{key}',
            'required': False,
            'type': 'string',
            'default': str(default_value)
        }
    
    return inputs

def generate_update_commands(options):
    """Generate sed commands to update configuration file"""
    commands = []
    
    for key in options.keys():
        # Escape special characters for sed
        escaped_key = key.replace('/', r'\/')
        command = f'''          if [ -n "${{{{ inputs.{key} }}}}" ]; then
            sed -i "s/^{escaped_key}=.*/{escaped_key}= ${{{{ inputs.{key} }}}}/" "$CONFIG_PATH"
          fi'''
        commands.append(command)
    
    return '\n'.join(commands)

def create_complete_workflow(options):
    """Create complete workflow YAML"""
    inputs = generate_workflow_inputs(options)
    update_commands = generate_update_commands(options)
    
    workflow = {
        'name': 'SU2 Validation Pipeline - Dynamic',
        'on': {
            'workflow_dispatch': {
                'inputs': inputs
            }
        },
        'jobs': {
            'validate': {
                'runs-on': 'ubuntu-latest',
                'steps': [
                    {
                        'name': 'Checkout SU2 Main Repo',
                        'uses': 'actions/checkout@v4',
                        'with': {
                            'path': 'su2-main'
                        }
                    },
                    {
                        'name': 'Checkout VandV Repo',
                        'uses': 'actions/checkout@v4',
                        'with': {
                            'repository': '${{ github.repository_owner }}/SU2-VandV',
                            'path': 'su2-vandv',
                            'token': '${{ secrets.GITHUB_TOKEN }}'
                        }
                    },
                    {
                        'name': 'Update Configuration Files',
                        'run': f'''CATEGORY="${{ inputs.category }}"
          CASE_CODE="${{ inputs.case_code }}"
          CONFIG_PATH="su2-main/VandV/$CATEGORY/$CASE_CODE/config.cfg"
          
          # Create updated config from template
          cp su2-main/template_config.cfg "$CONFIG_PATH"
          
          # Update configuration values based on user inputs
{update_commands}'''
                    },
                    {
                        'name': 'Copy Config to All Mesh Folders',
                        'run': '''CATEGORY="${{ inputs.category }}"
          CASE_CODE="${{ inputs.case_code }}"
          MAIN_PATH="su2-main/VandV/$CATEGORY/$CASE_CODE"
          CONFIG_PATH="$MAIN_PATH/config.cfg"
          
          # Copy updated config to all mesh folders
          for mesh_folder in "$MAIN_PATH"/*; do
            if [ -d "$mesh_folder" ] && [ "$(basename "$mesh_folder")" != "." ] && [ "$(basename "$mesh_folder")" != ".." ]; then
              cp "$CONFIG_PATH" "$mesh_folder/"
              echo "Copied config to $(basename "$mesh_folder")"
            fi
          done'''
                    },
                    {
                        'name': 'Copy Files from VandV Repo',
                        'run': '''CATEGORY="${{ inputs.category }}"
          CASE_CODE="${{ inputs.case_code }}"
          VANDV_PATH="su2-vandv/VandV/$CATEGORY/$CASE_CODE"
          MAIN_PATH="su2-main/VandV/$CATEGORY/$CASE_CODE"
          
          # Copy restart and mesh files from VandV repo to main repo
          for mesh_folder in "$VANDV_PATH"/*; do
            if [ -d "$mesh_folder" ]; then
              folder_name=$(basename "$mesh_folder")
              target_folder="$MAIN_PATH/$folder_name"
              
              if [ -d "$target_folder" ]; then
                echo "Copying files to $target_folder"
                
                # Copy restart file
                if [ -f "$mesh_folder/restart.dat" ]; then
                  cp "$mesh_folder/restart.dat" "$target_folder/"
                fi
                
                # Copy mesh file
                find "$mesh_folder" -name "*.su2" -exec cp {} "$target_folder/" \\;
              fi
            fi
          done'''
                    },
                    {
                        'name': 'Install Dependencies',
                        'run': '''sudo apt-get update
          sudo apt-get install -y build-essential cmake python3 python3-pip
          sudo apt-get install -y libopenmpi-dev openmpi-bin
          pip3 install numpy matplotlib pandas'''
                    },
                    {
                        'name': 'Build SU2',
                        'run': '''cd su2-main
          mkdir -p build
          cd build
          cmake .. -DCMAKE_BUILD_TYPE=Release
          make -j$(nproc)
          sudo make install'''
                    },
                    {
                        'name': 'Run Automation Script',
                        'run': '''cd su2-main/VandV/${{ inputs.category }}/${{ inputs.case_code }}
          if [ -f "../../Automation.py" ]; then
            python3 ../../Automation.py
          else
            echo "::warning::Automation.py not found, skipping simulation"
          fi'''
                    },
                    {
                        'name': 'Generate Plots',
                        'run': '''cd su2-main/VandV/${{ inputs.category }}/${{ inputs.case_code }}
          if [ -f "Plot.py" ]; then
            python3 Plot.py
          else
            echo "::warning::Plot.py not found, skipping plot generation"
          fi'''
                    },
                    {
                        'name': 'Collect Results',
                        'run': '''mkdir -p results
          find su2-main/VandV/${{ inputs.category }}/${{ inputs.case_code }} -name "*.csv" -exec cp {} results/ \\; 2>/dev/null || true
          find su2-main/VandV/${{ inputs.category }}/${{ inputs.case_code }} -name "*.vtu" -exec cp {} results/ \\; 2>/dev/null || true
          find su2-main/VandV/${{ inputs.category }}/${{ inputs.case_code }} -name "*.png" -exec cp {} results/ \\; 2>/dev/null || true
          find su2-main/VandV/${{ inputs.category }}/${{ inputs.case_code }} -name "*.jpg" -exec cp {} results/ \\; 2>/dev/null || true'''
                    },
                    {
                        'name': 'Upload Results as Artifacts',
                        'uses': 'actions/upload-artifact@v4',
                        'with': {
                            'name': 'su2-validation-results-${{ inputs.case_code }}',
                            'path': 'results/'
                        }
                    },
                    {
                        'name': 'Deploy to Website Repo',
                        'if': 'success()',
                        'run': '''# Clone website repo
          git clone https://${{ secrets.GITHUB_TOKEN }}@github.com/${{ github.repository_owner }}/SU2-Website.git website
          cd website
          
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          
          # Create new branch with case name
          BRANCH_NAME="${{ inputs.case_name }}"
          git checkout -b "$BRANCH_NAME" 2>/dev/null || git checkout "$BRANCH_NAME"
          
          # Create folder structure
          mkdir -p "vandv_files/${{ inputs.case_name }}"
          
          # Copy plot files to website repo
          find ../results -name "*.png" -exec cp {} "vandv_files/${{ inputs.case_name }}/" \\; 2>/dev/null || true
          find ../results -name "*.jpg" -exec cp {} "vandv_files/${{ inputs.case_name }}/" \\; 2>/dev/null || true
          
          # Commit and push if there are changes
          if [ -n "$(git status --porcelain)" ]; then
            git add .
            git commit -m "Add validation results for ${{ inputs.case_name }}"
            git push origin "$BRANCH_NAME"
          else
            echo "No changes to commit"
          fi'''
                    }
                ]
            }
        }
    }
    
    return workflow

def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_dynamic_workflow.py <config_file_path>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    # Parse configuration file
    options = parse_config_file(config_path)
    print(f"Found {len(options)} configuration options")
    
    # Generate complete workflow
    workflow = create_complete_workflow(options)
    
    # Write workflow file
    output_path = Path('.github/workflows/su2_validation_dynamic.yml')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        yaml.dump(workflow, f, default_flow_style=False, sort_keys=False, width=1000)
    
    print(f"Generated dynamic workflow at {output_path}")
    print(f"Workflow includes inputs for: {', '.join(list(options.keys())[:10])}{'...' if len(options) > 10 else ''}")

if __name__ == "__main__":
    main()