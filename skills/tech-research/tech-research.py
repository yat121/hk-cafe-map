#!/usr/bin/env python3
"""Tech Research - Daily tech news summary in 4 categories via Telegram & Email"""

import json
import urllib.request
import urllib.parse
import subprocess
import re
from datetime import datetime

# ===== CONFIGURATION =====
TG_BOT_TOKEN = "8652497348:AAGf16He0xuI80MymX0kJs1TRnqmLTRYnaE"
TG_CHAT_ID = "869229225"
BRAVE_API_KEY = "BSAq5fTPs04TDIgIugUUKhM9a7flGC9"
AGENTMAIL_API_KEY = (
    "am_us_d6254787478daa5b57ef92a0635fc4a80f8fbd5b68c42aec3fe3ec2d9daa19b6"
)
AGENTMAIL_INBOX = "alphaai_sales@agentmail.to"


def search_brave(query, count=10):
    """Search using Brave Search API - Daily news only"""
    # Add pd freshness for daily news
    url = f"https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote(query)}&count={count}&freshness=pd"

    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY},
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"Brave search error: {e}")
        return {"web": {"results": []}}


def send_telegram(message):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"

    if len(message) > 4000:
        message = message[:3950] + "\n\n... (內容已截斷)"

    data = json.dumps({"chat_id": TG_CHAT_ID, "text": message}).encode()

    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        print(f"Telegram HTTP Error {e.code}: {error_body[:500]}")
        raise


