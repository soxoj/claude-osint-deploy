#!/usr/bin/env python3
"""Phase 1 recon: shallow-clone a repo and print every fact the stack decision needs.

usage: recon.py <owner/repo | url> [--dir ~/osint_tools/src]
Stdlib only. Prints a compact report; read the CI section first.
"""
import argparse, json, os, re, subprocess, sys, urllib.request
from pathlib import Path

def sh(cmd, cwd=None):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=300)
    return (p.stdout + p.stderr).strip()

def api(path):
    try:
        req = urllib.request.Request("https://api.github.com" + path,
                                     headers={"Accept": "application/vnd.github+json"})
        return json.load(urllib.request.urlopen(req, timeout=20))
    except Exception as e:
        return {"_error": str(e)}

def _hub(ref):
    try:
        urllib.request.urlopen(f"https://hub.docker.com/v2/repositories/{ref}/", timeout=10)
        return "yes"
    except Exception as e:
        return "no" if "404" in str(e) else f"? ({e.__class__.__name__})"


def _ghcr(ref):
    try:
        tok = json.load(urllib.request.urlopen(
            f"https://ghcr.io/token?scope=repository:{ref}:pull&service=ghcr.io", timeout=10))["token"]
        req = urllib.request.Request(f"https://ghcr.io/v2/{ref}/manifests/latest",
                                     headers={"Authorization": f"Bearer {tok}",
                                              "Accept": "application/vnd.oci.image.index.v1+json,"
                                                        "application/vnd.docker.distribution.manifest.list.v2+json,"
                                                        "application/vnd.docker.distribution.manifest.v2+json"})
        urllib.request.urlopen(req, timeout=10)
        return "yes"
    except Exception as e:
        return "no" if ("404" in str(e) or "403" in str(e)) else f"? ({e.__class__.__name__})"


