# Known tools

**Verified** rows were deployed and checked end-to-end on 2026-08-24 (Ubuntu 26.04, Python 3.14 host,
uv 0.12, Docker 29, Node 22). Manifests are in `../examples/`. Re-verify anything older than a few
months — OSINT repos rot fast.

## Top 10 of GitHub `topic:osint`, by stars — as deployed

| # | Repo | Class | Stack that worked | Result |
|---|---|---|---|---|
| 1 | `sherlock-project/sherlock` 90k★ | CLI | `uv tool install sherlock-project` | T0 2/2 · T1 14/14 offline · T2 1/1 |
| 2 | `koala73/worldmonitor` 84k★ | desktop app + CLI | `npx -y worldmonitor tools` | T2 1/1 (CLI); desktop = signed release artifacts |
| 3 | `soxoj/maigret` 37k★ | CLI | `uv tool install maigret` | T0 1/1 · T1 447 passed · T2 1/1 |
| 4 | `lissy93/web-check` 34k★ | **server** | `docker run -d -p 3000 lissy93/web-check` | T0 1/1 · T2 1/1 (`/api/headers`) |
| 5 | `mukul975/Anthropic-Cybersecurity-Skills` 31k★ | **not a tool** | — | Claude skills collection; `npx skills add …` |
| 6 | `jivoi/awesome-osint` 28k★ | **not a tool** | — | awesome-list, nothing to install |
| 7 | `qeeqbox/social-analyzer` 24k★ | CLI | `uv tool install social-analyzer` | T0 2/2 · T2 1/1 |
| 8 | `gildas-lormeau/SingleFile` 22k★ | browser extension | CLI is **`single-file-cli` on npm**; self-built image | T0 1/1 · T2 1/1 |
| 9 | `smicallef/spiderfoot` 21k★ | server + CLI | `docker build -t spiderfoot .` | T0 2/2 · T2 1/1 (passive DNS scan) |
| 10 | `mxrch/GHunt` 19k★ | CLI, auth-gated | `uv tool install ghunt` | T0 2/2 · T2 **AUTH_REQUIRED** (`ghunt login`) |

Also verified outside the top 10: `laramies/theHarvester` (docker, T1 1842 passed),
`megadose/holehe` (uv tool), `projectdiscovery/subfinder` (release binary).

**Four of ten are plain CLIs.** Run the Phase 1.5 classification before promising an install.

## Per-tool gotchas found in practice

| Tool | Gotcha |
|---|---|
| sherlock | PyPI 0.16.0 lags git main 0.16.1 — the version test fails when the global binary shadows the checkout. Offline suite: `pytest -m "not online"` (14). Verify with `--site GitHub`, never the 400-site sweep. |
| maigret | `uv tool install maigret` on a 3.14 host works; tests want a venv (`uv venv --python 3.12` + `pytest-asyncio pytest-rerunfailures pytest-httpserver`). `libcairo2-dev` only matters for PDF reports. |
| web-check | Server, no CLI. `-p 3000:3000` may bind a **non-loopback** interface — read `docker port <cid> 3000/tcp`. `/api/*` endpoints are the verifiable surface. |
| social-analyzer | README's `python3 -m social-analyzer` fails after `uv tool install` (isolated venv). Use the `social-analyzer` console script. Node 20+ needed for the screenshot/UI features only. |
| SingleFile | The starred repo is the browser extension. CLI = `single-file-cli` on npm, and it needs a Chromium binary. Chrome-for-Testing download can be blocked (403); `capsulecode/singlefile` is stale (Node 20 vs required ≥22.4). Working recipe: `FROM node:24-slim` + `apt-get install chromium` + `npm i -g single-file-cli`. **node:22-slim fails with `CloseEvent is not defined`.** |
| spiderfoot | ENTRYPOINT is `python`, CMD is `sf.py -l 0.0.0.0:5001` → `docker run img -h` prints *Python's* help. Use `docker run --rm spiderfoot sf.py -h`. Repo pins Python 3.7–3.10, so Docker is the only sane host-independent path. Needs Chrome for some modules. |
| GHunt | Requires `ghunt login` with a real Google session. Without it, `ghunt email …` exits 1 with a clean `GHuntInvalidSession`. Report AUTH_REQUIRED; there is no honest T2 without credentials. |
| worldmonitor | Tauri desktop app with 38 CI workflows and 100+ optional API keys. The runnable-anywhere surface is `npx worldmonitor tools` (MCP tool list, no key). |
| holehe | No tests, no CI, unmaintained since 2024. `-T/--timeout` is broken (no `type=int`) — passing it makes **all 121 modules report `[x] Rate limit`** at exit 0. 17 hits on `test@gmail.com` is healthy; 100% `[x]` means broken. |
| theHarvester | Image ENTRYPOINT is `harvestview` (web UI), not the CLI — `--entrypoint theHarvester` is mandatory. Repo CI greps for `harvestview`, so CI is green while the documented command fails. Needs Python ≥3.14; `uv sync --all-groups` for test deps. `-b crtsh,certspotter` intermittently returns 0 hosts — retry with a delay before calling it broken. |
| subfinder | Release binary, no Go toolchain. Keyless run gives ~24 subdomains for `hackerone.com`; more sources need `~/.config/subfinder/provider-config.yaml`. Binaries skip T1 by nature. |

