---
name: osint-deploy
description: Install, run and verify an OSINT tool from GitHub on macOS, Windows or Linux. First classifies what the repo actually is (CLI / server / desktop app / browser extension / not-a-tool), picks the deployment stack (prebuilt binary / Docker / uv / pipx / venv / npm / go), installs it isolated, then proves it works with the repo's own unit tests plus the example commands from its README. Use when the user asks to install, deploy, set up, run, fix or verify any OSINT / recon / scraping tool from a GitHub repo (sherlock, holehe, theHarvester, maigret, subfinder, amass, phoneinfoga, spiderfoot, ...), or says "install this repo", "make this tool work", "why does this tool fail".
---

# OSINT tool deploy & verify

Goal: the tool is **installed, isolated, and proven to run** on this machine — not "the install command exited 0".

Non-negotiable: **never report success without Phase 5 evidence.** OSINT tools rot fast (dead APIs,
stale pins, abandoned repos). A green `pip install` means nothing.

## Scope

Deploy/verify tooling only. Run tools against targets the user is authorised to investigate,
use documented example targets for verification, keep verification to a single low-volume request,
and honour each tool's rate limits and the target's ToS. Report which sources need API keys instead
of hunting for ways around them.

---

## Phase 0 — Environment (once per machine)

```
python3 scripts/env_probe.py       # or: py scripts/env_probe.py  on Windows
```

Cache the output in the conversation; it decides everything below. If `python3` itself is missing,
read `references/stacks.md` § Bootstrap.

## Phase 1 — Recon the repo (never guess)

One command clones the repo and prints every fact below:

```
python3 scripts/recon.py <owner/repo>        # clones into ~/osint_tools/src/<repo>
```

It reports stars/last-commit/archived, entry points, manifest files, the CI matrix **and CI's own test
commands**, `requires-python`/`go`/node engines, system packages, API keys named in the README,
release assets, Docker files, test dirs, and the README's example invocations. Read the CI section
first. Fall back to reading by hand only for what it flags as missing:

| Read | What you get |
|---|---|
| `.github/workflows/*.yml` | **The ground truth**: supported OS matrix, Python/Go/Node versions, system packages, the *exact* test command. Read this before anything else. |
| `README*` | Install commands, **example invocations with expected output** (Phase 5 T2 material), required API keys |
| `pyproject.toml` / `setup.py` / `requirements*.txt` | `requires-python`, deps, entry points |
| `go.mod` / `package.json` / `Cargo.toml` | Toolchain version |
| `Dockerfile`, `docker-compose.yml` | An official, pre-solved dependency set |
| Releases / tags via `gh release list` or the API | Prebuilt binaries → zero toolchain |
| Last commit date, open issues | Abandoned repo? Expect stale pins; jump to a pinned interpreter or Docker early |

Check `references/known-tools.md` first — if the tool is listed, its stack and gotchas are known.

### Phase 1.5 — Classify the repo before deploying it

Popularity on the `osint` topic does not mean "installable CLI". Of the current top 10 by stars,
**four** are CLIs. Decide the class first, because it changes both the install and the verification:

| Class | Signal | Deploy | Verify |
|---|---|---|---|
| **CLI tool** | `[project.scripts]`, `bin` in package.json, console entry point | the Phase 2 ladder | T0/T1/T2 as written |
| **Server / web app** | `EXPOSE`, `docker-compose.yml`, `server.js`, a `-l host:port` flag | container, published port | start → `docker port` → poll readiness → **one API call** → stop |
| **Desktop app** | Tauri/Electron, `.dmg`/`.msi`/`.AppImage` release assets | release artifact per OS | artifact downloads + launches; prefer its CLI sibling if one is published |
| **Browser extension** | `manifest.json`, store links in README | not installable headlessly | **find the CLI package** — it is usually a different repo/package |
| **Not a tool** | no build manifest at all: awesome-list, docs, skills collection | nothing to deploy | say so and stop — do not invent an install |

`scripts/recon.py` prints `entry_points`, `manifest_files` and flags the last class outright.

