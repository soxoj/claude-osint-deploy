# Verification manifest

`scripts/verify.py` takes a JSON file and returns a pass/fail table plus a JSON summary.

`examples/` holds five manifests as **templates**, one per shape — copy the closest and adapt it:
`sherlock` (CLI + the repo's own tests), `theharvester` (Docker CLI, entrypoint override, self-diagnosing
live check), `web-check` (server: start → poll → API → stop), `ghunt` (auth-gated, T0 only), and
`interactive-cli` (menu/prompt tool driven over stdin, nonzero EOF exit). The manifest you write for a
real deployment belongs in `~/osint_tools/recipes/<tool>.checks.json` alongside its recipe, because it
encodes that machine's paths and that tool's install.

```json
{
  "tool": "sherlock",
  "checks": [
    {"name": "help",    "tier": "T0", "cmd": "sherlock --help",           "expect_exit": 0, "expect_regex": "usage: sherlock"},
    {"name": "version", "tier": "T0", "cmd": "sherlock --version",        "expect_exit": 0},
    {"name": "unit",    "tier": "T1", "cmd": "pytest -q tests/test_x.py", "expect_exit": 0, "timeout": 600},
    {"name": "readme-example", "tier": "T2", "network": true, "retry": 1, "timeout": 300,
     "cmd": "sherlock jack --site GitHub --print-found",
     "expect_exit": 0, "expect_regex": "github\\.com/jack"}
  ]
}
```

Fields: `name`, `cmd`, `tier` (T0/T1/T2), `expect_exit` (default 0), `expect_regex` (searched in
stdout+stderr), `expect_absent` (regex that must NOT appear), `timeout` seconds (default 120),
`network` (true → skipped under `--skip-network`, and a network error is reported as `NET` not `FAIL`),
`retry` (extra attempts for flaky live checks), `retry_delay` (seconds between attempts — use 20–60
when the source rate-limits), `cwd`, `env`.

### Self-diagnosing live checks

A T2 check that depends on **one** third-party data source is flaky by construction. theHarvester's
`-b crtsh,certspotter` intermittently returns zero hosts *with exit 0* — crt.sh was answering 502
during this skill's development. Never loosen the assertion to make that pass. Instead make the check
probe its own sources on failure and tell the runner which output means "upstream, not us":

```json
{"name":"readme-example","tier":"T2","network":true,"retry":2,"retry_delay":30,
 "cmd":"out=$(<the README command> 2>&1); echo \"$out\"; echo \"$out\" | grep -q 'www.example.com' || { echo \"source-health: crtsh=$(curl -s -o /dev/null -w '%{http_code}' -m 20 'https://crt.sh/?q=example.com&output=json')\"; exit 1; }",
 "expect_regex":"www\\.example\\.com",
 "net_if_matches":"(crtsh|certspotter)=(5\\d\\d|000|429)"}
```

`net_if_matches` downgrades a failing `network: true` check from **FAIL** to **NET** only when that
regex appears in the output. Sources answered 200 and still no results → real **FAIL**. Sources
answered 502 → **NET**, install is fine, say which source went quiet.

## Writing good checks

- **T0** proves it's on PATH and importable. Cheap, always include both `--help` and a version/banner.
- **T1** comes from CI, not from your imagination. `grep -A5 'run:' .github/workflows/*.yml`.
  If part of the suite needs credentials or live sites, run the rest and name the excluded tests.
- **T2** comes from the README verbatim, using the target the README itself uses (a maintainer's demo
  account, `example.com`, the project's own domain). Assert on the *shape* of a real result — a URL, a
  count, parseable JSON — never merely exit 0.

## Server / web-app checks

A server has no useful `--help`. Start it, ask the port, wait for readiness, make **one** API call, stop.
As a single manifest command:

```json
{"name":"api-headers","tier":"T2","network":true,"timeout":300,
 "cmd":"CID=$(docker run -d -p 3000 lissy93/web-check:latest); A=$(docker port $CID 3000/tcp|head -1); \
        curl -sS -m 120 --retry 30 --retry-delay 2 --retry-connrefused \"http://$A/api/headers?url=https://example.com\"; \
        R=$?; docker rm -f $CID >/dev/null; exit $R",
 "expect_regex":"\"content-type\""}
```

Three things that make it reliable: `docker port` instead of a hardcoded `localhost:3000` (the mapping
may bind a non-loopback interface), `curl --retry-connrefused` instead of a sleep, and `docker rm -f`
in the same command so a failed check never leaks a container.

## Auth-gated tools

Some tools cannot reach T2 without a real session (GHunt needs `ghunt login` with Google cookies).
Verify T0, assert the *error* is the clean auth error rather than a crash, and report `AUTH_REQUIRED`
with the exact command the user must run. A fabricated T2 pass is worse than an honest blocker.

## Failure classification (report it, don't hide it)

| Symptom | Class | Blocks success? |
|---|---|---|
| ImportError, entry point missing, DLL/ABI error, wrong Python | **BROKEN** | yes — fix and reinstall |
| 401/403 without a key, "API key required" | **NEEDS_KEY** | no — report it |
| 429, captcha, timeout, DNS failure | **NET/RATE** | no — retry once, then report |
| Site changed its HTML, module upstream-broken | **UPSTREAM** | no — report with the module name |
| Needs a login/session the user must create | **AUTH_REQUIRED** | no — report the exact login command |
| Needs a browser binary that will not download | **BLOCKED_DEP** | no — report it, offer the Docker path |
| Exit 0 but no results the README promised | **SUSPECT** | investigate before claiming a pass |

`verify.py` marks `network:true` checks that fail with a connection/timeout/429 as `NET`; everything
else is a real `FAIL` and exits non-zero.
