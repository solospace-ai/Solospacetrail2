"""
Code Executor Tool - Python code execution in sandboxed subprocess
"""
import asyncio
import subprocess
import tempfile
import os
from typing import Dict, Any, Optional
from pathlib import Path


class CodeExecutorTool:
    """Sandboxed Python code execution tool."""
    
    name = "code_executor"
    description = "Execute Python code in a sandboxed environment"
    
    def __init__(self, timeout: int = 30, memory_limit: str = "256M"):
        self.timeout = timeout
        self.memory_limit = memory_limit
        self.allowed_modules = {
            "math", "random", "statistics", "datetime", "collections",
            "itertools", "functools", "re", "json", "csv", "typing",
            "dataclasses", "enum", "pathlib", "io", "string", "textwrap"
        }
    
    async def execute(self, code: str, input_data: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute Python code in a sandboxed subprocess.
        
        Args:
            code: Python code to execute
            input_data: Optional input data to pass to the script
            
        Returns:
            Dict with execution result
        """
        # Security check - block dangerous operations
        dangerous_patterns = [
            "__import__", "importlib", "subprocess", "os.system", "eval(",
            "exec(", "compile(", "open(", "file(", "socket", "urllib",
            "requests", "httpx", "aiohttp", "ftplib", "smtplib"
        ]
        
        for pattern in dangerous_patterns:
            if pattern in code:
                return {
                    "success": False,
                    "error": f"Blocked dangerous operation: {pattern}",
                    "stdout": "",
                    "stderr": ""
                }
        
        # Create temporary directory and file
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                script_path = Path(tmpdir) / "script.py"
                
                # Wrap user code with safety measures
                wrapped_code = f"""
import sys
import io

# Redirect stdout/stderr
old_stdout = sys.stdout
old_stderr = sys.stderr
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()

try:
{chr(10).join('    ' + line for line in code.split(chr(10)))}
except Exception as e:
    print(f"Error: {{e}}", file=sys.stderr)

# Get outputs
stdout_output = sys.stdout.getvalue()
stderr_output = sys.stderr.getvalue()

# Restore
sys.stdout = old_stdout
sys.stderr = old_stderr

print(stdout_output, end='')
print(stderr_output, file=sys.stderr, end='')
"""
                
                script_path.write_text(wrapped_code)
                
                # Set up environment
                env = os.environ.copy()
                env["PYTHONPATH"] = tmpdir
                
                # Run the script
                try:
                    process = await asyncio.wait_for(
                        asyncio.create_subprocess_exec(
                            "python",
                            str(script_path),
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            cwd=tmpdir,
                            env=env
                        ),
                        timeout=self.timeout
                    )
                    
                    # Send input if provided
                    stdin_data = input_data.encode() if input_data else None
                    
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(input=stdin_data),
                        timeout=self.timeout
                    )
                    
                    return {
                        "success": process.returncode == 0,
                        "returncode": process.returncode,
                        "stdout": stdout.decode("utf-8", errors="replace"),
                        "stderr": stderr.decode("utf-8", errors="replace")
                    }
                    
                except asyncio.TimeoutError:
                    return {
                        "success": False,
                        "error": f"Execution timed out after {self.timeout} seconds",
                        "stdout": "",
                        "stderr": ""
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": ""
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """Return the tool's input schema."""
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                },
                "input_data": {
                    "type": "string",
                    "description": "Optional input data to pass to the script"
                }
            },
            "required": ["code"]
        }
