#!/usr/bin/env python3
import os
import sys
import time
import json
import logging
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
import praw
import requests

# Configuration
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = os.getenv("USER_AGENT", "BeastModeBot/3.0")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

SUBREDDITS = ["stocks", "options", "options_trading", "thetagang","shortsqueeze", "superstonk", "trading", "wallstreetbets"]

# EXPANDED KEYWORDS - More tickers and terms!
KEYWORDS = [
    # Popular tickers
    "tsla", "spy", "iwm", "qqq", "amc", "gme", "nvda", "aapl", "msft", "xlk", "arkk", "pltr", "sofi", "coin",
    "meta", "amzn", "googl", "nflx", "ba", "dis", "baba", "nio", "lucid", "rivn", "f", "gm",
    "uber", "lyft", "snap", "hood", "shop", "sq", "pypl", "crm", "adbe", "orcl",
    "mu", "intc", "qcom", "mrna", "pfe", "jnj", "xom", "cvx", "mro", "oxy",
    # Squeeze/momentum terms
    "short squeeze", "gamma ramp", "gamma squeeze", "breakout", "momentum", "volume spike",
    "insider buying", "options flow", "unusual options activity", "dark pool", 
    "bullish flow", "bearish flow", "buyback", "squeeze", "yolo", "calls", "puts",
    # Catalyst terms
    "earnings beat", "earnings miss", "sec filing", "catalyst", "fda approval",
    "analyst upgrade", "analyst downgrade", "price target", "reversal",
    "gap up", "gap down", "pre-market", "after hours", "halt", "halted",
    # General interest
    "ai stocks", "undervalued", "oversold", "overbought", "moon", "rocket", "powerhour", 
]

SCAN_INTERVAL_SEC = 180  # 3 minutes
POSTS_PER_SUB = 25  # INCREASED from 150 to 25!
SEEN_FILE = "seen_posts.json"
MAX_SEEN_POSTS = 10000
TZ = ZoneInfo("America/New_York")
ACTIVE_START_HOUR = 4
ACTIVE_END_HOUR = 20
ACTIVE_DAYS = {6, 0, 1, 2, 3, 4}  # Sunday through Friday

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

def validate_config():
    missing = []
    if not REDDIT_CLIENT_ID:
        missing.append("REDDIT_CLIENT_ID")
    if not REDDIT_CLIENT_SECRET:
        missing.append("REDDIT_CLIENT_SECRET")
    if not DISCORD_WEBHOOK_URL:
        missing.append("DISCORD_WEBHOOK_URL")
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        return False
    return True

def in_active_window():
    now = datetime.now(TZ)
    weekday = now.weekday()
    current_time = now.time()
    active_day = weekday in ACTIVE_DAYS
    start_time = dtime(ACTIVE_START_HOUR, 0)
    end_time = dtime(ACTIVE_END_HOUR, 0)
    active_time = start_time <= current_time <= end_time
    return active_day and active_time

def seconds_until_next_window():
    now = datetime.now(TZ)
    start_today = datetime(now.year, now.month, now.day, ACTIVE_START_HOUR, 0, tzinfo=TZ)
    if now < start_today and now.weekday() in ACTIVE_DAYS:
        return max(60, int((start_today - now).total_seconds()))
    return 1800

def load_seen_posts():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                data = json.load(f)
                seen = set(data)
                logger.info(f"Loaded {len(seen)} previously seen posts")
                if len(seen) > MAX_SEEN_POSTS:
                    seen = set(list(seen)[-MAX_SEEN_POSTS:])
                    logger.info(f"Trimmed seen posts to {MAX_SEEN_POSTS}")
                return seen
        except Exception as e:
            logger.warning(f"Error loading seen posts: {e}")
            return set()
    return set()

def save_seen_posts(seen):
    try:
        recent_posts = list(seen)[-MAX_SEEN_POSTS:]
        with open(SEEN_FILE, "w") as f:
            json.dump(recent_posts, f)
    except Exception as e:
        logger.error(f"Error saving seen posts: {e}")

