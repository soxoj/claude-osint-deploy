# OSINT Tool Deploy Skill

<p align="center">
  <img src="docs/logo.jpeg" alt="claude-osint-deploy" width="220">
</p>

<p align="center">
  <b>Claude Code plugin/skill: install an OSINT tool from GitHub on any OS and prove it works.</b>
</p>

## Quick Start

**As a plugin** (gets updates, one command to install):

```
/plugin marketplace add soxoj/claude-osint-deploy
/plugin install osint-deploy@osint-deploy-marketplace
```

**As a bare skill** (no marketplace, no updates):

```
git clone https://github.com/soxoj/claude-osint-deploy
cp -r claude-osint-deploy/skills/osint-deploy ~/.claude/skills/        # user-wide
cp -r claude-osint-deploy/skills/osint-deploy .claude/skills/          # or one project
```

Either way you then say *"install sherlock from github and make sure it works"*, or type
`/osint-deploy sherlock-project/sherlock`.

## What it does

You point it at a GitHub repo. It gets that tool running on your machine and then shows you proof
that it actually works.

Getting there means answering questions you would otherwise answer by hand:

- **What is this repo, really?** A CLI, a web server, a desktop app, a browser extension, or just an
  awesome-list with nothing to install. Each needs a different treatment.
- **How should it be installed here?** A prebuilt binary if the project ships one, Docker if the
  dependencies are heavy, an isolated Python environment with the interpreter version the project
  actually wants — whichever is the least work that still satisfies the project's constraints. On
  Windows it also decides *where* to run it: WSL, Docker, or native.
- **Does it work?** Not "did the install command exit 0" — it runs the project's own test suite,
  taken from its CI configuration, and the example commands from its README against real targets.
- **And if something fails, whose fault is it?** A rate-limited API, a missing key, a login you have
  to do yourself and an actually broken install look identical at first glance. They get told apart
  and reported separately, so you never chase a bug that isn't yours.

Everything it learns goes into a recipe, so reinstalling the same tool later — or on another
machine — is one command.

## What's Inside

```
skills/osint-deploy/
  SKILL.md                      the 7-phase procedure + the traps it exists for
  references/stacks.md          stack decision table, per-OS quirks, bootstrap
  references/verify.md          manifest format, server/auth patterns, failure classes
  references/known-tools.md     the top 10 as actually deployed + per-tool gotchas
  references/troubleshooting.md symptom -> cause -> fix ladder
  scripts/env_probe.py          one call, all stack-decision facts (stdlib only)
  scripts/recon.py              one call, all Phase 1 repo facts incl. CI test commands
  scripts/verify.py             runs a checks manifest, PASS/FAIL/NET/SKIP (stdlib only)
  examples/*.checks.json        5 manifest templates, one per check shape
```

## Verified

Two honest numbers:

- **~65 repositories examined** — from GitHub's `topic:osint` (the top 10 by stars, plus random
  samples down to rank ~300).
- **50 tools deployed and verified end-to-end** — each with a passing check manifest in
  `~/osint_tools/recipes/`.

The rest were correctly classified as **not-installable** (awesome-lists, a wordlist, a desktop
`.exe`, multi-container platforms) — a "no" is a valid result, not a failure.

The verified set spans:

- plain CLIs and interactive/stdin menu tools
- web servers and a desktop app
- browser extensions
- prebuilt Go binaries and pure-offline generators
- auth-gated tools (reported as `NEEDS_KEY`, not silently skipped)

`examples/` ships **five** manifest templates, one per check shape: CLI, Docker-CLI, server,
auth-gated, interactive/stdin.

## Requirements

`python3` (3.9+, stdlib only — no pip install for this repo) and `git`. Everything else is decided
per tool: `uv` is the default Python path and can bootstrap its own interpreter, Docker is the
fallback for anything with heavy native deps, and neither is required up front.

> Use the tools it installs only against targets you are authorised to investigate. Verification is
> limited to one small query per check, against the targets the projects themselves document.

## License

MIT — see [LICENSE](LICENSE).
