#!/usr/bin/env python3
"""Run a verification manifest (see references/verify.md). Stdlib only.

usage: verify.py checks.json [--skip-network] [--json out.json] [-v]
exit 0 only if every check passed; NET / SKIP do not fail the run.
"""
import argparse, json, os, re, subprocess, sys, time

NET_ERR = re.compile(r"(connection (reset|refused|error|aborted)|timed? ?out|temporary failure in name"
                     r"|max retries exceeded|429|too many requests|ssl|captcha|network is unreachable"
                     r"|failed to resolve|no address associated)", re.I)


def attempt(c, timeout):
    try:
        p = subprocess.run(c["cmd"], shell=True, capture_output=True, text=True, timeout=timeout,
                           cwd=os.path.expandvars(os.path.expanduser(c["cwd"])) if c.get("cwd") else None,
                           env={**os.environ, **c.get("env", {})})
        out, code = (p.stdout or "") + (p.stderr or ""), p.returncode
    except subprocess.TimeoutExpired as e:
        return ["timeout after %ss" % timeout], (e.stdout or b"").decode("utf8", "replace") + " <timeout>"
    why = []
    if code != c.get("expect_exit", 0):
        why.append(f"exit {code} != {c.get('expect_exit', 0)}")
    if c.get("expect_regex") and not re.search(c["expect_regex"], out, re.I | re.S):
        why.append(f"missing /{c['expect_regex']}/")
    if c.get("expect_absent") and re.search(c["expect_absent"], out, re.I | re.S):
        why.append(f"forbidden /{c['expect_absent']}/")
    return why, out


def check(c, skip_net):
    if c.get("network") and skip_net:
        return "SKIP", "network check skipped", ""
    tries = 1 + int(c.get("retry", 0))
    for i in range(tries):
        if i:
            time.sleep(c.get("retry_delay", 0))
        why, out = attempt(c, c.get("timeout", 120))
        if not why:
            return "PASS", "", out
    extra = c.get("net_if_matches")
    if c.get("network") and (NET_ERR.search(out) or (extra and re.search(extra, out, re.I))):
        return "NET", "; ".join(why) + " (network/rate-limit, not an install failure)", out
    return "FAIL", "; ".join(why), out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--skip-network", action="store_true")
    ap.add_argument("--json")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    m = json.load(open(a.manifest))

    results = []
    for c in m["checks"]:
        status, why, out = check(c, a.skip_network)
        results.append({"name": c["name"], "tier": c.get("tier", "?"), "status": status,
                        "why": why, "tail": out[-400:]})
        print(f"[{status:4}] {c.get('tier','?'):3} {c['name']}" + (f"  — {why}" if why else ""), flush=True)
        if a.verbose and out:
            print("\n".join("       | " + l for l in out.strip().splitlines()[-15:]))

    n = lambda s: sum(r["status"] == s for r in results)
    summary = {"tool": m.get("tool"), "passed": n("PASS"), "failed": n("FAIL"),
               "net": n("NET"), "skipped": n("SKIP"), "results": results}
    print(f"\n{summary['passed']} pass, {summary['failed']} fail, "
          f"{summary['net']} network, {summary['skipped']} skipped")
    if a.json:
        json.dump(summary, open(a.json, "w"), indent=2)
    sys.exit(1 if summary["failed"] else 0)


if __name__ == "__main__":
    main()
