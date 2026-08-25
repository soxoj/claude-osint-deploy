#!/usr/bin/env python3
"""Print everything the stack decision needs, in one call. Stdlib only."""
import json, os, platform, shutil, socket, subprocess, sys

def ver(cmd):
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return {"path": exe, "version": (out.stdout or out.stderr).strip().splitlines()[0][:80]}
    except Exception as e:
        return {"path": exe, "version": f"<error: {e}>"}

def wsl_distros():
    """On a Windows host: which WSL distros exist. Empty list = WSL not usable."""
    if platform.system() != "Windows":
        return None
    try:
        out = subprocess.run(["wsl.exe", "-l", "-q"], capture_output=True, timeout=20)
        text = out.stdout.decode("utf-16-le", "ignore") if b"\x00" in out.stdout[:8] \
            else out.stdout.decode("utf8", "ignore")
        return [d.strip() for d in text.splitlines() if d.strip()]
    except Exception:
        return []


def reachable(host, port=443):
    try:
        socket.create_connection((host, port), timeout=5).close()
        return True
    except OSError:
        return False

info = {
    "os": platform.system(), "release": platform.release(), "arch": platform.machine(),
    "in_wsl": "microsoft" in platform.release().lower(),
    "wsl_distros": wsl_distros(),   # None off-Windows, [] if Windows without WSL
    "python_running": sys.version.split()[0],
    "admin": os.geteuid() == 0 if hasattr(os, "geteuid") else None,
    "path_has_local_bin": any(p.rstrip("/\\").endswith(("local/bin", ".local\\bin"))
                              for p in os.environ.get("PATH", "").split(os.pathsep)),
    "tools": {n: ver(c) for n, c in {
        "uv": ["uv", "--version"], "pipx": ["pipx", "--version"], "pip": ["pip", "--version"],
        "python3": ["python3", "-V"], "py": ["py", "-V"], "docker": ["docker", "--version"],
        "git": ["git", "--version"], "go": ["go", "version"], "node": ["node", "-v"],
        "npm": ["npm", "-v"], "cargo": ["cargo", "-V"], "brew": ["brew", "-v"],
        "gh": ["gh", "--version"],
    }.items()},
    "net": {h: reachable(h) for h in ("github.com", "pypi.org", "registry.npmjs.org")},
    "docker_usable": subprocess.run(["docker", "info"], capture_output=True).returncode == 0
                     if shutil.which("docker") else False,
    "free_gb": round(shutil.disk_usage(os.path.expanduser("~")).free / 2**30, 1),
}
print(json.dumps(info, indent=2))
