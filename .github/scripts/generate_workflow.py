# .github/scripts/generate_workflow.py
import json
import os
import re

def escape_sed_pattern(s):
    """Escape special characters for sed patterns"""
    return re.sub(r'([\/&])', r'\\\1', s)

def generate_workflow():
    # Load config keys
    with open('artifacts/config_options.json') as f:
        config_keys = json.load(f)

    # Generate inputs section
    inputs_yaml = ""
    for key in config_keys:
        inputs_yaml += f"""      {key}:
        description: "Set value for {key}"
        required: false
        type: string
"""

    # Generate update commands
    update_commands = ""
    for key in config_keys:
        escaped_key = escape_sed_pattern(key)
        update_commands += f"""      if [ -n "${{{{ github.event.inputs.{key} }}}" ]; then
        sed -i "s/^{escaped_key} *=.*/{escaped_key}= ${{{{ github.event.inputs.{key} }}}/" "$CONFIG_PATH"
      fi
"""

    # Complete workflow template
    workflow_template = f"""name: Dynamic Config Update
on:
  workflow_dispatch:
    inputs:
      case_code:
        description: "Validation Case Code"
        required: true
        type: string
{inputs_yaml}
jobs:
  update-config-file:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Update config file
        run: |
          CONFIG_PATH="VandV/${{{{ github.event.inputs.case_code }}}}/config_sa_restart.cfg"
          cp artifacts/original_config.cfg "$CONFIG_PATH"
{update_commands}
      - name: Commit changes
        run: |
          git config --global user.name "GitHub Actions"
          git config --global user.email "actions@github.com"
          git add "VandV/${{{{ github.event.inputs.case_code }}}}/config_sa_restart.cfg"
          git commit -m "Updated config for ${{{{ github.event.inputs.case_code }}}}"
          git push
"""

    # Write the workflow file
    os.makedirs('.github/workflows', exist_ok=True)
    with open('.github/workflows/dynamic_config.yml', 'w') as f:
        f.write(workflow_template)

if __name__ == "__main__":
    generate_workflow()