## Pattern by repo age

- Active CI matrix incl. current Python → install natively, host interpreter is fine.
- Last commit 1–3 years, no CI → `uv tool install --python <highest version in its classifiers>`.
- Abandoned >3 years, native deps → Docker, and expect some modules to be upstream-dead.


## Also verified (deeper into `topic:osint`, 2026-08-24)

| # | Tool | Stack | Result / gotcha |
|---|---|---|---|
| 27 | `shmilylty/OneForAll` | docker (official image) | subdomains; ENTRYPOINT `python oneforall.py`, results in mounted `/OneForAll/results` |
| 50 | `megadose/toutatis` | uv tool | installs & runs; **AUTH_REQUIRED** — needs your Instagram `sessionid` |
| 81 | `kpcyrd/sn0int` | docker (official ghcr) | **must run `--user $(id -u):$(id -g)`** with bind mounts or it can't write `/data`; public source modules were rate-limited (UPSTREAM) |
| 154 | `SpiderLabs/HostHunter` | uv-venv | crashes until `pyOpenSSL==24.0.0` pinned (26.x dropped `X509.get_extension`); output at `<-o>.vhosts.csv` |
| 215 | `nyxgeek/onedrive_user_enum` | uv-venv | needs `-n` (else MySQL); `--help` itself crashes though the tool works |

Recipes and manifests for these live in `~/osint_tools/recipes/`.

## Random sample deeper in the tail (2026-08-24)

Ten picked across ranks 63–282. **3 were not installable tools** (correctly classified, not deployed):
`K2SOsint/Legendary_OSINT` and `Paper-Pen/GatherInfo` are awesome-lists; `momenbasel/keyFinder` is a
browser extension with no CLI. The other 7 all deployed:

| # | Tool | Stack | Fix that made it work |
|---|---|---|---|
| 63 | `kaifcodec/user-scanner` | uv tool | none — clean |
| 88 | `evilsocket/xray` | docker (built) | no Go toolchain → build the Dockerfile; usage exits 1 by design |
| 136 | `sham00n/buster` | uv tool | **triple**: python 3.10 (cchardet wheel) + `setuptools<81` (pkg_resources) |
| 161 | `devxprite/infoooze` | npx | none — clean |
| 209 | `infobyte/emploleaks` | uv-venv | `cmd2<3` (style/Fg removed in 4.x) |
| 258 | `itsmehacker/CardPwn` | uv-venv | none; interactive, needs a full card number |
| 282 | `7onez/cti-expert` | stdlib | none — its own `scripts/smoke-test.sh` is the T1 gate |

Takeaway: in the long tail, the blocker is almost always a stale/unpinned Python dependency, and the
fix is a pin (interpreter or package), never editing the tool.

## Random sample, second draw (ranks 30–300, 2026-08-24)

Ten more, picked across ranks 30/45/70/99/120/175/190/230/260/300. **2 were not installable tools**
(`may215/awesome-termux-hacking`, `redhuntlabs/Awesome-Asset-Discovery` — awesome-lists). Of the other
8, two are not plain CLIs and were classified, not "installed": `idefasoft/Emora-Project` (rank 230) is
a **Windows-only .NET GUI** — its only release asset is `Emora.exe` (verified a valid `MZ`/.NET PE, but
no headless run on Linux); `yogeshojha/rengine` (rank 30) is a **7-container server platform**
(db/redis/celery/celery-beat/web/proxy/ollama) — recipe recorded, full bring-up is out of scope for a
bounded sample verify. The six real CLIs:

