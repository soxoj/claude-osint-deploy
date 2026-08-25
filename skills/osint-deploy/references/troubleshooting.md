# Troubleshooting ladder

Work top to bottom. Stop at the first fix. Never skip to the bottom, and never "fix" by disabling checks.

| Symptom | Cause | Fix |
|---|---|---|
| `error: externally-managed-environment` | PEP 668, system Python | `uv tool install` / venv. **Not** `--break-system-packages` |
| `requires-python` / `Requires-Python` conflict | host interpreter too new or too old | `uv tool install --python 3.11 <pkg>` — uv downloads it |
| Builds a C extension and fails | missing headers/compiler | Linux: `-dev` package from CI; macOS: `xcode-select --install`; Windows: **switch to Docker** |
| `ModuleNotFoundError` after a green install | wrong interpreter on PATH, or package name ≠ import name | `command -v <tool>`, `head -1 $(command -v <tool>)` |
| Tests fail on version/CLI assertions | a globally installed copy shadows the checkout | put the venv first: `PATH=$PWD/.venv/bin:$PATH pytest` |
| `docker run <img> <args>` → "unrecognized arguments" | image ENTRYPOINT is not the CLI you want | `docker inspect <img> --format '{{json .Config.Entrypoint}}'`, then `--entrypoint <bin>` |
| Exit 0, zero or all-identical results | swallowed exceptions, or a bad flag you added | re-run the README command **verbatim**; then bisect your flags |
| 401/403 on many sources | API keys | list the keyless sources, report the rest as `NEEDS_KEY` |
| 429 / captcha everywhere | rate limits | one small query, back off, `NET` not `FAIL` |
| `No module named X` running the README's `python3 -m X` | `uv tool install` isolates the venv | use the console script, or `~/.local/share/uv/tools/X/bin/python -m X` |
| Container healthy but `localhost:PORT` refuses | port published on a non-loopback interface | `docker port <cid> <port>/tcp` and use that address; never hardcode localhost |
| `docker run img --help` prints Python's/Node's help | ENTRYPOINT is the interpreter | pass the script as CMD (`docker run img sf.py -h`) or `--entrypoint` |
| Third-party image crashes on import | unofficial tag is years stale | repo's own image → repo's Dockerfile → your own 5-line image on a current base |
| `CloseEvent is not defined` / `WebSocket is not available` | Node too old for the package | bump the base image (node:24-slim worked where node:22-slim did not) |
| Browser download 403 / "All providers failed" | egress blocks Chrome-for-Testing | install the distro browser in an image and pass `--browser-executable-path` |
| `pytest: command not found` after `uv sync` | test deps sit in a `[dependency-groups]` | `uv sync --all-groups`, then `ls .venv/bin/pytest` before T1 |
| `--help` crashes but the tool runs | broken argparse usage string (e.g. ASCII-art metavars) | smoke-test with a minimal real invocation, not `--help` |
| `AttributeError: 'X509' object has no attribute ...` / `ImportError: cannot import name` on first use | unpinned `>=` dep pulled a breaking newer major | pin below the break (`pyOpenSSL==24.0.0`, `cmd2<3`) — root-cause, don't patch the tool |
| C-extension dep fails to **compile** (`cchardet`, `_cchardet.cpp` error) | no wheel for the host Python version | pin the interpreter to the newest Python the dep ships a wheel for (`--python 3.10`); check PyPI's wheel list |
| `ModuleNotFoundError: No module named 'pkg_resources'` | setuptools 81+ removed it, tool assumes it | inject a compatible one: `--with 'setuptools<81'` |
| Containerised tool: `Permission denied` writing to a mounted dir | image runs as root, mount owned by host UID | run with `--user $(id -u):$(id -g)` |
| Tool hangs/errors trying to reach a database | hard MySQL/DB dependency with no fallback | look for a `-n`/`--no-db`/offline flag before provisioning the service |
| `bad interpreter: .../python: No such file or directory` | the install prefix moved; venv scripts keep absolute shebangs, and `uv sync` will **not** repair them | `rm -rf .venv && uv sync --all-groups`, then re-run the manifest |
| Installed in PowerShell, `command not found` in WSL (or the reverse) | two separate machines share one drive letter | install and verify in **one** host; record it as `host` in the recipe |
| Linux tool crawls or hits permission errors on Windows files | working over `/mnt/c` | keep the work inside the distro, copy results out at the end |
| Works on Linux, not Windows | `fcntl`, `libpcap`, path length, no `python3` alias | WSL2 or Docker; `py -3.11` on native Windows |
| Slow/hanging with no output | tool waits on DNS/Tor/proxy | check whether it wants Tor; add a timeout to the check |
| Tool reprints its `--help`/usage and exits 0 on a real invocation | a required arg is missing — often an API key or `-k` | supply it (or read the current README's examples); a keyed data source = NEEDS_KEY, not FAIL |
| Archived bash scraper produces only its banner | the scraped site added Cloudflare/anti-bot since | `curl` the endpoint it scrapes; a "Just a moment..." page = UPSTREAM (dead), not a broken install |
| System dep missing and no sudo | can't `apt install` | pure-interpreter deps (exiftool=Perl) → drop into `~/.local/bin`; compiled deps (jq/nmap/whois) → use the tool's Docker image |
| Tool mis-parses args / "no target specified" only under Docker | you set `-e TERM` and it now assumes an interactive TTY | drop `-e TERM`; a `tput`/`No value for $TERM` warning printed *after* the results is cosmetic |
| Go tool, no release binary, no host Go | nothing to install | build in `golang:<v>` container (`--user $(id -u):$(id -g)`, `GOCACHE`/`GOPATH` in /tmp), run the linux binary |
| `TypeError: 'type' object is not subscriptable` at import | pinned interpreter too **old** for a dep using `list[...]`/PEP585 (needs py3.9+) | bump the interpreter/base image *up*, not down |
| `TypeError: __init__() got an unexpected keyword argument` on first use | repo pins a dep version incompatible with its own code, and no version fixes both | last resort: 1-line source patch dropping the arg + a modern dep; record it in `patches[]` |
| Old `requirements.txt` fails to build (Cython/wheel errors) on a current Python | 2018-era `==` pins fossilised | install the same libs **unpinned**; also add any modules the code imports but the file omits |
| Interactive menu tool: EOF/`EOFError` or nonzero exit when scripted | it reads `input()`, not argv | feed the menu sequence on stdin; assert on output regex, set `expect_exit` to the EOF code |
| Live feed connects but delivers 0 events, no error | the public server is up but the feed is deprecated | UPSTREAM (dead source); self-host the feed server — not a broken install |
| `go.mod requires go >= X (running go Y; GOTOOLCHAIN=local)` | the `golang:` build image is older than the repo's `go.mod` | use a `golang:<v>` tag that meets the `go`/`toolchain` line, or drop `GOTOOLCHAIN=local` to let it fetch |
| Repo "has releases" but nothing runs on Linux | the only assets are `.exe`/wrong-arch | check asset names for `Linux`/`linux_amd64`; if none, build from source in a `golang:`/build container |
| `WARNING: DNS features are limited due to lack of DNSPython` (or similar "limited/degraded" notice) | an optional extra isn't installed | add it (`--with dnspython`, the `[full]` extra); `expect_absent` the warning so a half-install can't pass |
| Source is full of token/api-key logic | reads like AUTH_REQUIRED | run the README example keyless first — many tools have a working free tier; only classify NEEDS_KEY if it actually refuses |
| Installed but the documented console name isn't on PATH | entry point installed under a different name (e.g. `<tool>_cli.py`) | `ls .venv/bin` / `~/.local/bin` for the real script name before calling it broken |
| Live check flaps: some queries return "too many requests" | per-source/per-platform rate limiting | narrow to the reliable sources and set `net_if_matches` on the throttle wording so a rate-limited run is NET, not FAIL |
| `File not found: requirements.txt` | it's a `pyproject.toml`/`setup.py` package, not a script | `uv pip install .` inside a venv (or `uv tool install <dir>`); entry point lands in `.venv/bin` |
| `FileNotFoundError: .../data/*.json` on first real run | tool downloads its dataset on run; you passed `--no-update`/offline | run it plain once to let it fetch, then use the offline flag |
| One async module aborts the whole run with a traceback | that site's API changed (module rot) while others work | classify the module UPSTREAM; only a source patch (try/except) salvages the run — don't claim a clean pass |

## Check the tracker before you invent a fix

When an error is confusing and smells like a known bug, someone probably hit it already. Look before
you patch:

```
gh issue list -R <owner/repo> --state all --search "<error phrase>"
gh pr list    -R <owner/repo> --state all --search "<error phrase>"   # merged + open
gh api repos/<owner/repo>/forks --jq '.[] | select(.pushed_at > .parent.pushed_at) | .full_name'  # forks ahead of upstream
```

- **Merged PR** → the fix may be newer than the last release; install from the repo HEAD or the tag
  that includes it.
- **Open PR / active fork with the fix** → install from that ref
  (`uv tool install git+<url>@<branch>`, `pip install git+<url>@<sha>`) and record the ref in the
  recipe — don't hand-copy the diff.
- **Closed `WONTFIX` / long-stale issue** → it's genuinely **UPSTREAM**; report it, don't burn time
  fighting it.
- A fork that is many commits ahead and recently pushed is often the maintained continuation of an
  abandoned tool — worth deploying instead of the dead original.

## When a fix requires editing the tool

Allowed, but: pin the change in the recipe (`"patches": [...]`), prefer a version pin over a source
edit, and say so in the report. Upstream bugs (holehe's `-T`) go in the report as **UPSTREAM**, not
silently patched.
