from tools.base import Tool, ToolKind, ToolInvocation, ToolResult
from pydantic import BaseModel, Field
from pathlib import Path
import fnmatch
import asyncio
import os
import sys

BLOCKED_COMMANDS = {
    "rm -rf /",
    "rm -rf ~",
    "rm -rf /*",
    "dd if=/dev/zero",
    "dd if=/dev/random",
    "mkfs",
    "fdisk",
    "parted",
    ":(){ :|:& };:",  # Fork bomb
    "chmod 777 /",
    "chmod -R 777",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init 0",
    "init 6",
}


class ShellParams(BaseModel):
    command: str = Field(..., description="The shell command to execute")
    timeout: int = Field(
        120, ge=1, le=600, description="Timeout in seconds (default: 120)"
    )
    cwd: str | None = Field(None, description="Working directory for the command")


class ShellTool(Tool):
    name = "shell"
    kind = ToolKind.SHELL
    description = "Execute a shell command. Use this for running system commands, scripts, or any terminal-based operations."
    schema = ShellParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = ShellParams(**invocation.params)

        command = params.command.strip()
        for blocked in BLOCKED_COMMANDS:
            if blocked in command:
                return ToolResult.error_result(
                    f"command blocked for safety reasons: {params.command}",
                    metadata={"blocked": True},
                )

        if params.cwd:
            cwd = Path(params.cwd)
            if not cwd.is_absolute():
                cwd = invocation.cwd / cwd
        else:
            cwd = invocation.cwd

        if not cwd.exists():
            return ToolResult.error_result(
                f"working directory does not exist: {cwd}",
            )

        env = self._build_environment()

        if sys.platform == "win32":
            shell_cmd = ["cmd.exe", "/c", params.command]
        else:
            shell_cmd = ["sh", "-c", params.command]

        process = await asyncio.create_subprocess_exec(
            *shell_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
            env=env,
            start_new_session=True,
        )

        try:
            stdout_data, stderr_data = await asyncio.wait_for(
                process.communicate(),
                timeout=params.timeout,
            )
        except asyncio.TimeoutError:
            if sys.platform != "win32":
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            else:
                process.kill()
            await process.wait()
            return ToolResult.error_result(
                f"command timed out after {params.timeout} seconds"
            )

        stdout = stdout_data.decode("utf-8", errors="replace").strip()
        stderr = stderr_data.decode("utf-8", errors="replace").strip()
        output = ""
        if stdout.strip():
            output += stdout.rstrip() + "\n"

        if stderr.strip():
            output += "\n--- stderr ---\n"
            output += stderr.rstrip() + "\n"

        exit_code = process.returncode
        if exit_code != 0:
            output += "\n--- exit code ---\n"
            output += str(exit_code) + "\n"

        if len(output) > 100 * 1024:
            output = output[: 100 * 1024] + "\n... (truncated) ...\n"

        return ToolResult(
            success=exit_code == 0,
            error=stderr if exit_code != 0 else None,
            output=output,
            exit_code=exit_code,
        )

    def _build_environment(self) -> dict[str, str]:
        env = os.environ.copy()

        shell_environment = self.config.shell_environment

        if not shell_environment.ignore_default_excludes:
            for pattern in shell_environment.exclude_patterns:
                keys_to_remove = [
                    key
                    for key in env.keys()
                    if fnmatch.fnmatch(key.upper(), pattern.upper())
                ]
                for key in keys_to_remove:
                    del env[key]

        if shell_environment.set_vars:
            env.update(shell_environment.set_vars)

        return env
