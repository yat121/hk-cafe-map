#!/usr/bin/env python3
"""Generate the daily dashboard HTML page."""

import json
import os
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
import xml.etree.ElementTree as ET

DASHBOARD_DIR = "/home/yat121/.openclaw/workspace/skills/daily-dashboard"
DATA_DIR = f"{DASHBOARD_DIR}/data"
OUTPUT = f"{DASHBOARD_DIR}/index.html"

# ─── Helpers ────────────────────────────────────────────────────────────────

def hk_now():
    return datetime.now(timezone.utc).astimezone(
        timezone(timedelta(hours=8))
    )

class StripHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
    def handle_data(self, data):
        self.result.append(data)
    def get_text(self):
        return re.sub(r'\s+', ' ', ' '.join(self.result)).strip()

# ─── Data Fetchers ──────────────────────────────────────────────────────────

def parse_weather():
    try:
        with open(f"{DATA_DIR}/weather.json") as f:
            data = json.load(f)
        current = data.get('current_condition', [{}])[0]
        temp_C = current.get('temp_C', 'N/A')
        desc = current.get('weatherDesc', [{}])[0].get('value', 'N/A')
        humidity = current.get('humidity', 'N/A')
        wind = current.get('windspeedKmph', 'N/A')
        
        # 3-day forecast
        forecast = []
        for day in data.get('weather', [])[:3]:
            date = day.get('date', '')
            max_c = day.get('maxtempC', 'N/A')
            min_c = day.get('mintempC', 'N/A')
            desc_f = day.get('hourly', [{}])[0].get('weatherDesc', [{}])[0].get('value', '')
            forecast.append({'date': date, 'max': max_c, 'min': min_c, 'desc': desc_f})
        
        return {'temp': temp_C, 'desc': desc, 'humidity': humidity, 'wind': wind, 'forecast': forecast}
    except Exception as e:
        return {'temp': 'N/A', 'desc': 'N/A', 'humidity': 'N/A', 'wind': 'N/A', 'forecast': [], 'error': str(e)}

def parse_crypto():
    try:
        with open(f"{DATA_DIR}/crypto.json") as f:
            data = json.load(f)
        btc = data.get('bitcoin', {})
        eth = data.get('ethereum', {})
        return {
            'btc_usd': btc.get('usd', 'N/A'),
            'btc_change': btc.get('usd_24h_change', 0),
            'eth_usd': eth.get('usd', 'N/A'),
            'eth_change': eth.get('usd_24h_change', 0),
        }
    except:
        return {'btc_usd': 'N/A', 'btc_change': 0, 'eth_usd': 'N/A', 'eth_change': 0}

def parse_news():
    headlines = []
    try:
        with open(f"{DATA_DIR}/news.json") as f:
            data = json.load(f)
        for hit in data.get('hits', [])[:5]:
            title = hit.get('title', '')
            if title:
                headlines.append(re.sub(r'\s+', ' ', title).strip())
    except:
        pass
    return headlines if headlines else [
        "No news available — check your connection",
        "News refreshes every time you run generate.sh",
        "Tip: Set up a cron job for automatic updates",
    ]

def read_schedule():
    path = os.path.expanduser("~/daily-schedule.txt")
    if os.path.exists(path):
        with open(path) as f:
            content = f.read().strip()
        return content if content else None
    return None

