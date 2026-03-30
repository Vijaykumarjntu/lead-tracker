import json
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration - Add your webhook URLs here or in .env file
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')

# How many leads to send at once (to avoid spam)
SEND_LIMIT = 10

def load_leads(filename: str = 'emerging_leads.json'):
    """Load leads from JSON file"""
    try:
        with open(filename, 'r') as f:
            leads = json.load(f)
        print(f"✅ Loaded {len(leads)} leads from {filename}")
        return leads
    except FileNotFoundError:
        print(f"❌ File {filename} not found!")
        return []
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in {filename}")
        return []

def send_to_slack(leads, webhook_url):
    """Send leads to Slack channel"""
    if not webhook_url:
        print("⚠️ No Slack webhook URL configured")
        return False
    
    for lead in leads[:SEND_LIMIT]:
        # Format message for Slack
        message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🎯 HIGH-VALUE LEAD #{lead['rank']}",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Repository:*\n<{lead['repo_url']}|{lead['repo']}>"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Owner:*\n@{lead['owner']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Stars:*\n⭐ {lead['stars']:,}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Growth:*\n📈 {lead['stars_per_month']:.1f} stars/month"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Starred by:*\n@{lead['influencer']} ({lead['influencer_followers']:,} followers)"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Age:*\n🎂 {lead['age_months']:.1f} months"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Description:*\n{lead['description'][:200]}"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*💡 AI Sales Pitch:*\n{lead['sales_pitch']}"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"🚀 Ready for outreach | Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                }
            ]
        }
        
        try:
            response = requests.post(webhook_url, json=message)
            if response.status_code == 200:
                print(f"✅ Sent lead #{lead['rank']} to Slack")
            else:
                print(f"❌ Failed to send lead #{lead['rank']}: {response.status_code}")
        except Exception as e:
            print(f"❌ Error sending to Slack: {e}")
        
        time.sleep(1)  # Rate limiting
    
    return True

def send_to_discord(leads, webhook_url):
    """Send leads to Discord channel"""
    if not webhook_url:
        print("⚠️ No Discord webhook URL configured")
        return False
    
    for lead in leads[:SEND_LIMIT]:
        # Format message for Discord
        message = {
            "content": None,
            "embeds": [
                {
                    "title": f"🎯 HIGH-VALUE LEAD #{lead['rank']}: {lead['repo']}",
                    "url": lead['repo_url'],
                    "color": 5814783,  # GitHub purple-ish
                    "fields": [
                        {
                            "name": "📦 Repository",
                            "value": f"[{lead['repo']}]({lead['repo_url']})",
                            "inline": True
                        },
                        {
                            "name": "👤 Owner",
                            "value": f"@{lead['owner']}",
                            "inline": True
                        },
                        {
                            "name": "⭐ Stars",
                            "value": f"{lead['stars']:,}",
                            "inline": True
                        },
                        {
                            "name": "📈 Growth Rate",
                            "value": f"{lead['stars_per_month']:.1f} stars/month",
                            "inline": True
                        },
                        {
                            "name": "🎭 Starred by",
                            "value": f"@{lead['influencer']} ({lead['influencer_followers']:,} followers)",
                            "inline": True
                        },
                        {
                            "name": "🎂 Age",
                            "value": f"{lead['age_months']:.1f} months",
                            "inline": True
                        },
                        {
                            "name": "📝 Description",
                            "value": lead['description'][:200] + ("..." if len(lead['description']) > 200 else ""),
                            "inline": False
                        },
                        {
                            "name": "💡 AI Sales Pitch",
                            "value": lead['sales_pitch'][:1000],
                            "inline": False
                        }
                    ],
                    "footer": {
                        "text": f"🚀 Ready for outreach | Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    },
                    "timestamp": datetime.now().isoformat()
                }
            ]
        }
        
        try:
            response = requests.post(webhook_url, json=message)
            if response.status_code == 204 or response.status_code == 200:
                print(f"✅ Sent lead #{lead['rank']} to Discord")
            else:
                print(f"❌ Failed to send lead #{lead['rank']}: {response.status_code}")
        except Exception as e:
            print(f"❌ Error sending to Discord: {e}")
        
        time.sleep(1)  # Rate limiting
    
    return True

def send_simple_message(leads, webhook_url, platform="slack"):
    """Simple text-based message (if fancy formatting fails)"""
    for lead in leads[:SEND_LIMIT]:
        message = f"""
🎯 HIGH-VALUE LEAD #{lead['rank']}

📦 Repo: {lead['repo']}
👤 Owner: @{lead['owner']}
⭐ Stars: {lead['stars']:,}
📈 Growth: {lead['stars_per_month']:.1f} stars/month
🎭 Starred by: @{lead['influencer']} ({lead['influencer_followers']:,} followers)
📝 Description: {lead['description'][:150]}

💡 PITCH:
{lead['sales_pitch']}

🔗 URL: {lead['repo_url']}
        """
        
        payload = {"text": message} if platform == "slack" else {"content": message}
        
        try:
            response = requests.post(webhook_url, json=payload)
            if response.status_code in [200, 204]:
                print(f"✅ Sent lead #{lead['rank']} to {platform}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        time.sleep(1)

def main():
    print("🚀 Sending leads to Slack/Discord...")
    print("=" * 60)
    
    # Load leads
    leads = load_leads('emerging_leads.json')
    
    if not leads:
        print("❌ No leads to send!")
        return
    
    # Ask user which platform to use
    print(f"\n📤 Ready to send {min(len(leads), SEND_LIMIT)} leads")
    
    # Send to Slack
    if SLACK_WEBHOOK_URL:
        print("\n📨 Sending to Slack...")
        send_to_slack(leads, SLACK_WEBHOOK_URL)
    else:
        print("\n⚠️ Slack not configured. Add SLACK_WEBHOOK_URL to .env")
    
    # Send to Discord
    if DISCORD_WEBHOOK_URL:
        print("\n📨 Sending to Discord...")
        send_to_discord(leads, DISCORD_WEBHOOK_URL)
    else:
        print("\n⚠️ Discord not configured. Add DISCORD_WEBHOOK_URL to .env")
    
    print("\n✅ Done!")

if __name__ == "__main__":
    import time
    main()