**The starred repo is often not the installable artifact.** `gildas-lormeau/SingleFile` is the browser
extension; the CLI is `single-file-cli` on npm. `koala73/worldmonitor` is a desktop app; the CLI is
`npx worldmonitor`. Check npm/PyPI for a `-cli` sibling before concluding a repo cannot be run.

## Phase 2 — Pick the stack

**On Windows, pick the execution host first — it is a separate decision from the stack.**
`env_probe.py` reports `wsl_distros`: `None` off-Windows, `[]` on Windows without WSL, otherwise the
distro names.

| Host | When | Cost |
|---|---|---|
| **WSL2** (`wsl -d <distro> -- <cmd>`) | default on Windows whenever a distro exists — most OSINT repos only test `ubuntu-latest` | native speed, real Linux paths, no image build |
| **Docker Desktop** | no WSL distro, or the repo needs a pinned system image | image pull/build, volume mounts |
| **native Windows** | only when the repo's CI actually has a `windows-latest` job | `fcntl`, `libpcap`, path limits, MSVC toolchain |

If CI has no `windows-latest` job, do not fight native Windows — say so in one line and use WSL.
Install *inside* the chosen host: `wsl -d Ubuntu -- bash -lc 'uv tool install <pkg>'`, and write the
run command in the same form so the user's invocation matches what you verified. Files cross at
`\\wsl$\<distro>\home\...` from Windows and `/mnt/c/...` from Linux; prefer keeping work inside the
distro and copying results out.

Then take the **first** option that satisfies the repo's constraints (laziest wins):

1. **Prebuilt release binary** (Go/Rust tools) — no toolchain, works on all three OSes.
2. **Official Docker image** — `recon.py` probes Docker Hub and ghcr for one instead of keeping a
   stored list; a published image saves the build entirely (theHarvester ships one on ghcr). Falls back to the repo's `Dockerfile` — when deps are heavy/native (chromium,
   libpcap, tor), when the repo is abandoned, or when the host interpreter is incompatible.
3. **Python** → `uv tool install` (isolated, and can fetch the *right* interpreter:
   `uv tool install --python 3.11 <pkg>`) → `pipx` → `uv venv`/`python -m venv` + pip.
   **Never** `pip install` into the system interpreter, never `sudo pip`.
4. **Node** → `npx <pkg>` for one-shot, `npm i -g` only if the user wants it on PATH.
5. **Go** → `go install ...@latest` if Go is present, otherwise back to 1 or 2.

Decision details, per-OS quirks and the bootstrap path: `references/stacks.md`.

Announce the choice in one line with the reason ("py3.14 host vs `requires-python <3.13` → uv with
pinned 3.11") before installing.

## Phase 3 — Constraints before install

- **Interpreter/toolchain version** — compare `requires-python` / `go.mod` against Phase 0. Mismatch is
  the #1 cause of failure; solve it with a pinned interpreter or Docker, not with `--ignore-requires-python`.
- **System packages** — take them from the CI workflow, not from guesswork (`libpcap-dev`, `libmagic`,
  `chromium`, `tor`). On macOS: brew; Windows: prefer Docker/WSL over native builds.
- **API keys** — list which modules are inert without them. Do not treat a keyless module as broken.
- **Network egress** — some tools need Tor or unrestricted egress; note it, don't fight it.

## Phase 4 — Install, isolated and reproducible

- Install prefix: `~/osint_tools/<tool>` (venv, binary, or docker tag). Never touch system site-packages.
- Log **every** command you actually ran — Phase 6 writes them into the recipe verbatim.
- On failure: read the real error, fix the *cause* (wrong interpreter, missing system lib, bad pin),
  and re-run. Never mask it with `--break-system-packages` or by dropping deps.
  Escalation ladder in `references/troubleshooting.md`.
- **Before inventing a fix for a confusing error, check whether someone already dealt with it.** Search
  the repo's Issues and PRs for the error text (`gh issue list -R <repo> --search "<msg>" --state all`,
  `gh pr list -R <repo> --search "<msg>" --state all`). An open/merged PR often carries the exact patch
  or the right dep pin; a `WONTFIX`/stale issue tells you it's genuinely UPSTREAM. If the fix lives only
  in an unmerged PR or an active fork, prefer installing from that ref
  (`uv tool install git+<url>@<branch>` / `pip install git+<url>@<sha>`) over hand-patching, and record
  which ref in the recipe.

