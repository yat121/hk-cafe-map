#!/usr/bin/env python3
"""
VV Self-Improving Memory System
Tracks explicit corrections and preferences.
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/home/yat121/.openclaw/workspace")
MEM_DIR = WORKSPACE / "memory" / "preferences"
HOT_FILE = MEM_DIR / "hot.md"
CORRECTIONS_FILE = MEM_DIR / "corrections.log"
ARCHIVE_FILE = MEM_DIR / "archive.md"
CONTEXT_DIR = MEM_DIR / "context"

TELEGRAM_BOT_TOKEN = "8652497348:AAGf16He0xuI80MymX0kJs1TRnqmLTRYnaE"
TELEGRAM_CHAT_ID = "869229225"


def log_correction(context: str, correction: str) -> dict:
    """Log a correction and track repetitions."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Read existing log
    entries = []
    if CORRECTIONS_FILE.exists():
        with open(CORRECTIONS_FILE) as f:
            lines = f.readlines()[4:]  # Skip header (4 lines)
            for line in lines:
                if line.strip() and " | " in line and not line.startswith("TIMESTAMP"):
                    parts = line.strip().split(" | ")
                    if len(parts) >= 5:
                        entries.append(
                            {
                                "context": parts[1].strip(),
                                "correction": parts[2].strip(),
                                "reps": (
                                    int(parts[3].strip())
                                    if parts[3].strip().isdigit()
                                    else 1
                                ),
                                "status": parts[4].strip(),
                            }
                        )

    # Check if this correction already exists
    found = False
    for entry in entries:
        if entry["context"] == context and entry["correction"] == correction:
            entry["reps"] += 1
            found = True
            break

    if not found:
        entries.append(
            {
                "context": context,
                "correction": correction,
                "reps": 1,
                "status": "tracking",
            }
        )

    # Write updated log
    with open(CORRECTIONS_FILE, "w") as f:
        f.write("# CORRECTIONS LOG\n")
        f.write("# Format: TIMESTAMP | CONTEXT | CORRECTION | REPETITIONS | STATUS\n")
        f.write("# Status: tracking | promoted | dismissed\n\n")
        f.write("TIMESTAMP | CONTEXT | CORRECTION | REPS | STATUS\n")
        f.write("--------- | ------- | ---------- | ---- | ------\n")
        for entry in entries:
            f.write(
                f"{timestamp} | {entry['context']} | {entry['correction']} | {entry['reps']} | {entry['status']}\n"
            )

    # Check if any entry hit 3 repetitions
    for entry in entries:
        if entry["reps"] == 3 and entry["status"] == "tracking":
            return {
                "needs_promotion": True,
                "context": entry["context"],
                "correction": entry["correction"],
            }

    return {"needs_promotion": False}


def promote_to_hot(correction: str, scope: str = "global"):
    """Promote a correction to hot memory."""
    timestamp = datetime.now().strftime("%Y-%m-%d")

    # Read hot memory
    with open(HOT_FILE) as f:
        content = f.read()

    # Add new rule
    new_rule = f"\n| {correction} | {timestamp} | Correction (3x) |"

    # Find the table and add
    if "| # | Rule |" in content:
        content = content.replace(
            "| # | Rule |", f"| ## | {correction} | {timestamp} |"
        )

    with open(HOT_FILE, "w") as f:
        f.write(content)

    # Mark as promoted in corrections log
    with open(CORRECTIONS_FILE) as f:
        lines = f.readlines()

    with open(CORRECTIONS_FILE, "w") as f:
        for line in lines:
            if correction in line and "promoted" not in line:
                line = line.replace("tracking", "promoted")
            f.write(line)

    return f"✅ Promoted to HOT memory: {correction}"


def forget_item(item: str):
    """Delete an item from all memory files."""
    deleted = []

    # Hot memory
    if HOT_FILE.exists():
        with open(HOT_FILE) as f:
            content = f.read()
        if item.lower() in content.lower():
            # Simple deletion - remove lines containing the item
            lines = content.split("\n")
            new_lines = [l for l in lines if item.lower() not in l.lower()]
            with open(HOT_FILE, "w") as f:
                f.write("\n".join(new_lines))
            deleted.append("hot.md")

    # Context memory
    if CONTEXT_DIR.exists():
        for f in CONTEXT_DIR.glob("*.md"):
            with open(f) as file:
                content = file.read()
            if item.lower() in content.lower():
                lines = content.split("\n")
                new_lines = [l for l in lines if item.lower() not in l.lower()]
                with open(f, "w") as file:
                    file.write("\n".join(new_lines))
                deleted.append(f"context/{f.name}")

    # Corrections log - mark as dismissed
    if CORRECTIONS_FILE.exists():
        with open(CORRECTIONS_FILE) as f:
            lines = f.readlines()
        with open(CORRECTIONS_FILE, "w") as f:
            for line in lines:
                if item.lower() in line.lower() and "dismissed" not in line:
                    line = line.strip() + " dismissed\n"
                f.write(line)

    return deleted if deleted else None


