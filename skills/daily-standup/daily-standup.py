#!/usr/bin/env python3
"""
VV Daily Standup — Multi-Agent Standup System
Each agent logs to their own file, then a summary is generated.
"""

import os
import json
import urllib.request
import urllib.parse
from datetime import datetime

WORKSPACE = "/home/yat121/.openclaw/workspace"
SKILL_DIR = f"{WORKSPACE}/skills/daily-standup"
AGENTS_DIR = f"{SKILL_DIR}/agents"
STANDUP_FILE = f"{SKILL_DIR}/standups.json"

TELEGRAM_BOT_TOKEN = "8652497348:AAGf16He0xuI80MymX0kJs1TRnqmLTRYnaE"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
DESMOND_CHAT_ID = "869229225"
DASHBOARD_URLS = {
    "Dashboard": "https://yat121.github.io/daily-dashboard/",
    "Quant Alpha": "https://naturally-liberty-full-quantitative.trycloudflare.com",
    "Property": "https://native-pointer-ensure-dining.trycloudflare.com",
    "Meeting Prep": "https://diabetes-provider-illustrations-patrick.trycloudflare.com",
}


def ensure_dirs():
    os.makedirs(AGENTS_DIR, exist_ok=True)


def get_agent_file(agent: str) -> str:
    return f"{AGENTS_DIR}/{agent}-standup.json"


def load_agent_standup(agent: str) -> dict:
    """Load standup data for an agent."""
    filepath = get_agent_file(agent)
    if os.path.exists(filepath):
        with open(filepath) as f:
            return json.load(f)
    return {}


def save_agent_standup(agent: str, data: dict):
    """Save standup data for an agent."""
    filepath = get_agent_file(agent)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def log_agent_activity(agent: str, section: str, content: str):
    """Log an activity for an agent."""
    ensure_dirs()
    today = datetime.now().strftime("%Y-%m-%d")

    data = load_agent_standup(agent)

    if today not in data:
        data[today] = {"yesterday": "", "today": "", "blockers": "", "activities": []}

    if section in ["yesterday", "today", "blockers"]:
        data[today][section] = content
    elif section == "activity":
        data[today]["activities"].append(
            {"time": datetime.now().isoformat(), "content": content}
        )

    data[today]["updated"] = datetime.now().isoformat()
    save_agent_standup(agent, data)
    return f"✅ Logged to {agent}: {content[:50]}..."


def update_agent_standup(
    agent: str, yesterday: str = None, today: str = None, blockers: str = None
):
    """Update full sections for an agent."""
    ensure_dirs()
    today_key = datetime.now().strftime("%Y-%m-%d")

    data = load_agent_standup(agent)

    if today_key not in data:
        data[today_key] = {
            "yesterday": "",
            "today": "",
            "blockers": "",
            "activities": [],
        }

    if yesterday is not None:
        data[today_key]["yesterday"] = yesterday
    if today is not None:
        data[today_key]["today"] = today
    if blockers is not None:
        data[today_key]["blockers"] = blockers

    data[today_key]["updated"] = datetime.now().isoformat()
    save_agent_standup(agent, data)
    return f"✅ Updated {agent} standup"


def get_all_standups() -> dict:
    """Load standups from all agents."""
    agents = {}
    if os.path.exists(AGENTS_DIR):
        for f in os.listdir(AGENTS_DIR):
            if f.endswith("-standup.json"):
                agent = f.replace("-standup.json", "")
                agents[agent] = load_agent_standup(agent)
    return agents


def generate_summary() -> str:
    """Generate multi-agent standup summary."""
    today = datetime.now().strftime("%Y-%m-%d")
    agents = get_all_standups()

    if not agents:
        return "📋 No standups recorded yet today."

    summary = f"*📋 Multi-Agent Daily Standup* — {today}\n\n"

    for agent, data in agents.items():
        if today in data:
            entry = data[today]

            # Mapping of agent to display name and emoji
            name_map = {
                "vv": ("VV", "🤖"),
                "caca": ("Caca", "🍫"),
                "rasp": ("Rasp", "🔍"),
                "mimi": ("Mimi", "🎯"),
                "potato": ("Potato", "🥔"),
            }
            display_name, emoji = name_map.get(agent, (agent.capitalize(), "👤"))

            summary += f"{emoji} *{display_name}*\n"

            if entry.get("yesterday"):
                summary += f"  Yesterday: {entry['yesterday']}\n"
            if entry.get("today"):
                summary += f"  Today: {entry['today']}\n"
            if entry.get("blockers"):
                summary += f"  Blockers: {entry['blockers']}\n"

            # Show recent activities
            activities = entry.get("activities", [])
            if activities:
                summary += f"  Recent: {'; '.join([a['content'][:40] for a in activities[-3:]])}\n"

            summary += "\n"

    return summary.strip()