## Phase 5 — Verify (this is the deliverable)

Three tiers. Write them into a manifest and run them with the bundled runner:

```
python3 scripts/verify.py checks.json          # add --skip-network for offline/CI
```

| Tier | What | Pass criteria |
|---|---|---|
| **T0 smoke** | `<tool> --help`, `--version` | exit 0, banner/usage matches a regex |
| **T1 unit** | The repo's own test command **from its CI workflow** (`pytest -q`, `go test ./...`, `npm test`) | exit 0, or a documented subset passes with the network-dependent failures listed by name |
| **T2 functional** | The example invocations copied out of the README, against the documented example target | exit 0 **and** output matches the shape the README promises (a found profile, N results, valid JSON) |

Rules that keep the verdict honest:

- **Distinguish failure classes.** `installation broken` ≠ `target site changed / rate-limited /
  needs an API key / offline`. Classify every failure; only the first class blocks success.
- Re-run a flaky T2 check once before calling it. Rate-limit and timeout responses are *not* pass.
- Never fake a pass: exit 0 with empty output is a FAIL if the README promises results.
- Keep T2 to one small query per check. No target enumeration, no bulk runs.
- A tool that only ever runs inside Docker gets verified through the same wrapper the user will use.

### Traps this skill exists for — every one hit while deploying the top 10 `topic:osint` repos

- **Run the README command verbatim before adding any flag of your own.** holehe's `-T` takes no
  `type=int`, so `-T 5` makes all 121 modules report `[x] Rate limit` — exit 0, zero real output.
- **Check the Docker ENTRYPOINT.** theHarvester's image entrypoint is the web UI, not the CLI; the
  documented `docker run <img> -d example.com` fails. `docker inspect <img> --format
  '{{json .Config.Entrypoint}}'` before writing the run command.
- **CI green ≠ the documented command works.** theHarvester's docker CI check passes *because* it
  greps for the web-UI help text. Re-derive T2 from the README, never from CI.
- **Put the project venv first on PATH for T1.** sherlock's version test invokes `sherlock` from PATH;
  a globally installed copy makes the checkout's tests fail for no real reason.
- **PyPI ≠ git HEAD.** sherlock is 0.16.0 on PyPI and 0.16.1 in the repo. Say which one you installed.
- **A "no tests" repo is not exempt from T1.** Replace it with something real — import every plugin
  module and assert the count (`holehe`: 144 modules), or run the tool's own self-check.
- **`python3 -m <pkg>` out of a README fails after `uv tool install`** — the package lives in an
  isolated venv. Use the console script, or that tool's own interpreter
  (`~/.local/share/uv/tools/<pkg>/bin/python -m <pkg>`). Hit on `social-analyzer`.
- **Never assume `localhost` for a container port.** Read the real mapping:
  `docker port <cid> 3000/tcp` — it can bind an interface that is not loopback. Hit on `web-check`.
- **An ENTRYPOINT can be the interpreter, not the tool.** spiderfoot's is `python` with CMD
  `sf.py -l 0.0.0.0:5001`, so `docker run img -h` prints *Python's* help. Pass the script:
  `docker run --rm spiderfoot sf.py -h`.
- **Unofficial Docker images rot silently.** `capsulecode/singlefile` ships Node 20 while the CLI now
  needs ≥22.4 — it crashes on import. Prefer the repo's own image/Dockerfile; otherwise a five-line
  `FROM node:24-slim` + distro browser beats a stale third-party tag (node:22 was already too old).
- **Auth-gated tools stop at T0 and say so.** GHunt needs `ghunt login` with a real Google session;
  report `AUTH_REQUIRED` with the exact command the user must run, never a fake T2 pass.
- **`uv sync` before T1, then check the runner exists.** Test deps can sit in a `[dependency-groups]`
  that a plain sync skips — `uv sync --all-groups`, then `ls .venv/bin/pytest`.