MANIFESTS = ["pyproject.toml", "setup.py", "requirements.txt", "package.json", "go.mod",
             "Cargo.toml", "Dockerfile", "docker-compose.yml", "compose.yaml", "Makefile", "tox.ini"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--dir", default=os.path.expanduser("~/osint_tools/src"))
    a = ap.parse_args()
    slug = re.sub(r"^https?://github\.com/|\.git$", "", a.repo).strip("/")
    name = slug.split("/")[-1]
    dest = Path(a.dir) / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        sh(f"git clone -q --depth 1 https://github.com/{slug}.git {dest}")
    if not dest.exists():
        sys.exit(f"clone failed: {slug}")

    meta = api(f"/repos/{slug}")
    rel = api(f"/repos/{slug}/releases/latest")
    assets = [x["name"] for x in rel.get("assets", [])] if isinstance(rel, dict) else []

    print(f"## {slug}  ->  {dest}")
    print(f"stars={meta.get('stargazers_count')} lang={meta.get('language')} "
          f"pushed={str(meta.get('pushed_at'))[:10]} archived={meta.get('archived')} "
          f"license={(meta.get('license') or {}).get('spdx_id')}")
    print(f"last_commit={sh('git log -1 --date=short --format=%ad', dest)}")

    print("\n### is it a runnable tool?")
    entry = []
    if (dest / "pyproject.toml").exists():
        entry += re.findall(r"^\s*([\w.-]+)\s*=\s*[\"'][\w.:]+[\"']",
                            sh("sed -n '/\\[project.scripts\\]/,/^\\[/p;"
                               "/\\[tool.poetry.scripts\\]/,/^\\[/p' pyproject.toml", dest), re.M)
    if (dest / "package.json").exists():
        try:
            pj = json.loads((dest / "package.json").read_text())
            entry += list(pj.get("bin", {}) if isinstance(pj.get("bin"), dict) else [pj.get("name")] if pj.get("bin") else [])
        except Exception:
            pass
    if (dest / "setup.py").exists():
        entry += re.findall(r"'([\w.-]+)\s*=\s*[\w.]+:\w+'", (dest / "setup.py").read_text())
    md_only = not any((dest / m).exists() for m in MANIFESTS)
    print(f"entry_points={entry or '-'}  manifest_files="
          f"{[m for m in MANIFESTS if (dest / m).exists()] or 'NONE'}")
    if md_only:
        print("!! no build manifest -> probably an awesome-list / docs / skills collection, NOT a tool")

    print("\n### CI (ground truth)")
    wf = sorted((dest / ".github/workflows").glob("*.y*ml")) if (dest / ".github/workflows").exists() else []
    print(f"workflows={[w.name for w in wf] or 'NONE'}")
    for w in wf[:6]:
        t = w.read_text()
        py = sorted(set(re.findall(r"python-version:\s*\[?\s*['\"]?([\d.txt ,'\"]+)", t)))
        oses = sorted(set(re.findall(r"(ubuntu-[\w.]+|windows-[\w.]+|macos-[\w.]+)", t)))
        tests = [l.strip()[:110] for l in t.splitlines()
                 if re.search(r"\b(pytest|tox|go test|npm (run )?test|jest|vitest|cargo test|unittest)\b", l)]
        if py or oses or tests:
            print(f"  {w.name}: py={py} os={oses}")
            for c in tests[:4]:
                print(f"     test> {c}")

    print("\n### constraints")
    for pat, label in [(r"requires-python\s*=\s*\S+", "requires-python"),
                       (r"python_requires\s*=\s*\S+", "python_requires"),
                       (r"^python\s*=\s*\S+", "poetry-python"),
                       (r"^go \d[\d.]*", "go"),
                       (r'"node"\s*:\s*"[^"]+"', "node-engine")]:
        hit = sh(f"grep -rhoE '{pat}' pyproject.toml setup.py go.mod package.json 2>/dev/null | head -2", dest)
        if hit:
            print(f"  {label}: {hit}")
    sysdeps = sh("grep -rhoE '(apt-get install|apt install|brew install|yum install)[^\"'\\''|&]*' "
                 ".github/workflows Dockerfile* README* 2>/dev/null | head -4", dest)
    print(f"  system-deps: {sysdeps or '-'}")
    keys = sh("grep -rhoiE '[A-Z0-9_]*(API_KEY|APIKEY|TOKEN|SECRET)[A-Z0-9_]*' "
              "README* .env.example* 2>/dev/null | sort -u | head -8", dest)
    print(f"  api-keys mentioned: {keys.split() or '-'}")

    print("\n### published images (discovered, not from a stored list)")
    imgs = []
    for w in wf:
        t = w.read_text()
        if re.search(r"docker/(build-push|metadata)-action|docker push", t):
            body = "\n".join(l for l in t.splitlines() if not re.match(r"\s*(-\s*)?uses:", l))
            imgs += re.findall(r"(?:ghcr\.io/|docker\.io/)?((?:[\w.-]+/)+[\w.-]+)", body)
    for f in ("README.md", "docs/README.md", "docker-compose.yml", "compose.yaml"):
        if (dest / f).exists():
            txt = (dest / f).read_text(errors="replace")
            imgs += re.findall(r"docker\s+(?:run|pull)\s+((?:-\S+\s+|\S+:\S+\s+)*)((?:[\w.-]+/)+[\w.-]+)", txt) \
                and [m[1] for m in re.findall(r"docker\s+(?:run|pull)\s+((?:-{1,2}\S+(?:\s+\S+)?\s+)*)((?:[\w.-]+/)+[\w.-]+)", txt)]
            imgs += re.findall(r"^\s*image:\s*([\w./-]+)", txt, re.M)
    owner = slug.split("/")[0]
    cands = []
    for i in imgs + [slug.lower(), f"{owner.lower()}/{name.lower()}"]:
        i = re.sub(r"^(ghcr\.io|docker\.io|registry\.hub\.docker\.com)/", "", i.strip().rstrip(":/"))
        head = i.split("/")[0]
        if i.count("/") != 1 or "." in head or head in ("actions", "docker", "tmp", "app", "home", "var", "opt", "usr", "mnt"):
            continue
        if i not in cands:
            cands.append(i)
    hits = [(c, _hub(c), _ghcr(c)) for c in cands[:8]]
    hits = [(c, h, g) for c, h, g in hits if "yes" in (h, g)]
    for c, h, g in hits:
        print(f"  {'docker.io/' + c if h == 'yes' else 'ghcr.io/' + c}   (hub={h} ghcr={g})")
    print("  " + ("an official image beats building the Dockerfile: no build time, maintainer-tested"
                  if hits else "none published - build the repo's Dockerfile, or skip Docker"))

    print("\n### deploy inputs")
    print(f"  release assets: {assets[:8] or '-'}")
    print(f"  docker: {[m for m in ('Dockerfile','docker-compose.yml','compose.yaml') if (dest/m).exists()] or '-'}")
    print(f"  tests dir: {[p.name for p in dest.iterdir() if p.is_dir() and p.name in ('tests','test','__tests__','spec')] or '-'}")

    print("\n### README example invocations")
    readme = next((p for p in list(dest.glob("README*")) + list(dest.glob("docs/README*"))), None)
    if readme:
        txt = readme.read_text(errors="replace")
        pat = re.compile(rf"^\s*[$>#]?\s*((?:sudo\s+)?(?:python3?\s+-m\s+\S+|uv run \S+|npx\s+\S+|docker\s+run\s+\S+|\./?{re.escape(name)}\S*|{re.escape(name)}(?:\.py)?)[ \t]+[^\n`]*)", re.M | re.I)
        seen = []
        for m in pat.finditer(txt):
            c = m.group(1).strip()
            if c not in seen and 4 < len(c) < 160 and "\n" not in c:
                seen.append(c)
        for c in seen[:10]:
            print(f"  $ {c}")
        if not seen:
            print("  (none matched - read the README manually)")
    else:
        print("  no README found")

if __name__ == "__main__":
    main()
