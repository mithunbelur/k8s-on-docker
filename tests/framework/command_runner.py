"""
Command execution utilities for the test framework.
"""

import subprocess
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class CommandRunner:
    """Utility class for running shell commands."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def debug_print(self, message: str):
        """Print debug message to stdout."""
        if self.debug:
            print(message, flush=True)
    
    def run_command(self, cmd: str, capture_output: bool = True, timeout: int = 60) -> Dict:
        """Run a shell command and return result."""
        try:
            logger.info(f"Executing: {cmd}")
            
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=capture_output,
                text=True,
                timeout=timeout
            )
            
            command_result = {
                'returncode': result.returncode,
                'stdout': result.stdout.strip() if result.stdout else "",
                'stderr': result.stderr.strip() if result.stderr else "",
                'success': result.returncode == 0
            }
            
            # Print debug output if enabled
            if self.debug:
                self.debug_print(f"\n[DEBUG] Command: {cmd}")
                self.debug_print(f"[DEBUG] Return code: {command_result['returncode']}")
                if command_result['stdout']:
                    self.debug_print(f"[DEBUG] STDOUT:\n{command_result['stdout']}")
                if command_result['stderr']:
                    self.debug_print(f"[DEBUG] STDERR:\n{command_result['stderr']}")
                self.debug_print(f"[DEBUG] Success: {command_result['success']}\n")
            
            return command_result
            
        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out: {cmd}"
            logger.error(error_msg)
            self.debug_print(f"\n[DEBUG] {error_msg}\n")
            return {
                'returncode': -1,
                'stdout': "",
                'stderr': "Command timed out",
                'success': False
            }
        except Exception as e:
            error_msg = f"Command failed: {cmd}, Error: {e}"
            logger.error(error_msg)
            self.debug_print(f"\n[DEBUG] {error_msg}\n")
            return {
                'returncode': -1,
                'stdout': "",
                'stderr': str(e),
                'success': False
            }