def send_discord_alert(title, url, subreddit):
    if len(title) > 200:
        title = title[:197] + "..."
    embed = {
        "embeds": [{
            "title": "🚨 BEASTMODE ALERT",
            "description": f"**{title}**",
            "url": url,
            "color": 15158332,
            "fields": [
                {"name": "📍 Subreddit", "value": f"r/{subreddit}", "inline": True},
                {"name": "🔗 Link", "value": f"[View Post]({url})", "inline": True}
            ],
            "footer": {"text": f"⏰ {datetime.now(TZ).strftime('%Y-%m-%d %I:%M %p ET')}"},
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=embed, timeout=10)
        if response.status_code == 204:
            logger.info(f"✅ Alert sent: {title[:80]}")
            return True
        else:
            logger.warning(f"Discord webhook returned status {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Discord alert: {e}")
        return False

def create_reddit_client():
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=USER_AGENT,
            check_for_updates=False,
            timeout=30
        )
        reddit.user.me()
        logger.info("✅ Reddit client authenticated successfully")
        return reddit
    except Exception as e:
        logger.error(f"Failed to create Reddit client: {e}")
        raise

def scan_subreddit(reddit, subreddit_name, seen):
    alerts_sent = 0
    try:
        subreddit = reddit.subreddit(subreddit_name)
        for post in subreddit.new(limit=POSTS_PER_SUB):
            if post.id in seen:
                continue
            seen.add(post.id)
            title = post.title or ""
            title_lower = title.lower()
            matching_keywords = [k for k in KEYWORDS if k in title_lower]
            if matching_keywords:
                url = f"https://www.reddit.com{post.permalink}"
                if send_discord_alert(title, url, subreddit_name):
                    alerts_sent += 1
                # REMOVED THE 5-ALERT LIMIT! Send all alerts found!
                time.sleep(2.5)
        return alerts_sent
    except Exception as e:
        logger.error(f"Error scanning r/{subreddit_name}: {e}")
        return 0

def main():
    logger.info("=" * 70)
    logger.info("🚀 BEASTMODE REDDIT-DISCORD INTELLIGENCE BOT v3.0 (LOOSENED)")
    logger.info("=" * 70)
    logger.info(f"Active Window: {ACTIVE_START_HOUR}:00 - {ACTIVE_END_HOUR}:00 ET (Sun-Fri)")
    logger.info(f"Scan Interval: {SCAN_INTERVAL_SEC} seconds ({SCAN_INTERVAL_SEC//60} minutes)")
    logger.info(f"Monitoring: {len(SUBREDDITS)} subreddits")
    logger.info(f"Tracking: {len(KEYWORDS)} keywords")
    logger.info(f"Posts per subreddit: {POSTS_PER_SUB} (INCREASED!)")
    logger.info(f"Alert limit: REMOVED (sends all matches!)")
    logger.info("=" * 70)
    
    if not validate_config():
        logger.error("❌ Configuration validation failed. Exiting.")
        sys.exit(1)
    
    try:
        reddit = create_reddit_client()
        seen = load_seen_posts()
        logger.info("✅ Initialization complete")
        logger.info("🔥 Bot is now ONLINE and monitoring...\n")
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        sys.exit(1)
    
    scan_count = 0
    total_alerts = 0
    
    while True:
        try:
            if not in_active_window():
                now_str = datetime.now(TZ).strftime("%I:%M %p ET on %A")
                logger.info(f"💤 Outside active window (current: {now_str})")
                sleep_time = seconds_until_next_window()
                logger.info(f"Sleeping for {sleep_time//60} minutes...")
                time.sleep(sleep_time)
                continue
            
            scan_count += 1
            scan_time = datetime.now(TZ).strftime("%I:%M %p ET")
            logger.info(f"\n{'='*70}")
            logger.info(f"🔍 SCAN #{scan_count} - {scan_time}")
            logger.info(f"{'='*70}")
            
            scan_alerts = 0
            for sub in SUBREDDITS:
                logger.info(f"Scanning r/{sub}...")
                alerts = scan_subreddit(reddit, sub, seen)
                scan_alerts += alerts
                time.sleep(2)
            
            save_seen_posts(seen)
            total_alerts += scan_alerts
            logger.info(f"\n{'='*70}")
            if scan_alerts > 0:
                logger.info(f"🔥 Scan complete: {scan_alerts} alert(s) sent!")
            else:
                logger.info(f"✓ Scan complete: No new alerts")
            logger.info(f"📊 Total alerts today: {total_alerts}")
            logger.info(f"💾 Tracking {len(seen)} seen posts")
            logger.info(f"⏳ Next scan in {SCAN_INTERVAL_SEC//60} minutes...")
            logger.info(f"{'='*70}\n")
            time.sleep(SCAN_INTERVAL_SEC)
        except KeyboardInterrupt:
            logger.info("\n\n👋 Bot stopped by user. Shutting down gracefully...")
            save_seen_posts(seen)
            break
        except Exception as e:
            logger.error(f"💥 Unexpected error in main loop: {e}")
            logger.info("⚠️ Attempting to recover in 60 seconds...")
            time.sleep(60)
            try:
                reddit = create_reddit_client()
                logger.info("✅ Reddit client reconnected")
            except:
                logger.error("❌ Failed to reconnect to Reddit")

if __name__ == "__main__":
    main()
