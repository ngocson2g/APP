import subprocess, time

def run_command(cmd):
    started = time.time()
    try:
        result = subprocess.run(
            cmd, shell=True, text=True, capture_output=True
        )
        duration = time.time() - started
        # In-ra console như cũ
        # print(f"\n$ {cmd}")
        # print(result.stdout if result.stdout else result.stderr)

        return {
            "cmd": cmd,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration_sec": round(duration, 4),
            "ok": (result.returncode == 0)
        }
    except Exception as e:
        duration = time.time() - started
        print(f"Error running {cmd}: {e}")
        return {
            "cmd": cmd,
            "returncode": None,
            "stdout": "",
            "stderr": str(e),
            "duration_sec": round(duration, 4),
            "ok": False
        }