def send_email(subject, html_content):
    """Send email via AgentMail CLI"""
    html_escaped = html_content.replace('"', '\\"').replace("\n", " ").replace("\r", "")

    cmd = f"""agentmail message send --from {AGENTMAIL_INBOX} --to desmondho121@gmail.com --subject "{subject}" --html "{html_escaped}" --json"""

    result = subprocess.run(
        f'export AGENTMAIL_API_KEY="{AGENTMAIL_API_KEY}" && {cmd}',
        shell=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode == 0:
        try:
            return json.loads(result.stdout)
        except:
            return {"success": True}
    else:
        print(f"Email error: {result.stderr}")
        return {"success": False}


def clean_html_text(text):
    """Remove HTML tags from text"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = " ".join(text.split())
    return text.strip()


def clean_summary(content, max_len=300):
    """Clean and truncate content"""
    if not content:
        return ""
    content = clean_html_text(content)
    if len(content) < 20:
        return ""
    if len(content) > max_len:
        content = content[:max_len]
        for punct in ["。", "！", "？", ".", "!", "?"]:
            last_punct = content.rfind(punct)
            if last_punct > max_len * 0.5:
                content = content[: last_punct + 1]
                break
        else:
            content = content.rstrip() + "..."
    return content


def is_valid_article(url, title, description):
    """Check if this is a valid article with content"""
    # Skip landing pages / tag pages / section pages
    skip_patterns = [
        "/tag/",
        "/topic/",
        "/section/",
        "/category/",
        "/archive",
        "/latest",
        "/home",
        "/index",
        "/search",
        "/cms/",
    ]
    for p in skip_patterns:
        if p in url.lower():
            return False

    # Skip very short titles (usually site-generated headlines)
    if len(title) < 15:
        return False

    # Skip if description is missing or just site name
    if not description or len(description) < 30:
        return False

    # Skip if description is exactly the title (no real content)
    if description.strip().lower() == title.strip().lower():
        return False

    return True


def process_article(r, skip_patterns, seen_titles, seen_urls):
    """Process a single article result"""
    title = r.get("title", "").strip()
    url = r.get("url", "").strip()
    description = r.get("description", "")

    if not title or not url:
        return None

    if title.lower() in seen_titles or url.lower() in seen_urls:
        return None

    if any(p in title.lower() for p in skip_patterns):
        return None

    if not is_valid_article(url, title, description):
        return None

    content = clean_summary(description, max_len=300)

    # Format as 1-2 bullet taglines
    bullet = ""
    if content:
        # Take first sentence as bullet 1
        sentences = re.split(r"(?<=[。！？.!?])[\s]+", content)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            bullet = "• " + sentences[0]
            if len(sentences) > 1 and len(sentences[1]) > 5:
                bullet += "\n• " + sentences[1][:150]
        else:
            bullet = "• " + content[:200]
    else:
        bullet = "• 點擊查看全文"

    return {"title": title, "url": url, "content": bullet}


def main():
    print("🔬 Tech Research started")

    # Categories with search queries
    categories = {
        "global": {
            "title": "🌍 GLOBAL TECH NEWS",
            "queries": [
                "AI technology news today 2026",
                "tech industry news today",
                "software developer tools release today",
            ],
            "min_count": 5,
        },
        "asia": {
            "title": "🌏 ASIA TECH NEWS",
            "queries": [
                "Asia technology AI startup news today 2026",
                "Japan Korea Singapore AI tech investment funding today",
                "Asia Pacific technology company news today",
                "India Southeast Asia tech startup news today",
            ],
            "min_count": 5,
        },
        "china": {
            "title": "🇨🇳 CHINA TECH NEWS (中文)",
            "queries": [
                "中国科技 市场 新闻 今天 2026",
                "中国科技公司 AI 动态 今天",
                "中国科技创新 投资 今天",
            ],
            "min_count": 5,
        },
        "hk": {
            "title": "🇭🇰 香港科技新聞 (繁體)",
            "queries": [
                "site:hk01.com 科技 AI 新闻 今天 2026",
                "site:hket.com 科技 新闻 今天",
                "site:unwire.hk 科技 新闻 今天",
            ],
            "min_count": 5,
        },
    }

    # Skip patterns
    skip_patterns = [
        "job",
        "career",
        "hiring",
        "press release",
        "sponsored",
        "advertisement",
        "recruitment",
        "job opening",
        "apply now",
        "salary",
        "vacancy",
    ]

    # Skip government domains
    skip_domains = ["gov.hk", "news.gov.hk", "gov.cn", "rthk.hk"]

    seen_titles = set()
    seen_urls = set()

    all_articles = {cat: [] for cat in categories}

    for cat_key, cat_info in categories.items():
        print(f"🔍 Searching {cat_key}...")
        articles_collected = []

        for query in cat_info["queries"]:
            results = search_brave(query, count=15)

            for r in results.get("web", {}).get("results", []):
                article = process_article(r, skip_patterns, seen_titles, seen_urls)

                if article:
                    if any(domain in article["url"].lower() for domain in skip_domains):
                        continue

                    articles_collected.append(article)
                    seen_titles.add(article["title"].lower())
                    seen_urls.add(article["url"].lower())

        all_articles[cat_key] = articles_collected[: cat_info["min_count"]]
        print(f"  → {len(all_articles[cat_key])} articles for {cat_key}")

    total_count = sum(len(articles) for articles in all_articles.values())
    print(f"📰 Total: {total_count} articles")

    # Format messages
    date_str = datetime.now().strftime("%Y年%m月%d日")

    # ===== TELEGRAM =====
    telegram_parts = [f"🔬 科技新聞精選 - {date_str}\n"]
    telegram_parts.append("━━━━━━━━━━━━━━━━━━━━━━━\n")
    telegram_parts.append(f"📰 今日精選 {total_count} 篇\n")

    for cat_key, cat_info in categories.items():
        articles = all_articles[cat_key]
        if articles:
            telegram_parts.append(f"\n{cat_info['title']}\n")
            telegram_parts.append("━━━━━━━━━━━━━━━━━━━━━━━\n")
            for i, article in enumerate(articles, 1):
                telegram_parts.append(f"\n{i}. {article['title']}")
                telegram_parts.append(f"   {article['content']}")
                telegram_parts.append(f"   🔗 {article['url']}\n")

    telegram_parts.append("\n━━━━━━━━━━━━━━━━━━━━━━━\n")
    telegram_parts.append("💡 保持資訊靈通！")

    telegram_msg = "\n".join(telegram_parts)

    # ===== EMAIL HTML =====
    email_html = f"""<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto; padding: 20px;">
<h1 style="color: #1a73e8;">🔬 科技新聞精選</h1>
<p style="color: #666;">{date_str} | 每日 8:00 AM 自動推送</p>
<hr>
"""

    for cat_key, cat_info in categories.items():
        articles = all_articles[cat_key]
        if articles:
            email_html += f'<h2 style="color: #333;">{cat_info["title"]}</h2>\n'
            email_html += "<hr>\n"
            for i, article in enumerate(articles, 1):
                email_html += f"""
<div style="margin-bottom: 20px; padding: 15px; background: #f9f9f9; border-radius: 8px;">
<h3 style="margin: 0 0 10px 0; color: #1a73e8; font-size: 16px;">{i}. {article['title']}</h3>
<p style="margin: 0 0 10px 0; color: #555; line-height: 1.6; font-size: 14px;">{article['content']}</p>
<a href="{article['url']}" style="color: #1a73e8;">🔗 閱讀全文</a>
</div>
"""

    email_html += """<hr>
<p style="color: #999; font-size: 12px;">
由 VV 🤖 透過 OpenClaw 自動整理發送<br>
Sent by VV via OpenClaw
</p>
</body></html>"""

    # Send
    print("📤 Sending to Telegram...")
    result_tg = send_telegram(telegram_msg)
    if result_tg.get("ok"):
        print("✅ Telegram sent!")

    print("📧 Sending to Email...")
    email_subject = f"🔬 科技新聞精選 {date_str}"
    result_email = send_email(email_subject, email_html)
    if result_email and (result_email.get("success") or result_email.get("messageId")):
        print("✅ Email sent!")

    print("🔬 Tech Research done")


if __name__ == "__main__":
    main()
