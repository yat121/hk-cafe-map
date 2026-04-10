#!/usr/bin/env python3
"""Morning Brief - Email + Calendar summary via Telegram"""

import json
import urllib.request
import re
import os
from datetime import datetime, timedelta

# ===== CONFIGURATION =====
MATON_API_KEY = "D2RGPr7Xov0s0fhqULJATtI9h8GjEhwj8OlCUJkQ08Lza8x2313VQdWKWBbF_HNKTXHdl5oR3YA1wwS2b6cts0Cps3clrCO25U0"
TG_BOT_TOKEN = "8652497348:AAGf16He0xuI80MymX0kJs1TRnqmLTRYnaE"
TG_CHAT_ID = "869229225"

# Urgent keywords (LinkedIn not included - not urgent)
URGENT_KW = [
    "rent",
    "property",
    "aop",
    "poets place",
    "service charge",
    "tax",
    "payment",
    "invoice",
    "deadline",
    "urgent",
    "important",
]


def fetch_url(url):
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {MATON_API_KEY}"}
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read())


def get_sender_name(from_val):
    match = re.search(r'^"?([^"<]+)"?\s*<', from_val)
    if match:
        return match.group(1).strip()
    return from_val.split("@")[0] if "@" in from_val else from_val


def main():
    print("🌅 Morning Brief started")

    # ===== GET GMAIL =====
    print("📧 Checking Gmail...")
    gmail_data = fetch_url(
        "https://gateway.maton.ai/google-mail/gmail/v1/users/me/messages?maxResults=20&q=is:unread"
    )
    msgs = gmail_data.get("messages", [])
    total_emails = len(msgs)
    print(f"📧 Found {total_emails} unread emails")

    urgent_items = []
    summary_items = []
    subjects_seen = set()

    for m in msgs[:20]:
        msg_id = m["id"]
        try:
            msg_data = fetch_url(
                f"https://gateway.maton.ai/google-mail/gmail/v1/users/me/messages/{msg_id}?format=metadata"
            )
            headers = msg_data.get("payload", {}).get("headers", [])
            subject = next(
                (h["value"] for h in headers if h["name"].lower() == "subject"),
                "No Subject",
            )
            from_val = next(
                (h["value"] for h in headers if h["name"].lower() == "from"), "Unknown"
            )
            snippet = msg_data.get("snippet", "")[:80]
            sender = get_sender_name(from_val)

            # Check urgent
            is_urgent = any(kw.lower() in subject.lower() for kw in URGENT_KW)
            if is_urgent:
                urgent_items.append((sender, subject, snippet))

            # Collect summaries (max 5)
            # Deduplicate by subject for summary (show unique subjects only, max 5)
            if subject not in subjects_seen and len(summary_items) < 5:
                summary_items.append((sender, subject))
                subjects_seen.add(subject)
        except Exception as e:
            print(f"  Error fetching message {msg_id}: {e}")

    print(f"🚨 Found {len(urgent_items)} urgent emails")

    # ===== GET CALENDAR =====
    print("📅 Fetching calendar...")
    today = datetime.utcnow()
    week_end = today + timedelta(days=7)

    cal_url = f"https://gateway.maton.ai/google-calendar/calendar/v3/calendars/primary/events?timeMin={today.isoformat()}Z&timeMax={week_end.isoformat()}Z&maxResults=50&singleEvents=true&orderBy=startTime"
    cal_data = fetch_url(cal_url)
    events = cal_data.get("items", [])
    print(f"📅 Found {len(events)} calendar events")

    # Format events
    cal_items = []
    for event in events:
        start = event.get("start", {})
        end = event.get("end", {})
        start_val = start.get("dateTime", start.get("date", ""))
        summary = event.get("summary", "Untitled")
        location = event.get("location", "")

        if not start_val:
            continue

        if "T" in start_val:
            try:
                dt = datetime.fromisoformat(
                    start_val.replace("Z", "+00:00").split("+")[0]
                )
                day = dt.strftime("%A, %B %d")
                time_str = dt.strftime("%H:%M")
            except:
                day = start_val[:10]
                time_str = "Time N/A"
        else:
            day = start_val[:10]
            time_str = "All Day"

        loc = f"📍 {location}" if location else ""
        cal_items.append((day, time_str, summary, loc))

    # ===== COMPOSE MESSAGE =====
    # Urgent section
    if urgent_items:
        urgent_text = "🚨 URGENT EMAILS ({})\n".format(len(urgent_items))
        for i, (s, subj, snip) in enumerate(urgent_items, 1):
            urgent_text += f"\n🚨 {i}. {s}\n   {subj}\n   {snip}..."
        urgent_text += "\n\n━━━━━━━━━━━━━━━━━━━━━━━"
    else:
        urgent_text = "✅ No urgent emails today\n\n━━━━━━━━━━━━━━━━━━━━━━━"

    # Summary section
    if summary_items:
        summary_text = f"📬 UNREAD OVERVIEW ({total_emails} total, top 5):\n"
        for s, subj in summary_items:
            summary_text += f"\n• {s}: {subj}"
        summary_text += "\n\n━━━━━━━━━━━━━━━━━━━━━━━"
    else:
        summary_text = ""

    # Calendar section
    if cal_items:
        cal_text = ""
        for day, time_str, summary, loc in cal_items:
            cal_text += f"\n📆 {day} | {time_str}\n   {summary}{loc}"
    else:
        cal_text = "\n📭 No events scheduled this week"

    # Final message
    message = f"""🌅 Good Morning, Desmond!

━━━━━━━━━━━━━━━━━━━━━━━
{urgent_text}
{summary_text}
📅 THIS WEEK'S SCHEDULE ({len(cal_items)} events)
{cal_text}

━━━━━━━━━━━━━━━━━━━━━━━
Have a productive day! 🌅"""

    # ===== SEND TELEGRAM =====
    print("📤 Sending Telegram message...")
    tg_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    data = json.dumps(
        {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML"}
    ).encode()

    req = urllib.request.Request(
        tg_url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read())
        if result.get("ok"):
            print("✅ Telegram message sent!")
        else:
            print(f"❌ Telegram error: {result}")

    print("🌅 Morning Brief done")


if __name__ == "__main__":
    main()
