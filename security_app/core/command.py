import subprocess, time
from security_app.models import CmdResult

def run_command(cmd: str) -> CmdResult:
    started = time.time()
    try:
        result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
        duration = time.time() - started
        return CmdResult(
            cmd=cmd,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_sec=round(duration, 4),
            ok=(result.returncode == 0),
        )
    except Exception as e:
        duration = time.time() - started
        return CmdResult(
            cmd=cmd,
            returncode=None,
            stdout="",
            stderr=str(e),
            duration_sec=round(duration, 4),
            ok=False,
        )