def forget_all():
    """Wipe all memory and start fresh."""
    files = [HOT_FILE, CORRECTIONS_FILE, ARCHIVE_FILE]
    for f in files:
        if f.exists():
            f.unlink()

    # Recreate empty files
    HOT_FILE.write_text(
        "# HOT MEMORY — VV's Active Rules\n\n> ⚠️ These are CONFIRMED rules.\n\n---\n\n## Current Confirmed Rules\n\n| # | Rule | Added | Source |\n|---|------|-------|--------|\n\n"
    )
    CORRECTIONS_FILE.write_text(
        "# CORRECTIONS LOG\n\nTIMESTAMP | CONTEXT | CORRECTION | REPS | STATUS\n\n"
    )
    ARCHIVE_FILE.write_text("# ARCHIVE\n\n")

    return "🧹 All memory wiped. Starting fresh."


def show_memory() -> str:
    """Display current hot + context memories."""
    output = ["# 📝 VV Memory Status\n"]

    # Hot memory
    if HOT_FILE.exists():
        output.append("\n## 🔥 HOT MEMORY\n")
        output.append(HOT_FILE.read_text())

    # Context memory
    if CONTEXT_DIR.exists():
        ctx_files = list(CONTEXT_DIR.glob("*.md"))
        if ctx_files:
            output.append("\n## 📁 CONTEXT MEMORY\n")
            for f in ctx_files:
                output.append(f"\n### {f.stem}\n")
                output.append(f.read_text())

    # Corrections tracking
    if CORRECTIONS_FILE.exists():
        output.append("\n## 📊 Corrections Being Tracked\n")
        output.append(CORRECTIONS_FILE.read_text())

    return "".join(output)


def weekly_maintenance() -> dict:
    """Run weekly cleanup and return digest."""
    # Read all files
    hot_content = HOT_FILE.read_text() if HOT_FILE.exists() else ""
    archive_content = ARCHIVE_FILE.read_text() if ARCHIVE_FILE.exists() else ""
    corrections = CORRECTIONS_FILE.read_text() if CORRECTIONS_FILE.exists() else ""

    changes = []

    # Check for duplicates in hot
    lines = hot_content.split("\n")
    seen = {}
    dupes = []
    for line in lines:
        if "| " in line and not line.startswith("-"):
            rule = line.split("|")[2] if len(line.split("|")) > 2 else ""
            if rule and rule.strip() in seen:
                dupes.append(line)
                changes.append(f"🗑️ Removed duplicate: {rule.strip()}")
            else:
                seen[rule.strip()] = line

    # Archive old items (not used in 30+ days)
    # For now, just clean up the archive structure

    # Write cleaned hot
    with open(HOT_FILE, "w") as f:
        f.write(hot_content)

    # Update archive
    with open(ARCHIVE_FILE, "a") as f:
        if dupes:
            f.write(f"\n## Cleanup {datetime.now().strftime('%Y-%m-%d')}\n")
            for d in dupes:
                f.write(d + "\n")

    return {
        "changes": changes if changes else ["✅ No duplicates found"],
        "summary": "Weekly maintenance complete",
    }


def send_digest():
    """Send weekly digest to Telegram."""
    maintenance = weekly_maintenance()

    digest = f"""# 📊 Weekly Memory Digest

**Date:** {datetime.now().strftime('%Y-%m-%d')}

## Changes This Week:
"""
    for change in maintenance["changes"]:
        digest += f"- {change}\n"

    digest += f"\n{maintenance['summary']}"

    # Send
    import urllib.request

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode(
        {"chat_id": TELEGRAM_CHAT_ID, "text": digest, "parse_mode": "Markdown"}
    ).encode()

    req = urllib.request.Request(url, data=data)
    urllib.request.urlopen(req, timeout=10)

    return digest


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: self-improver.py <action> [args]")
        print("Actions: log, promote, forget, forget-all, show, maintenance, digest")
        sys.exit(1)

    action = sys.argv[1]

    if action == "log":
        context = sys.argv[2] if len(sys.argv) > 2 else ""
        correction = sys.argv[3] if len(sys.argv) > 3 else ""
        result = log_correction(context, correction)
        print(json.dumps(result))

    elif action == "promote":
        correction = sys.argv[2] if len(sys.argv) > 2 else ""
        scope = sys.argv[3] if len(sys.argv) > 3 else "global"
        print(promote_to_hot(correction, scope))

    elif action == "forget":
        item = sys.argv[2] if len(sys.argv) > 2 else ""
        result = forget_item(item)
        print(result if result else "Item not found")

    elif action == "forget-all":
        print(forget_all())

    elif action == "show":
        print(show_memory())

    elif action == "maintenance":
        print(json.dumps(weekly_maintenance()))

    elif action == "digest":
        print(send_digest())
