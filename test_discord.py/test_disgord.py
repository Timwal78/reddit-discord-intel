import os
import requests

# Get your webhook from environment (Render → Environment)
WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# You can also paste it directly for a quick test (remove after testing)
# WEBHOOK = "https://discord.com/api/webhooks/xxxx/yyyy"

if not WEBHOOK:
    print("❌ No webhook found. Add DISCORD_WEBHOOK in your Render environment settings.")
else:
    data = {
        "content": "✅ **Discord Webhook Test Successful!** — Render and Bot connection verified 🚀"
    }
    response = requests.post(WEBHOOK, json=data)
    if response.status_code == 204:
        print("✅ Webhook test succeeded — check your Discord channel.")
    else:
        print(f"⚠️ Webhook test failed — status: {response.status_code}")
        print(response.text)
