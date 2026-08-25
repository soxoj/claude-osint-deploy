# Stack selection & per-OS notes

## Decision table

| Repo signal | Stack | Command |
|---|---|---|
| Has release assets for your OS/arch (Go/Rust) | prebuilt binary | download, `chmod +x`, drop in `~/osint_tools/bin` |
| Official image on ghcr/docker hub | docker | `docker run --rm <img> <args>` — `recon.py` probes both registries for you |
| `Dockerfile` only | docker build | `docker build -t osint/<tool> .` |
| `pyproject.toml` with `[project.scripts]`, on PyPI | uv tool | `uv tool install [--python X.Y] <pkg>` |
| Python CLI, not on PyPI | uv tool from git | `uv tool install [--python X.Y] git+<url>` |
| Python, library or messy layout | venv | `uv venv --python X.Y ~/osint_tools/<tool>/.venv && uv pip install -r requirements.txt` |
| `package.json` with `bin` | npx | `npx -y <pkg> <args>` |
| `go.mod`, Go installed | go install | `go install <mod>/cmd/<tool>@latest` |
| `go.mod`, no Go | binary or docker | — |

Ranking rationale: fewer moving parts first. A binary can't have a dependency conflict; Docker
can't be broken by the host interpreter; `uv` can't pollute the system Python.

## Python version pinning — the single biggest win

Most OSINT repos are pinned to an interpreter 1–3 years old. Do **not** force them onto the host
interpreter. `uv` downloads the right one on demand:

```
uv tool install --python 3.11 holehe
uv venv --python 3.10 && uv pip install -r requirements.txt
uv run --python 3.11 python -m tool
```

Signals to read: `requires-python`, `python_requires`, the `matrix.python-version` in CI,
classifiers in `setup.py`. When CI tests 3.9–3.12, pick the **highest tested**, not the newest existing.

## Docker: when to jump straight there

- Host interpreter/toolchain can't be satisfied (no uv, locked-down machine).
- Native deps: chromium/playwright, libpcap, nmap, tor, ImageMagick.
- Repo abandoned >2 years and pins ancient transitive deps.
- Windows host and the repo only tests Linux.

Mount for output, keep the network explicit:
```
docker run --rm -v "$PWD/out:/out" <img> <args> -o /out/result.json
```
Wrap it so the user's run command is identical to the native one:
`~/osint_tools/bin/<tool>` → one-line shell/`.cmd` script that calls docker.

## Per-OS

**Linux** — package manager for system libs (`apt-get install -y libpcap-dev`). Never `sudo pip`;
PEP 668 will (correctly) block you. Prefer `uv`.

**macOS** — Homebrew for system libs and for Go/Node. Apple Silicon: check the release asset is
`darwin_arm64`, otherwise use `--platform linux/amd64` under Docker or Rosetta. Xcode CLT
(`xcode-select --install`) is needed for any package building C extensions.

**Windows** — choose the *host* before the stack: **WSL2 > Docker Desktop > native**.

```
wsl -l -q                      # distros present? (env_probe reports this as wsl_distros)
wsl --install -d Ubuntu        # ~1 command, needs a reboot on first install — ask before running
wsl -d Ubuntu -- bash -lc 'curl -LsSf https://astral.sh/uv/install.sh | sh'
wsl -d Ubuntu -- bash -lc 'uv tool install <pkg>'
wsl -d Ubuntu -- bash -lc '<tool> --help'          # T0 runs in the same host you installed into
```

Why WSL first: nearly every OSINT repo's CI is `ubuntu-latest` only, so WSL is the environment the
maintainers actually test. It costs no image build and keeps native speed.

- Verify in the host you installed into. A `--help` that passes in PowerShell proves nothing about
  the WSL copy, and vice versa.
- Write the recipe's `run` field in the same form the user will type
  (`wsl -d Ubuntu -- <tool> <args>`), and record `"host": "wsl:Ubuntu"`.
- Paths: `/mnt/c/Users/<you>/...` from inside, `\\wsl$\Ubuntu\home\<you>\...` from Windows. Keep the
  work inside the distro and copy results out — running a Linux tool over `/mnt/c` is slow and hits
  permission oddities.
- Docker Desktop on Windows runs on the WSL2 backend anyway; if you need an image, you already have
  the machinery.
- Native Windows only when CI has a `windows-latest` job. Gotchas: no `libpcap`, no `fcntl`, path
  length limit, `py -3.11` instead of `python3`, MSVC Build Tools for C extensions. `uv tool` scripts
  land in `%USERPROFILE%\.local\bin` — add it to PATH.

## Bootstrap (nothing installed)

- `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh` (Linux/macOS),
  `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows). Installs its own Python —
  no system Python needed.
- Docker: Docker Desktop (macOS/Windows), distro package (Linux).
- Ask before installing anything system-wide with `sudo`.