def read_standup():
    today = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    agents_dir = "/home/yat121/.openclaw/workspace/skills/daily-standup/agents"
    lines = []
    for filename in ["vv-standup.json", "caca-standup.json"]:
        filepath = os.path.join(agents_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                entry = data.get(today, {})
                if entry:
                    agent_name = filename.replace("-standup.json", "").upper()
                    yesterday = entry.get("yesterday", "")
                    today_plan = entry.get("today", "")
                    blockers = entry.get("blockers", "")
                    lines.append(f"[{agent_name}]")
                    if yesterday:
                        lines.append(f"  Yesterday: {yesterday}")
                    if today_plan:
                        lines.append(f"  Today: {today_plan}")
                    if blockers:
                        lines.append(f"  Blockers: {blockers}")
            except Exception:
                pass
    return "\n".join(lines) if lines else None

# ─── Build HTML ─────────────────────────────────────────────────────────────

def build_html(weather, crypto, news, schedule, standup):
    now = hk_now()
    updated = now.strftime("%Y-%m-%d %H:%M:%S HKT")
    
    # Weather forecast rows
    forecast_rows = ""
    for f in weather.get('forecast', []):
        day_name = ""
        try:
            d = datetime.strptime(f['date'], '%Y-%m-%d')
            day_name = d.strftime('%a, %b %d')
        except:
            day_name = f['date']
        forecast_rows += f"""
        <div class="forecast-day">
            <div class="forecast-date">{day_name}</div>
            <div class="forecast-desc">{f['desc']}</div>
            <div class="forecast-temps">
                <span class="temp-high">{f['max']}°</span>
                <span class="temp-low">{f['min']}°</span>
            </div>
        </div>"""

    # Format crypto changes
    def fmt_change(v):
        sign = "+" if v > 0 else ""
        return f"{sign}{v:.2f}%"

    # Format crypto prices
    def fmt_price(v):
        if isinstance(v, (int, float)):
            return f"${v:,.0f}"
        return str(v)

    # News items
    news_items = ""
    for i, h in enumerate(news[:5], 1):
        news_items += f'<div class="news-item"><span class="news-num">{i}</span><span class="news-text">{h}</span></div>'

    # Schedule
    if schedule:
        schedule_section = f'<div class="section-content"><pre class="schedule-text">{schedule}</pre></div>'
    else:
        schedule_section = '<div class="section-content placeholder">No ~/daily-schedule.txt found. Create it to show your schedule.</div>'

    # Standup
    if standup:
        standup_section = f'<div class="section-content"><pre class="standup-text">{standup}</pre></div>'
    else:
        standup_section = '<div class="section-content placeholder">No standup data found for today. Standup entries are written by vv/caca agents.</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily Dashboard — {now.strftime('%a, %b %d')}</title>
<style>
  :root {{
    --bg: #0f1117;
    --card: #1a1d27;
    --card2: #21253a;
    --accent: #6c63ff;
    --accent2: #00d4aa;
    --text: #e0e0e0;
    --muted: #888;
    --border: #2a2d3a;
    --green: #4caf50;
    --red: #f44336;
    --yellow: #ff9800;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 20px;
  }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    flex-wrap: wrap;
    gap: 10px;
  }}
  header h1 {{ font-size: 1.5rem; color: var(--accent); }}
  .header-right {{
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 0.85rem;
    color: var(--muted);
  }}
  .refresh-btn {{
    background: var(--accent);
    color: #fff;
    border: none;
    padding: 6px 14px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.85rem;
  }}
  .refresh-btn:hover {{ opacity: 0.85; }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 16px;
  }}
  .card {{
    background: var(--card);
    border-radius: 12px;
    padding: 20px;
    border: 1px solid var(--border);
  }}
  .card-title {{
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--muted);
    margin-bottom: 14px;
  }}
  .weather-current {{
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;
  }}
  .weather-temp {{
    font-size: 3rem;
    font-weight: 700;
    color: var(--accent);
  }}
  .weather-desc {{ color: var(--muted); font-size: 0.9rem; line-height: 1.5; }}
  .forecast {{
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 10px;
  }}
  .forecast-day {{
    background: var(--card2);
    border-radius: 8px;
    padding: 10px 14px;
    flex: 1;
    min-width: 90px;
    text-align: center;
  }}
  .forecast-date {{ font-size: 0.75rem; color: var(--muted); margin-bottom: 4px; }}
  .forecast-desc {{ font-size: 0.8rem; margin-bottom: 6px; }}
  .forecast-temps {{ font-weight: 600; font-size: 0.9rem; }}
  .temp-high {{ color: var(--yellow); margin-right: 6px; }}
  .temp-low {{ color: #90caf9; }}
  .news-item {{
    display: flex;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
    font-size: 0.88rem;
    line-height: 1.4;
  }}
  .news-item:last-child {{ border-bottom: none; }}
  .news-num {{
    color: var(--accent);
    font-weight: 700;
    flex-shrink: 0;
    min-width: 18px;
  }}
  .news-text {{ color: var(--text); }}
  .schedule-text, .standup-text {{
    font-family: 'Fira Code', 'Courier New', monospace;
    font-size: 0.82rem;
    white-space: pre-wrap;
    color: var(--text);
    line-height: 1.6;
  }}
  .placeholder {{
    color: var(--muted);
    font-style: italic;
    font-size: 0.88rem;
  }}
  .crypto-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }}
  .crypto-item {{
    background: var(--card2);
    border-radius: 8px;
    padding: 12px;
  }}
  .crypto-name {{ font-size: 0.75rem; color: var(--muted); margin-bottom: 4px; }}
  .crypto-price {{ font-size: 1.2rem; font-weight: 700; }}
  .crypto-change {{ font-size: 0.8rem; margin-top: 4px; }}
  .change-up {{ color: var(--green); }}
  .change-down {{ color: var(--red); }}
  .stats-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
  }}
  .stat-item {{
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}
  .stat-label {{ font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }}
  .stat-value {{ font-size: 1.1rem; font-weight: 600; color: var(--accent2); }}
  .full-width {{ grid-column: 1 / -1; }}
  .footer {{
    text-align: center;
    margin-top: 24px;
    color: var(--muted);
    font-size: 0.75rem;
  }}
  @media (max-width: 480px) {{
    body {{ padding: 12px; }}
    header h1 {{ font-size: 1.2rem; }}
    .crypto-grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>☀️ Daily Dashboard</h1>
    <div class="header-right">
      <span id="last-updated">Updated: {updated}</span>
      <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
    </div>
  </header>

  <div class="grid">
    <!-- Weather -->
    <div class="card">
      <div class="card-title">🌤 Weather — Hong Kong</div>
      <div class="weather-current">
        <div class="weather-temp">{weather.get('temp', 'N/A')}°C</div>
        <div class="weather-desc">{weather.get('desc', 'N/A')}<br>💧 {weather.get('humidity', 'N/A')}% · 💨 {weather.get('wind', 'N/A')} km/h</div>
      </div>
      <div class="forecast">{forecast_rows if forecast_rows else '<div class="forecast-desc">Forecast unavailable</div>'}</div>
    </div>

    <!-- Crypto -->
    <div class="card">
      <div class="card-title">💹 Crypto Prices</div>
      <div class="crypto-grid">
        <div class="crypto-item">
          <div class="crypto-name">Bitcoin BTC</div>
          <div class="crypto-price">{fmt_price(crypto.get('btc_usd', 'N/A'))}</div>
          <div class="crypto-change {'change-up' if crypto.get('btc_change',0) >= 0 else 'change-down'}">
            {"▲" if crypto.get('btc_change',0) >= 0 else "▼"} {fmt_change(crypto.get('btc_change',0))}
          </div>
        </div>
        <div class="crypto-item">
          <div class="crypto-name">Ethereum ETH</div>
          <div class="crypto-price">{fmt_price(crypto.get('eth_usd', 'N/A'))}</div>
          <div class="crypto-change {'change-up' if crypto.get('eth_change',0) >= 0 else 'change-down'}">
            {"▲" if crypto.get('eth_change',0) >= 0 else "▼"} {fmt_change(crypto.get('eth_change',0))}
          </div>
        </div>
      </div>
    </div>

    <!-- News -->
    <div class="card">
      <div class="card-title">📰 Crypto/Tech News</div>
      <div>{news_items}</div>
    </div>

    <!-- Schedule -->
    <div class="card">
      <div class="card-title">📅 Today's Schedule</div>
      {schedule_section}
    </div>

    <!-- Standup -->
    <div class="card full-width">
      <div class="card-title">✅ Daily Standup</div>
      {standup_section}
    </div>

    <!-- Quick Stats -->
    <div class="card">
      <div class="card-title">⚡ Quick Stats</div>
      <div class="stats-row">
        <div class="stat-item">
          <span class="stat-label">Time (HK)</span>
          <span class="stat-value">{now.strftime('%H:%M:%S')}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Day</span>
          <span class="stat-value">{now.strftime('%A')}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Date</span>
          <span class="stat-value">{now.strftime('%d %b %Y')}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Week</span>
          <span class="stat-value">Week {now.isocalendar()[1]}</span>
        </div>
      </div>
    </div>
  </div>

  <div class="footer">
    Run <code>bash skills/daily-dashboard/generate.sh</code> to refresh data<br>
    File location: {OUTPUT}
  </div>
</div>
</body>
</html>"""
    return html

def fmt_change(v):
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.2f}%"

if __name__ == "__main__":
    from datetime import timedelta

    weather = parse_weather()
    crypto = parse_crypto()
    news = parse_news()
    schedule = read_schedule()
    standup = read_standup()

    html = build_html(weather, crypto, news, schedule, standup)

    with open(OUTPUT, "w") as f:
        f.write(html)

    print(f"Dashboard written to: {OUTPUT}")
