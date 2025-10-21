# 🚀 AIMe Reddit → Discord Intel Suite (Final v1)
# Full optimized, auto-filtered, duplicate-protected version
# Paste into reddit_discord_intel.py

import praw
import requests
import time
import json
import os
from datetime import datetime

# ==============================
# Reddit API credentials
# ==============================
REDDIT_CLIENT_ID     = "i_gdxTj8WF7a7e2zoUtxfQ"
REDDIT_CLIENT_SECRET = "0J14dAPQMS6lGVHIq1N10JZEQOobIg"
USER_AGENT           = "AIMe_DiscordIntelBot/1.0"

# ==============================
# Discord webhook
# ==============================
DISCORD_WEBHOOK_URL = "https://canary.discord.com/api/webhooks/1425603461826875435/aQBVUMfvza2qjuMaOJhSS3zTuC7mwJsreTlr_TfkUlQLzHt2gmc_noGlGadRUvrqJjGm"

# ==============================
# Subreddits + Keywords
# ==============================
SUBREDDITS = [
    "stocks", "options", "investing", "pennystocks",
    "wallstreetbets", "shortsqueeze", "StockMarket"
]

KEYWORDS = [
    "insider", "buying", "calls", "puts", "squeeze",
    "catalyst", "earnings", "acquisition", "breakout",
    "momentum", "upgrade", "volume", "options flow",
    "short interest", "sec filing", "buyback"
]

# ==============================
# Core setup
# ==============================
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=USER_AGENT
)

SCAN_INTERVAL = 300  # 5 minutes
SEEN_FILE = "seen_posts.json"

# ==============================
# Load & Save Seen IDs
# ==============================
def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_seen(ids):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(ids), f)

# ==============================
# Discord Send Function
# ==============================
def send_to_discord(title, url, sub):
    embed = {
        "embeds": [{
            "title": title,
            "url": url,
            "description": f"📈 New Intel from **r/{sub}**",
            "color": 16776960,  # yellow-gold
            "footer": {"text": f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"}
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=embed, timeout=10)
    except Exception as e:
        print(f"⚠️ Discord send error: {e}")

# ==============================
# Scan Logic
# ==============================
def main():
    print("🚀 AIMe Reddit Intel Scanner started.")
    seen = load_seen()

    while True:
        try:
            for sub in SUBREDDITS:
                print(f"\n🔎 Scanning r/{sub} ...")
                subreddit = reddit.subreddit(sub)
                for post in subreddit.new(limit=8):
                    if post.id not in seen:
                        title_lower = post.title.lower()
                        if any(k in title_lower for k in KEYWORDS):
                            send_to_discord(post.title, f"https://www.reddit.com{post.permalink}", sub)
                            print(f"✅ Sent to Discord: {post.title[:80]}...")
                        seen.add(post.id)

            save_seen(seen)
            print("\n⏳ Waiting 5 minutes before next cycle ...")
            time.sleep(SCAN_INTERVAL)

        except Exception as e:
            print(f"💥 Error: {e}")
            time.sleep(60)  # wait 1 minute before retry

# ==============================
# Run
# ==============================
if __name__ == "__main__":
    main()



