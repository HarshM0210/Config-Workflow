import argparse
import subprocess
import sys
from pathlib import Path
import time
import logging
from typing import List, Tuple
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('automation.log')
    ]
)
logger = logging.getLogger(__name__)

class SU2Automation:
    def __init__(self):
        self.su2_timeout = 600  # 10 minutes timeout for SU2 runs
        self.start_time = time.time()
        self.required_files = ['Config.cfg', 'Plot.py']
        self.mesh_extensions = ('.su2', '.mesh', '.msh')
        self.restart_extensions = ('.dat', '.csv')

    def validate_directory_structure(self, config_dir: Path) -> Tuple[bool, List[Path]]:
        """Strict validation requiring exactly one of each file type per mesh folder"""
        # 1. Check for Plot.py in config directory (mandatory)
        if not (config_dir / "Plot.py").exists():
            logger.error(f"Plot.py not found in {config_dir}")
            return False, []

        # 2. Get all mesh directories (non-hidden subdirectories)
        mesh_dirs = [d for d in config_dir.iterdir() 
                if d.is_dir() and not d.name.startswith('.')]
    
        if not mesh_dirs:
            logger.error(f"No mesh directories found in {config_dir}")
            return False, []

        # 3. Strict validation for each mesh directory
        valid_mesh_dirs = []
        for mesh_dir in mesh_dirs:
            # Check for exactly one Config.cfg
            cfg_files = list(mesh_dir.glob("Config.cfg"))
            if len(cfg_files) != 1:
                logger.error(f"Expected exactly one Config.cfg in {mesh_dir}, found {len(cfg_files)}")
                return False, []
        
            # Check for exactly one mesh file (.su2, .mesh, .msh)
            mesh_files = [f for ext in self.mesh_extensions 
                     for f in mesh_dir.glob(f"*{ext}")]
            if len(mesh_files) != 1:
                logger.error(f"Expected exactly one mesh file (*{self.mesh_extensions}) in {mesh_dir}, found {len(mesh_files)}")
                return False, []
        
            # Check for exactly one restart file (.dat, .csv)
            restart_files = [f for ext in self.restart_extensions 
                        for f in mesh_dir.glob(f"*{ext}")]
            if len(restart_files) != 1:
                logger.error(f"Expected exactly one restart file (*{self.restart_extensions}) in {mesh_dir}, found {len(restart_files)}")
                return False, []
        
            valid_mesh_dirs.append(mesh_dir)
    
        # If we get here, all checks passed
        logger.info(f"Validated {len(valid_mesh_dirs)} mesh directories in {config_dir}")
        return True, valid_mesh_dirs

    def run_su2_simulation(self, mesh_dir: Path) -> bool:
        """Run SU2_CFD in the specified mesh directory"""
        cfg_file = mesh_dir / "Config.cfg"
        logger.info(f"Starting SU2 simulation in {mesh_dir.name}")
        
        try:
            # Run SU2_CFD with the configuration file
            result = subprocess.run(
                ["SU2_CFD", str(cfg_file)],
                cwd=mesh_dir,
                check=True,
                timeout=self.su2_timeout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Log SU2 output for debugging
            with open(mesh_dir / "su2_output.log", 'w') as f:
                f.write(result.stdout)
            
            # Verify output files were created
            output_files = list(mesh_dir.glob("*.vtu")) + list(mesh_dir.glob("*.csv"))
            if not output_files:
                logger.error(f"No output files generated in {mesh_dir.name}")
                return False
                
            logger.info(f"SU2 completed successfully in {mesh_dir.name}")
            return True
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"SU2 timed out in {mesh_dir.name}")
            # Write any partial output to file
            if hasattr(e, 'stdout') and e.stdout:
                with open(mesh_dir / "su2_timeout.log", 'w') as f:
                    f.write(e.stdout)
            return False
            
        except subprocess.CalledProcessError as e:
            logger.error(f"SU2 failed in {mesh_dir.name}")
            # Write error output to file
            with open(mesh_dir / "su2_error.log", 'w') as f:
                f.write(f"STDOUT:\n{e.stdout}\n\nSTDERR:\n{e.stderr}")
            return False

    def run_plot_script(self, config_dir: Path) -> bool:
        """Execute Plot.py in the configuration directory"""
        plot_script = config_dir / "Plot.py"
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
            
            # Log plotting output
            with open(config_dir / "plot_output.log", 'w') as f:
                f.write(result.stdout)
            
            # Verify plot files were created
            plot_files = list(config_dir.glob("*.png")) + list(config_dir.glob("*.pdf"))
            if not plot_files:
                logger.warning(f"No plot files generated in {config_dir.name}")
                return False
                
            logger.info(f"Plotting completed in {config_dir.name}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Plot.py failed in {config_dir.name}")
            with open(config_dir / "plot_error.log", 'w') as f:
                f.write(f"STDOUT:\n{e.stdout}\n\nSTDERR:\n{e.stderr}")
            return False

    def process_configuration(self, config_path: Path) -> bool:
        """Process a single configuration directory"""
        logger.info(f"Processing configuration: {config_path.name}")
        
        # Validate directory structure
        is_valid, mesh_dirs = self.validate_directory_structure(config_path)
        if not is_valid:
            return False

        # Run SU2 for each mesh directory
        success_count = 0
        for mesh_dir in mesh_dirs:
            if self.run_su2_simulation(mesh_dir):
                success_count += 1
            else:
                # Early exit if any simulation fails
                logger.error(f"Aborting - simulation failed in {mesh_dir.name}")
                return False

        # Only proceed if ALL simulations succeeded
        if success_count == len(mesh_dirs):
            logger.info(f"All {len(mesh_dirs)} SU2 simulations completed successfully")
            return self.run_plot_script(config_path)
        else:
            logger.error("Unexpected state: Some simulations failed but weren't caught")
            return False

    def run(self, category: str, case_code: str, model: str, config: str):
        """Main execution method - handles single configurations"""
        config_path = Path("ValidationCases") / category / case_code / model / config
    
        if not config_path.exists():
            logger.error(f"Configuration path not found: {config_path}")
            sys.exit(1)

        if not self.process_configuration(config_path):
            sys.exit(1)

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