#!/usr/bin/env python3
"""
SU2 Validation Automation Script
Handles both single configuration and 'All' configurations cases
"""

import argparse
import subprocess
import sys
from pathlib import Path
import time
import logging
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SU2Automation:
    def __init__(self):
        self.su2_timeout = 3600  # 1 hour timeout for SU2 runs
        self.start_time = time.time()

    def run_su2_simulation(self, mesh_dir: Path) -> bool:
        """Run SU2_CFD in the specified mesh directory"""
        cfg_file = mesh_dir / "Config.cfg"
        
        if not cfg_file.exists():
            logger.error(f"Config.cfg not found in {mesh_dir}")
            return False

        logger.info(f"Starting SU2 simulation in {mesh_dir.name}")
        
        try:
            result = subprocess.run(
                ["SU2_CFD", str(cfg_file)],
                cwd=mesh_dir,
                check=True,
                timeout=self.su2_timeout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Verify output files were created
            if not any(mesh_dir.glob("*.vtu")) and not any(mesh_dir.glob("*.csv")):
                logger.error(f"No output files generated in {mesh_dir.name}")
                return False
                
            logger.info(f"SU2 completed successfully in {mesh_dir.name}")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"SU2 timed out in {mesh_dir.name}")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"SU2 failed in {mesh_dir.name}\nError: {e.stderr}")
            return False

    def run_plot_script(self, config_dir: Path) -> bool:
        """Execute Plot.py in the configuration directory"""
        plot_script = config_dir / "Plot.py"
        
        if not plot_script.exists():
            logger.error(f"Plot.py not found in {config_dir}")
            return False

        logger.info(f"Running Plot.py in {config_dir.name}")
        
        try:
            result = subprocess.run(
                [sys.executable, str(plot_script)],
                cwd=config_dir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if not any(config_dir.glob("*.png")) and not any(config_dir.glob("*.pdf")):
                logger.warning(f"No plot files generated in {config_dir.name}")
                
            logger.info(f"Plotting completed in {config_dir.name}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Plot.py failed in {config_dir.name}\nError: {e.stderr}")
            return False

    def get_mesh_directories(self, config_dir: Path) -> List[Path]:
        """Get all non-hidden subdirectories (mesh folders)"""
        return [d for d in config_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]

    def process_configuration(self, config_path: Path) -> bool:
        """Process a single configuration directory"""
        if not config_path.exists():
            logger.error(f"Configuration path not found: {config_path}")
            return False

        mesh_dirs = self.get_mesh_directories(config_path)
        if not mesh_dirs:
            logger.error(f"No mesh directories found in {config_path}")
            return False

        logger.info(f"Processing {config_path.name} with {len(mesh_dirs)} meshes")
        
        # Run SU2 for each mesh
        success_count = 0
        for mesh_dir in mesh_dirs:
            if self.run_su2_simulation(mesh_dir):
                success_count += 1

        if success_count != len(mesh_dirs):
            logger.warning(f"Only {success_count}/{len(mesh_dirs)} meshes completed successfully")

        # Run plotting script
        plot_success = self.run_plot_script(config_path)
        
        return plot_success and (success_count > 0)

    def run(self, category: str, case_code: str, model: str, config: str):
        """Main execution method"""
        base_path = Path("ValidationCases") / category / case_code / model
        
        if not base_path.exists():
            logger.error(f"Base path not found: {base_path}")
            sys.exit(1)

        if config.lower() == "all":
            config_dirs = [d for d in base_path.iterdir() 
                         if d.is_dir() and d.name.lower().startswith("configuration")]
            
            if not config_dirs:
                logger.error(f"No configuration directories found in {base_path}")
                sys.exit(1)
                
            logger.info(f"Processing ALL configurations ({len(config_dirs)} found)")
            
            for config_dir in config_dirs:
                self.process_configuration(config_dir)
        else:
            config_path = base_path / config
            self.process_configuration(config_path)

        logger.info(f"Automation completed in {time.time() - self.start_time:.2f} seconds")

def main():
    parser = argparse.ArgumentParser(
        description="SU2 Validation Automation Script",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--category', 
        required=True,
        choices=['Basic', 'Extended'],
        help='Validation case category'
    )
    parser.add_argument(
        '--case_code', 
        required=True,
        help='Validation case code (e.g., 2DML)'
    )
    parser.add_argument(
        '--model', 
        required=True,
        choices=['SA', 'SST'],
        help='Turbulence model'
    )
    parser.add_argument(
        '--config', 
        required=True,
        help='Configuration name or "All"'
    )

    args = parser.parse_args()
    
    automation = SU2Automation()
    automation.run(
        category=args.category,
        case_code=args.case_code,
        model=args.model,
        config=args.config
    )

if __name__ == "__main__":
    main()