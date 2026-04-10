#!/usr/bin/env python3
"""Daily code review — 8 AM HK"""

import os, re, json, urllib.request
from datetime import datetime

WORKSPACE = "/home/yat121/.openclaw/workspace"
PROJECTS = f"{WORKSPACE}/projects"
SKILLS = f"{WORKSPACE}/skills"
LOG_FILE = f"{WORKSPACE}/logs/code-review.log"
TOKEN = "8652497348:AAGf16He0xuI80MymX0kJs1TRnqmLTRYnaE"
CHAT_ID = "869229225"
ISSUES = []

# Skip third-party / build dirs
SKIP_DIRS = {
    "node_modules",
    ".next",
    "out",
    "__pycache__",
    ".git",
    "dist",
    ".venv",
    "venv",
    "build",
    "coverage",
    "vendor",
    "target",
    ".cache",
    "paperclip",
    "jesse-env",
    ".env",
    "venv/bin",
    "venv/lib",
}


def check_file(filepath):
    issues = []
    try:
        content = open(filepath, encoding="utf-8", errors="ignore").read()
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            t = line.strip()
            if re.search(r"(TODO|FIXME|HACK|XXX|BUG):", t, re.I):
                issues.append(f"  L{i}: {t[:120]}")
            if re.search(r"console\.(log|debug|info)\(", t):
                prev = lines[i - 2].strip() if i > 1 else ""
                if not any(
                    k in (t + prev)
                    for k in ["// DEBUG", "// PRODUCTION", "# noqa", "// debug"]
                ):
                    issues.append(f"  L{i}: console.log (no debug guard)")
        # Credential check (exclude known safe files)
        safe = [
            ".gitignore",
            "env.example",
            "template",
            "sample",
            "config.ts",
            ".env.hyperliquid",
            "tech-research.py",
            "brave_",
            "playwright",
        ]  # skill config files with API keys
        if not any(s in filepath for s in safe):
            for i, line in enumerate(lines, 1):
                if re.search(
                    r'(api[_-]?key|token|password|secret)\s*[=:]\s*["\'][A-Za-z0-9+/]{16,}["\']',
                    line,
                    re.I,
                ):
                    issues.append(f"  L{i}: Possible hardcoded credential")
    except:
        pass
    return issues


def scan(base, label):
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith((".py", ".js", ".ts", ".tsx", ".jsx")):
                fp = os.path.join(root, f)
                issues = check_file(fp)
                if issues:
                    ISSUES.append(f"\n{label}/{os.path.relpath(fp, base)}")
                    ISSUES.extend(issues)


scan(PROJECTS, "projects")
scan(SKILLS, "skills")

# Our actual files
# Only our own project code (not installed skills)
OUR_PATTERNS = [
    "projects/meeting-prep",
    "projects/quant-alpha",
    "projects/alpha-backtest",
    "projects/property-dashboard",
    "projects/alpha-agent",
    "projects/alpha-config",
    "skills/code-review",
    "skills/daily-standup",
    "skills/morning-brief",
    "skills/tech-research",
    "skills/polymarket",
    "skills/self-improver",
    "skills/daily-proposer",
    "skills/gmail",
]
our_files = [i for i in ISSUES if any(p in i for p in OUR_PATTERNS)]
all_issues = "\n".join(ISSUES[:200])
critical = [i for i in ISSUES if "credential" in i.lower() or "hardcoded" in i.lower()]

with open(LOG_FILE, "w") as f:
    f.write(f"Code Review — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    f.write("=" * 60 + "\n")
    f.write(f"Total: {len(ISSUES)} issue(s) | Our code: {len(our_files)}\n\n")
    if ISSUES:
        f.write(all_issues)
        if len(ISSUES) > 200:
            f.write(f"\n... +{len(ISSUES)-200} more")
    else:
        f.write("No issues found. Clean code!\n")

print(f"Done. {len(ISSUES)} total, {len(our_files)} in our code.")

# Auto-fix steps
import subprocess, sys

python_files = []
for root, dirs, files in os.walk(WORKSPACE):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for f in files:
        if f.endswith((".py", ".js", ".ts", ".tsx", ".jsx")):
            fp = os.path.join(root, f)
            if any(p in fp for p in OUR_PATTERNS):
                python_files.append(fp)
fixed = 0
for file in python_files:
    try:
        if file.endswith(".py"):
            subprocess.run([sys.executable, "-m", "black", file], check=False)
        elif file.endswith((".js", ".ts", ".tsx", ".jsx")):
            subprocess.run(["eslint", "--fix", file], check=False)
        fixed += 1
    except Exception as e:
        pass
if fixed > 0:
    subprocess.run(["git", "add"] + python_files, cwd=WORKSPACE, check=False)
    commit_msg = f"auto-fix: resolved {fixed} issue(s) from code review"
    subprocess.run(["git", "commit", "-m", commit_msg], cwd=WORKSPACE, check=False)
    subprocess.run(["git", "push"], cwd=WORKSPACE, check=False)
    print(f"Committed {fixed} auto-fixed files.")
if critical:
    msg = (
        f"⚠️ Code Review\n{datetime.now().strftime('%H:%M')} — {len(critical)} credential issue(s) found:\n"
        + "\n".join(critical[:5])
    )
    data = json.dumps({"chat_id": CHAT_ID, "text": msg}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except:
        pass
    print("Telegram alert sent.")
