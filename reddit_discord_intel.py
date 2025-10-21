# ========================= BEASTMODE ALERTS =========================
# Reddit → Discord intel bot (v2)
# - Active window: 4:00–20:00 America/New_York, Sun–Fri
# - Duplicate-proof via seen_posts.json
# - 5-minute scan cadence
# - Render-ready (uses env vars), falls back to constants
# ====================================================================

import os, json, time, requests, praw
from datetime import datetime, time as dtime
try:
    from zoneinfo import ZoneInfo  # Py3.9+
except ImportError:
    from backports.zoneinfo import ZoneInfo  # if running older Python locally

# -----------------------------
# CONFIG — credentials
# Prefer ENV (Render), fallback to inline constants if present.
# -----------------------------
REDDIT_CLIENT_ID     = os.getenv("REDDIT_CLIENT_ID", "i_gdxTj8WF7a7e2zoUtxfQ")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "0J14dAPQMS6lGVHIq1N10JZEQOobIg")
DISCORD_WEBHOOK_URL  = os.getenv("https://canary.discord.com/api/webhooks/1425603461826875435/aQBVUMfvza2qjuMaOJhSS3zTuC7mwJsreTlr_TfkUlQLzHt2gmc_noGlGadRUvrqJjGm", "YOUR_DISCORD_WEBHOOK_URL")
USER_AGENT           = os.getenv("USER_AGENT", "AIMe_DiscordIntelBot/2.0 BEASTMODE")

# -----------------------------
# CONFIG — scanning
# -----------------------------
SUBREDDITS = [
    "stocks",
    "options",
    "options_trading",   # extra options community
    "thetagang",         # options crowd
    "investing",
    "pennystocks",
    "shortsqueeze",
    "superstonk",
    "trading",
]

KEYWORDS = [
    # Core tickers / ETFs
    "tsla", "spy", "iwm", "qqq", "amc", "gme", "gme/w", "xlk",
    # Catalysts / flow
    "short squeeze", "gamma ramp", "earnings", "breakout",
    "momentum", "volume spike", "insider buying", "options flow",
    "unusual options activity", "bullish flow", "buyback",
    "sec filing", "catalyst", "fda approval", "analyst upgrade",
    "ai stocks", "undervalued", "reversal", "gap up"
]

SCAN_INTERVAL_SEC = 300  # 5 minutes
SEEN_FILE = "seen_posts.json"
TZ = ZoneInfo("America/New_York")

# -----------------------------
# Helpers — time window control
# -----------------------------
def in_active_window_now() -> bool:
    """Active Sun–Fri, 04:00–20:00 ET. Saturday off."""
    now = datetime.now(TZ)
    wd = now.weekday()  # Mon=0 ... Sun=6
    # Active days: Sun(6) and Mon–Fri(0–4). Saturday (5) is off.
    active_day = wd in {6, 0, 1, 2, 3, 4}
    start = dtime(4, 0)   # 04:00
    end   = dtime(20, 0)  # 20:00
    active_time = start <= now.time() <= end
    return active_day and active_time

def seconds_until_next_window() -> int:
    """Rough sleep guidance when outside window (wake up to check again)."""
    now = datetime.now(TZ)
    # If before 4am on an active day → wait until 4am today
    start_today = datetime(now.year, now.month, now.day, 4, 0, tzinfo=TZ)
    if now <= start_today and datetime.now(TZ).weekday() in {6, 0, 1, 2, 3, 4}:
        return max(60, int((start_today - now).total_seconds()))
    # Else sleep a conservative chunk (15 min), we'll re-check window on wake
    return 900

# -----------------------------
# Seen-post persistence
# -----------------------------
def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen(ids):
    try:
        with open(SEEN_FILE, "w") as f:
            json.dump(list(ids), f)
    except Exception:
        pass

# -----------------------------
# Discord sender
# -----------------------------
def send_embed_to_discord(title: str, url: str, subreddit: str):
    embed = {
        "embeds": [{
            "title": f"📢 BEASTMODE ALERTS",
            "description": f"**{title}**\n\n• Subreddit: **r/{subreddit}**",
            "url": url,
            "color": 16711680,  # red-ish
            "footer": {
                "text": datetime.now(TZ).strftime("⏰ %Y-%m-%d %I:%M %p ET")
            }
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=embed, timeout=10)
        print(f"✅ Sent: {title[:90]}...")
    except Exception as e:
        print(f⚠️ Discord send error: {e}")

# -----------------------------
# Reddit client
# -----------------------------
def make_reddit():
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=USER_AGENT,
        # PRAW will use read-only mode by default with client creds
    )

# -----------------------------
# Main scanning loop
# -----------------------------
def main():
    if DISCORD_WEBHOOK_URL == "YOUR_DISCORD_WEBHOOK_URL":
        print("⚠️ Set DISCORD_WEBHOOK_URL env var or inline constant before running.")
    reddit = make_reddit()
    seen = load_seen()
    print("🚀 BEASTMODE scanner online. Window: 4:00–20:00 ET, Sun–Fri.")

    while True:
        try:
            if not in_active_window_now():
                print("💤 Outside active window — sleeping until next window check...")
                time.sleep(seconds_until_next_window())
                continue

            for sub in SUBREDDITS:
                print(f"🔎 Scanning r/{sub} ...")
                subreddit = reddit.subreddit(sub)
                for post in subreddit.new(limit=8):
                    if post.id in seen:
                        continue
                    title = post.title or ""
                    lower = title.lower()
                    if any(k in lower for k in KEYWORDS):
                        url = f"https://www.reddit.com{post.permalink}"
                        send_embed_to_discord(title, url, sub)
                    seen.add(post.id)
            save_seen(seen)

            print(f"⏳ Sleeping {SCAN_INTERVAL_SEC//60} min...")
            time.sleep(SCAN_INTERVAL_SEC)

        except Exception as e:
            print(f"💥 Error: {e} — retrying in 60s")
            time.sleep(60)

# -----------------------------
if __name__ == "__main__":
    main()