def send_summary():
    """Send standup summary to Desmond."""
    summary = generate_summary()
    url = f"{TELEGRAM_API}/sendMessage"
    # Append all dashboard links
    links = "\n\n".join([f"🌐 {name}: {url}" for name, url in DASHBOARD_URLS.items()])
    full_message = f"{summary}\n\n{links}"
    data = urllib.parse.urlencode(
        {"chat_id": DESMOND_CHAT_ID, "text": full_message, "parse_mode": "Markdown"}
    ).encode()
    req = urllib.request.Request(url, data=data)
    urllib.request.urlopen(req, timeout=10)
    return full_message


def auto_standup_vv():
    """Generate automatic standup for all agents."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    # Update VV
    update_agent_standup(
        "vv",
        yesterday="Set up QMD memory, agent-browser skill, tech research, morning brief, daily proposer, self-improving memory system",
        today="Monitoring workflows, ready to assist, continuing improvements",
        blockers="None 🎉",
    )
    # Caca
    update_agent_standup(
        "caca",
        yesterday="Pushed Quant-Alpha to GitHub Pages, updated HK Cafe Map, fixed tile provider issues, implemented strategy improvements",
        today="Coding tasks, reviewing projects, continuing improvements",
        blockers="None 🎉",
    )
    # Rasp
    update_agent_standup(
        "rasp",
        yesterday="Tech research, market analysis, QMD research tasks",
        today="Research tasks, analysis, continuing improvements",
        blockers="None 🎉",
    )
    # Mimi
    update_agent_standup(
        "mimi",
        yesterday="Social media setup, Top5Battle content planning, marketing strategy",
        today="Social media management, content creation, marketing tasks",
        blockers="Social media automation pending (Meta API setup)",
    )
    # Potato
    update_agent_standup(
        "potato",
        yesterday="Quant-Alpha backtesting, RSI strategy analysis, dashboard improvements",
        today="Trading strategy work, IBKR setup, Quant-Alpha development",
        blockers="IBKR connection pending",
    )
    return "✅ All agents standup updated"


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: daily-standup.py <action> [args]")
        print("Actions:")
        print("  log <agent> <section> <content>")
        print("  update <agent> [--yesterday X] [--today X] [--blockers X]")
        print("  show [agent]")
        print("  summary")
        print("  send")
        print("  auto-vv")
        sys.exit(1)

    action = sys.argv[1]

    if action == "log":
        agent = sys.argv[2] if len(sys.argv) > 2 else "vv"
        section = sys.argv[3] if len(sys.argv) > 3 else "activity"
        content = sys.argv[4] if len(sys.argv) > 4 else ""
        print(log_agent_activity(agent, section, content))

    elif action == "update":
        agent = sys.argv[2] if len(sys.argv) > 2 else "vv"
        yesterday = today = blockers = None
        for i, arg in enumerate(sys.argv):
            if arg == "--yesterday" and i + 1 < len(sys.argv):
                yesterday = sys.argv[i + 1]
            if arg == "--today" and i + 1 < len(sys.argv):
                today = sys.argv[i + 1]
            if arg == "--blockers" and i + 1 < len(sys.argv):
                blockers = sys.argv[i + 1]
        print(update_agent_standup(agent, yesterday, today, blockers))

    elif action == "show":
        agent = sys.argv[2] if len(sys.argv) > 2 else None
        if agent:
            print(json.dumps(load_agent_standup(agent), indent=2))
        else:
            print(json.dumps(get_all_standups(), indent=2))

    elif action == "summary":
        print(generate_summary())

    elif action == "send":
        print(send_summary())

    elif action == "auto-vv":
        print(auto_standup_vv())

    elif action == "caca-log":
        # For Caca to log her work
        content = sys.argv[2] if len(sys.argv) > 2 else ""
        print(log_agent_activity("caca", "activity", content))

    else:
        print(f"Unknown action: {action}")