| # | Tool | Stack | Result / gotcha |
|---|---|---|---|
| 99 | `nitefood/asn` | docker (built) | T0+T2 pass (AS13335 lookup). **Do not set `-e TERM`** — with TERM + no TTY it enters interactive mode and mis-parses args. Reputation feed = NEEDS_KEY (harmless `jq: parse error`) |
| 120 | `m3n0sd0n4ld/GooFuzz` | docker (repo image; needs jq) | T0 pass. **NEEDS_KEY** — v2.0 moved from scraping Google to the Google CSE API; requires `-k CX_ID,API_KEY`, else it silently reprints usage |
| 175 | `obitouka/InstagramPrivSniffer` | uv-venv | T0+T2 pass (public `nasa`). **Security-vetted benign** — clickbait name; one unauth GET to IG's public `web_profile_info`, cannot bypass privacy |
| 190 | `ANG13T/SatIntel` | go build in golang container | Compiles + launches (T0). **AUTH_REQUIRED** — interactive TUI prompting for Space-Track + N2YO creds |
| 260 | `GONZOsint/Namechk` | bash (archived 2021) | Script runs (T0). **UPSTREAM** — scrapes namechk.com, which now serves a Cloudflare challenge; bails after the banner |
| 300 | `franckferman/MetaDetective` | uv-tool + exiftool | T0+T2 pass (metadata extraction). Hard dep on **exiftool** (installed no-root as pure Perl into `~/.local/bin`) |

Takeaway: as the sample widens, "not a plain CLI" grows — a `.exe`-only C# repo is a desktop app, a
db/redis/celery `docker-compose` is a platform. And the T2 blocker shifts from stale deps to **access**:
a keyed API (GooFuzz), account auth (SatIntel), or a source that went behind Cloudflare (Namechk).

## Random sample, third draw (ranks 15–240, 2026-08-24)

Ten more, ranks 15/22/38/55/77/105/130/170/200/240. **2 not tools** (`danieldurnea/FBI-tools` = link
collection, `n0kovo/n0kovo_subdomains` = a 3M-line wordlist). The other 8 deployed — 7 CLIs + 1 server:

| # | Tool | Stack | Result / gotcha |
|---|---|---|---|
| 15 | `HunxByts/GhostTrack` | uv-venv | T0+T2 pass (IP geo on 8.8.8.8). **Interactive menu** (no argv) — feed stdin; EOF exit is nonzero but output is correct |
| 22 | `calesthio/Crucix` | docker (server) | T2 pass — `/api/health` 200. Node dashboard on :3117, runs keyless. **Non-loopback port** again — read `docker port`, not localhost |
| 38 | `michenriksen/gitrob` | release binary (Go) | T0 pass. Archived 2018 but its prebuilt linux binary still runs. **AUTH_REQUIRED** (GitHub token) |
| 55 | `evyatarmeged/Raccoon` | docker (py3.9 base + 1-line patch) | T0+T2 pass. **Base py3.8 too old** for its own fake-useragent; and it passes a `verify_ssl` kwarg no working fake-useragent version has → patch |
| 105 | `x0rz/phishing_catcher` | uv-venv (relaxed deps) | Connects to CT feed (T0/T2 handshake). **UPSTREAM** — public calidog firehose is up (200) but emits 0 events; self-host certstream |
| 130 | `twelvesec/gasmask` | uv-venv (censys<2) | T0+T2 pass (example.com DNS/whois). py3-compatible despite the `python` shebang; pin `censys<2` |
| 170 | `JackJuly/linkook` | uv-tool (PyPI) | T0+T2 pass — found Linktree/GitHub/Dev.to profiles. Clean; T2 scans many sites, needs a long timeout |
| 240 | `novitae/sterraxcyl` | uv-tool | T0 pass. **AUTH_REQUIRED** (IG session). setup.py lists stdlib (`argparse`,`datetime`) as deps — harmless smell |

Takeaway: the dependency-rot family got richer — the pinned interpreter can be too **old** (Raccoon on
3.8), a repo can pin a dep its **own code** can't use (Raccoon's fake-useragent), and the fix is
sometimes to **loosen** fossilised pins, not tighten them (phishing_catcher). And "connects" ≠ "works":
a live feed can hand you a clean handshake and zero data (UPSTREAM).

## Random sample, fourth draw (ranks 11–275, 2026-08-25)

Ten more, ranks 11/26/41/60/103/110/160/195/235/275. **Cleanest draw yet: 10/10 were installable
tools, 9/10 genuinely work keyless** (uDork works offline; its live mode is UPSTREAM). Four Go CLIs, six
Python/bash.