- **`--help` is not a guaranteed smoke test.** onedrive_user_enum's `--help` crashes with an argparse
  `AssertionError` (its ASCII-art usage string breaks the formatter) while the tool runs fine. If T0
  fails only on `--help`, try a minimal real run before concluding the install is broken.
- **Unpinned `requirements.txt` rots against today's transitive deps.** HostHunter pulls the latest
  pyOpenSSL (26.x), which removed `X509.get_extension` — the tool crashes on first use. Fix the *cause*:
  pin the offending dep to a version that still has the API (`pyOpenSSL==24.0.0`), don't edit the tool.
- **A root Docker image + a bind mount = permission failures.** sn0int's image runs as root but writes
  its data dir into a mounted `/data` owned by your host UID → `Permission denied`. Run it as
  `--user $(id -u):$(id -g)`. Check this whenever a containerised tool that mounts a volume can't write.
- **Some tools hard-require a service (DB) you must opt out of.** onedrive_user_enum tries to reach
  MySQL unless given `-n`. Read the args for a `--no-db`/offline switch before provisioning a whole
  service just to smoke-test.
- **The tool can work while every data source is down.** sn0int added/queried/ran modules correctly,
  but crt.sh/OTX/ThreatMiner all returned 429/502/522. That is UPSTREAM — verify the tool's own
  machinery (registry, DB, module execution) separately from any single live source.
- **A C-extension dep with no wheel for the host Python fails to *build*, not to *find*.** buster pulls
  `cchardet`, which has wheels only up to cp310 — on 3.11+ it tries to compile and dies. Don't install
  a compiler; pin the interpreter to the newest Python the dep still ships a wheel for
  (`uv tool install --python 3.10 ...`). Check the wheel list on PyPI, don't guess.
- **`pkg_resources` / setuptools is an implicit dep that modern envs don't provide.** buster imports
  `pkg_resources`; setuptools 81+ removed it. Inject a compatible one: `--with 'setuptools<81'`.
- **An unpinned lower-bound dep (`cmd2>=2.4.3`) silently pulls a breaking major.** emploleaks imports
  `from cmd2 import style, Fg`, gone in cmd2 3.x → 4.x. Pin below the break (`cmd2<3`). Same root cause
  as HostHunter's pyOpenSSL — a `>=` with no ceiling is a time bomb; cap it, don't edit the tool.
- **Layered tools may have a stdlib-only core you can verify without the heavy install.** cti-expert's
  collection layer runs with no deps; its own `scripts/smoke-test.sh` (its CI gate) is the honest T1.
  Look for a low-dependency entrypoint before provisioning pandoc/xelatex/graphviz for the full stack.
- **A tool that reprints its own usage instead of running usually means a *required* arg is missing —
  often an API key.** GooFuzz v2.0 silently prints its help and exits 0 without `-k CX_ID,API_KEY`; that
  is not "ran, found nothing". Also: a tool's data source can migrate from free-scrape to a keyed API
  across a major version (GooFuzz v1 scraped Google, v2 needs a Google CSE key) — read the *current*
  README's examples, not the old blog post. Classify as **NEEDS_KEY**, not FAIL.
- **An archived bash tool that scrapes a website is almost always UPSTREAM-dead.** Namechk (archived
  2021) scrapes a CSRF token from namechk.com, which now returns a Cloudflare "Just a moment..." page,
  so it bails after its banner. The script installs and runs fine — the source is gone. Before blaming
  the install, `curl` the endpoint it scrapes and look for a challenge/redirect.
- **No sudo? Install the portable deps, containerise the rest — never block on `apt`.** exiftool is pure
  Perl: drop the distro tarball into `~/.local/bin` and MetaDetective works. jq/whois/nmap are compiled:
  use the tool's own Docker image (GooFuzz, asn) instead of fighting a rootless build.
- **Setting `TERM` to silence a `tput` warning can *break* a tool.** asn works headless as a plain
  `docker run`; adding `-e TERM=xterm` (to hide a cosmetic `tput: No value for $TERM`) makes it think a
  terminal is attached, enter interactive mode, and mis-parse its args ("no target specified"). If a
  warning prints *after* correct output, it is cosmetic — leave it alone.
