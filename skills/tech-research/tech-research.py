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

MAX_MSG_LEN = 4000  # Telegram message limit
MAX_ARTICLE_SUMMARY = 150  # Max chars per article summary
MAX_ARTICLES_PER_CAT = 4  # Reduce to keep message short


def search_brave(query, count=10):
    """Search using Brave Search API"""
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
    """Send message to Telegram (handles long messages by splitting)"""
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"

    # If message is too long, split it
    if len(message) > MAX_MSG_LEN:
        # Find a good split point (by category)
        parts = message.split("━━━━━━━━━━━━━━━")
        current = ""
        for part in parts:
            if len(current) + len(part) > MAX_MSG_LEN - 100:
                # Send current batch
                send_single(current)
                current = part
            else:
                current += "━━━━━━━━━━━━━━━" + part
        if current.strip():
            send_single(current)
    else:
        send_single(message)


def send_single(data):
    """Send single message to Telegram"""
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = json.dumps(
        {"chat_id": TG_CHAT_ID, "text": data, "parse_mode": "HTML"}
    ).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read())
            if result.get("ok"):
                print(f"  ✅ Sent ({len(data)} chars)")
            else:
                print(f"  ❌ Error: {result.get('description')}")
            return result
    except Exception as e:
        print(f"  ❌ Send error: {e}")
        return {"ok": False}


def clean_html_text(text):
    """Remove HTML tags from text"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
    )
    text = " ".join(text.split())
    return text.strip()


def create_summary(title, description, max_len=MAX_ARTICLE_SUMMARY):
    """Create a meaningful summary from article description"""
    if not description:
        return ""

    # Clean HTML
    text = clean_html_text(description)

    if len(text) < 20:
        return ""

    # Get first 1-2 complete sentences
    sentences = re.split(r"(?<=[。！？.!?])[\s]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return text[:max_len] + "..." if len(text) > max_len else text

    # First sentence
    summary = sentences[0]

    # Add second sentence if short and fits
    if len(sentences) > 1 and len(summary) + len(sentences[1]) < max_len + 50:
        summary += " " + sentences[1][:100]

    # Truncate if still too long
    if len(summary) > max_len:
        # Find last sentence boundary
        for punct in ["。", "！", "？", ".", "!", "?"]:
            last_punct = summary.rfind(punct)
            if last_punct > max_len * 0.5:
                summary = summary[: last_punct + 1]
                break
        else:
            summary = summary[:max_len].rstrip() + "..."

    return summary if summary else text[:max_len]


def is_valid_article(url, title, description):
    """Check if this is a valid article with content"""
    skip_patterns = [
        "/tag/",
        "/topic/",
        "/section/",
        "/category/",
        "/archive",
        "/latest",
        "/home",
        "/search",
        "/cms/",
    ]
    for p in skip_patterns:
        if p in url.lower():
            return False
    if len(title) < 15:
        return False
    if not description or len(description) < 30:
        return False
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

    # Create meaningful summary
    summary = create_summary(title, description)

    return {"title": title, "url": url, "summary": summary}


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
            "min_count": 3,
        },
        "asia": {
            "title": "🌏 ASIA TECH NEWS",
            "queries": [
                "Asia technology AI startup news today 2026",
                "Japan Korea Singapore AI tech investment funding today",
            ],
            "min_count": 3,
        },
        "china": {
            "title": "🇨🇳 CHINA TECH NEWS",
            "queries": ["中国科技 市场 新闻 今天 2026", "中国科技公司 AI 动态 今天"],
            "min_count": 3,
        },
        "hk": {
            "title": "🇭🇰 HK TECH NEWS",
            "queries": [
                "site:hk01.com 科技 AI 新闻 今天",
                "site:hket.com 科技 新闻 今天",
                "site:unwire.hk 科技 新闻 今天",
            ],
            "min_count": 3,
        },
    }

    skip_patterns = [
        "job",
        "career",
        "hiring",
        "press release",
        "sponsored",
        "advertisement",
        "recruitment",
        "job opening",
        "salary",
        "vacancy",
    ]
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

        all_articles[cat_key] = articles_collected[:MAX_ARTICLES_PER_CAT]
        print(f"  → {len(all_articles[cat_key])} articles for {cat_key}")

    total_count = sum(len(articles) for articles in all_articles.values())
    print(f"📰 Total: {total_count} articles")

    date_str = datetime.now().strftime("%Y年%m月%d日")

    # Format and send messages
    header = f"🔬 科技新聞精選 - {date_str}\n"
    header += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    header += f"📰 今日精選 {total_count} 篇\n"

    # Send header first
    send_single(header)

    for cat_key, cat_info in categories.items():
        articles = all_articles[cat_key]
        if articles:
            category_header = f"\n{cat_info['title']}\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            send_single(category_header)

            for i, article in enumerate(articles, 1):
                msg = f"{i}. {article['title']}\n"
                msg += f"   📝 {article['summary']}\n"
                msg += f"   🔗 {article['url']}\n"
                send_single(msg)

    send_single("\n━━━━━━━━━━━━━━━━━━━━━━━\n💡 保持資訊靈通！")
    print("🔬 Tech Research done")


if __name__ == "__main__":
    main()