| # | Tool | Stack | Result / gotcha |
|---|---|---|---|
| 11 | `sundowndev/phoneinfoga` | release binary (Go) | T0+T1 pass. `Linux_x86_64` release tarball; the offline `local` scanner (libphonenumber) needs no key or network — deterministic T1. numverify/ovh scanners = NEEDS_KEY only |
| 26 | `projectdiscovery/httpx` | release binary (Go) | T0+T2 pass (probe example.com → `200 Example Domain`). The Go HTTP prober, **not** the python `httpx` lib. `-version` on stderr; `-no-color` keeps assertions clean |
| 41 | `elceef/dnstwist` | uv tool | T0+T2 pass (typo-squat resolution). Bare install warns `DNS features are limited` and skips NS/MX — `--with dnspython` fixes it. Permutation offline, `--registered` resolves |
| 60 | `ibnaleem/gosearch` | go build in container | T0+T2 pass (305-site username sweep). **No Linux release** (`.exe` only) → build from source; **`go.mod` needs go≥1.25** so `golang:1.22` fails, use `golang:1.25`. Keyless (HudsonRock/ProxyNova) |
| 103 | `iojw/socialscan` | uv tool | T0+T2 pass (username/email availability). Async, keyless; GitHub/Instagram/Reddit **throttle fast** — narrow to tumblr/gitlab/twitter and `net_if_matches` the "too many requests" wording |
| 110 | `josh0xA/darkdump` | uv-venv | T0+T2 pass (Ahmia `.onion` search). Searches **ahmia.fi clearnet** keyless — no Tor needed; `-p/--proxy` + a Tor SOCKS proxy only to visit the onions. Cosmetic banner SyntaxWarning |
| 160 | `AlephNullSK/dnsgen` | uv tool | T0+T2 pass. **Pure offline** permutation (~167 subdomains of example.com); network:false, fully deterministic |
| 195 | `m3n0sd0n4ld/uDork` | bash | T0+T1 pass (offline `-l` dork listing). Only dep is `curl`; live Google dorking (`-g`/`-e`) hangs on a consent/captcha page → **UPSTREAM**, not a broken install |
| 235 | `chiasmod0n/chiasmodon` | uv-venv | T0+T2 pass (domain leak records). Token logic in the source reads as AUTH, but a **free API tier works keyless** (5-page cap). Console script is `chiasmodon_cli.py`; query is `-m <mode> <query>` |
| 275 | `vflame6/leaker` | release binary (Go) | T0+T2 pass (example.com leak rows). `linux_amd64` tarball; keyless (auto-writes a provider config). Exit code is nonzero/variable → grep-and-exit wrapper instead of asserting a code |

Takeaway: the long tail isn't all rot — a whole draw can be clean when the tools are Go binaries or
pure-offline Python. New traps here are about **matching the toolchain to the repo**: a `golang:` image
older than `go.mod` fails (gosearch), a release can exist yet be the wrong OS (gosearch `.exe`), an
optional extra separates "runs" from "runs fully" (dnstwist + dnspython), and token-handling *code*
doesn't prove a token is *required* — run the keyless example first (chiasmodon).

## Fifth batch — single-purpose keyless CLIs (ranks 20–268, 2026-08-25)

Not a random draw: six **deliberately picked** single-purpose keyless CLIs to round the
deployed-and-verified count out to 50. All six pass T0+T2. (A seventh, `N0rz3/Zehef`, was examined and
dropped — one module, `picsart`, throws an unhandled `JSONDecodeError` on a changed API and aborts the
async gather; salvageable only with a source patch.)

| # | Tool | Stack | Result / gotcha |
|---|---|---|---|
| 20 | `s0md3v/Photon` | uv-venv | crawls example.com, extracts URLs; writes a `<domain>/` output dir in cwd |
| 33 | `p1ngul1n0/blackbird` | uv-venv | username search; **auto-fetches `data/wmn-data.json` on run — do NOT pass `--no-update` on a fresh checkout** or it dies FileNotFoundError |
| 80 | `thewhiteh4t/nexfil` | uv-venv (pyproject, src/ layout) | finds octocat profiles; **no `requirements.txt`** → `uv pip install .`; `undetected_chromedriver` is an optional JS-site dep, warns but works without |
| 92 | `initstring/cloud_enum` | uv-venv (pyproject) | enumerates public AWS/Azure/GCP for a keyword; keyless DNS/HTTP; `-k example` finds `example.s3.amazonaws.com` |
| 94 | `megadose/ignorant` | uv tool | phone-number-used check (holehe's sibling); positional `country_code number`; `[x]` = per-site rate limit |
| 268 | `akamhy/waybackpy` | uv tool | Wayback/CDX client; `--oldest` returns the earliest snapshot; cosmetic click "parameter used more than once" warnings on stderr → drop stderr |

Takeaway: two reusable lessons — a **`pyproject`-only repo has no `requirements.txt` and that's not an
error**, you `uv pip install .` the package (nexfil, cloud_enum); and a tool that **fetches its data file
on first run** (blackbird's WhatsMyName list) breaks if you pass its `--no-update`/offline flag before
that file exists — let the first run download it.