- **A Go OSINT tool with no release binary + no host toolchain: build in a throwaway `golang:` image.**
  SatIntel (`go.mod`, no releases) compiles with `docker run --rm -v "$PWD":/src -w /src -e GOCACHE=/tmp/gc
  -e GOPATH=/tmp/gp --user $(id -u):$(id -g) golang:1.22 go build -o <bin> .`; the linux binary then runs
  on the host. Compiling *is* the T1 for a Go tool.
- **Judge an "impossible-claim" tool by its code, not its name.** InstagramPrivSniffer ("view private
  posts anonymously") sounds like a scam; the code is one unauthenticated GET to Instagram's public
  `web_profile_info` endpoint and cannot bypass privacy. Read the fetch/auth path before running it —
  classify **SUSPECT** only if it actually harvests credentials or does something malicious, and never
  run such a tool against a real private target.
- **The pinned interpreter can be too *old*, not just too new.** Raccoon's Dockerfile is
  `FROM python:3.8-alpine`, but its own `fake-useragent` uses `list[...]` generics (PEP 585, needs 3.9+)
  → `TypeError: 'type' object is not subscriptable` at import. All the other interpreter traps here are
  "host too new"; this is the mirror. Bump the base *up* to the lowest version the deps actually support.
- **A repo can pin a dependency version its own code is incompatible with — and no version fixes it.**
  Raccoon calls `UserAgent(verify_ssl=False)`, a kwarg removed in fake-useragent 1.x, yet pins 1.1.3
  (which lacks it); the older 0.1.x has `verify_ssl` but fetches its UA data from a dead Heroku server
  (403). When neither the old nor the new version works, a **documented one-line source patch** (drop the
  kwarg) + modern offline data is the honest fix — record it in the recipe's `patches[]`, don't pretend a
  pin solved it. (gasmask is the gentler cousin: unpinned `censys` pulled 2.x, which dropped
  `censys.certificates` → pin `censys<2`, same family as pyOpenSSL/cmd2.)
- **Interactive menu tools are not arg-driven — smoke them over stdin, and expect a messy exit code.**
  GhostTrack reads `int(input())` for a menu choice, then `input()` for the target; there is no `--help`.
  Verify by piping the sequence (`printf '1\n8.8.8.8\n'`); the menu loop then hits EOF and the process
  exits nonzero even though the output above it is correct. Assert on the **output regex** and set
  `expect_exit` to the observed EOF code, not 0.
- **Ancient pinned requirements that won't build: relax them (and add the imports the file forgot).**
  phishing_catcher's 2018 pins (`PyYAML==5.1`, `python_Levenshtein==0.12.0`, `websocket-client==0.48.0`)
  don't compile on a current Python; installing the same libraries **unpinned** works. It also imports
  `confusables` and `Levenshtein`, which are not even in `requirements.txt`. Loosening pins is as valid a
  fix as tightening them — the direction depends on whether the pin is too new (tighten) or fossilised
  (loosen). Record the deviation.
- **A live-feed tool can reach a server that is up but no longer broadcasting.** phishing_catcher's
  `certstream.calidog.io` returns HTTP 200, the client connects with no error and the tqdm bar appears —
  but the deprecated public firehose emits **0 events**. That is **UPSTREAM** (dead data source), not a
  broken install; the tool works against a self-hosted certstream server. A silent feed with a healthy
  handshake is a source problem, and a bounded run (~20s, 0 events, no traceback) is enough to tell.
- **A `golang:` build image can be too old for the repo's `go.mod`.** gosearch's `go.mod` says
  `go >= 1.25`; `golang:1.22` fails with `go.mod requires go >= 1.25.0 (running go 1.22.12;
  GOTOOLCHAIN=local)` — the pinned image blocks the auto-download. Read the `go`/`toolchain` line in
  `go.mod` and pick a `golang:<v>` tag that meets it (or drop `GOTOOLCHAIN=local` to let it fetch). Same
  "pinned runtime too old" family as Raccoon's python:3.8.
- **A release can exist and still be the wrong OS.** gosearch's only release asset is `gosearch.exe`
  (Windows) — there is no Linux binary, so "has releases" doesn't mean "download and run". Check the
  asset *names* for your platform (`Linux`/`linux_amd64`) before choosing the binary path; if none match,
  fall back to a source build. (phoneinfoga/httpx/leaker did ship `Linux_x86_64`/`linux_amd64` — those
  are the laziest path and beat any container.)
- **A tool that "works" may need an optional extra to work *fully*.** dnstwist runs and resolves without
  its extras, but prints `WARNING: DNS features are limited due to lack of DNSPython` and skips NS/MX.
  `uv tool install dnstwist --with dnspython` silences it and enables full records. When a tool warns
  about a missing optional lib, add it via `--with`/the `[full]` extra rather than accepting the degraded
  mode — and assert `expect_absent` on the warning so a half-installed tool can't pass.
- **Token-handling code is not proof a token is required — try the keyless run first.** chiasmodon's
  source is full of `token`/`__check_token` logic, which reads as AUTH_REQUIRED; but it queries
  chiasmodon.io on a free tier that returns real data with no token (a page cap, not an auth wall).
  Don't classify NEEDS_KEY/AUTH from reading the source — run the documented example keyless and see if it
  produces results. (Also: its console script installs as `chiasmodon_cli.py`, not the `chiasmodon` name
  the README uses — `ls .venv/bin` for the real entry point.)
- **No `requirements.txt` is not "no dependencies" — a `pyproject.toml`/`setup.py` repo installs the
  package itself.** nexfil (src/ layout) and cloud_enum ship only `pyproject.toml`; `pip install -r
  requirements.txt` fails with "File not found". Install the package: `uv pip install .` inside a venv
  (entry points then land in `.venv/bin`), or `uv tool install <dir>`. Check for a build manifest before
  concluding a repo has no deps.
- **A tool that fetches its data file on first run breaks if you pre-emptively pass its offline flag.**
  blackbird auto-downloads the WhatsMyName list (`data/wmn-data.json`) on a normal run; `--no-update`
  skips that and crashes `FileNotFoundError` on a fresh checkout. Run it plain the first time to let it
  populate, and only use the offline/no-update switch once the data exists. Same shape as any
  "download models/signatures on first launch" tool — the first run needs the network.

Manifest format, the server-app and auth-gated patterns, and the failure-class table:
`references/verify.md`. Five manifests in `examples/` cover every shape you will need to write:
`sherlock` (CLI with the repo's own tests), `theharvester` (Docker CLI with an entrypoint override and
a self-diagnosing live check), `web-check` (server), `ghunt` (auth-gated, T0 only), and
`interactive-cli` (menu/prompt tool fed over stdin, with a nonzero EOF exit).

## Phase 6 — Record the recipe

Write `~/osint_tools/recipes/<owner>__<repo>.json`:

```json
{"tool":"sherlock","repo":"https://github.com/sherlock-project/sherlock","stack":"uv-tool",
 "os":"linux","host":"native",   // or "wsl:Ubuntu" / "docker"
 "install":["uv tool install --python 3.12 sherlock-project"],
 "run":"sherlock <username>","checks":"checks.json","verified":"2026-08-24","notes":["..."]}
```

Write the tool's manifest next to it as `~/osint_tools/recipes/<tool>.checks.json` — **not** into the
skill's `examples/`, which ships as part of the plugin and is overwritten on update. Re-verification
and redeploy on another machine then cost one command each. If the tool is in `references/known-tools.md` and reality disagreed, say so in the
report — the table is a starting point, not truth.

## Phase 7 — Report

Five lines, no essay:

```
Tool      sherlock @ <commit>       Stack  uv tool, pinned py3.12
Run       sherlock <username>       Where  ~/.local/bin/sherlock
Verified  T0 pass · T1 12/12 · T2 2/2 (README example)
Blocked   —  (or: 3 sources need API keys: X, Y, Z)
Recipe    ~/osint_tools/recipes/sherlock-project__sherlock.json
```

Then the exact command the user should type next.
