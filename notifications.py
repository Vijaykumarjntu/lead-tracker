import json
import requests
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')
SEND_LIMIT = 10

def safe_text(value, max_length=None):
    """Safely convert None to empty string and truncate if needed"""
    if value is None:
        return ""
    text = str(value)
    if max_length:
        return text[:max_length] + ("..." if len(text) > max_length else "")
    return text

def load_leads(filename='emerging_leads.json'):
    """Load leads from JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            leads = json.load(f)
        print(f"✅ Loaded {len(leads)} leads from {filename}")
        
        # Sanitize leads
        for lead in leads:
            lead['description'] = safe_text(lead.get('description'), 200)
            lead['sales_pitch'] = safe_text(lead.get('sales_pitch'), 500)
            lead['owner'] = safe_text(lead.get('owner'))
            lead['repo'] = safe_text(lead.get('repo'))
            lead['influencer'] = safe_text(lead.get('influencer'))
        
        return leads
    except FileNotFoundError:
        print(f"❌ File {filename} not found!")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {filename}: {e}")
        return []
    except Exception as e:
        print(f"❌ Error loading leads: {e}")
        return []

def send_to_discord(leads, webhook_url):
    """Send leads to Discord channel"""
    if not webhook_url:
        print("⚠️ No Discord webhook URL configured")
        return False
    
    if not leads:
        print("⚠️ No leads to send")
        return False
    
    sent_count = 0
    
    for lead in leads[:SEND_LIMIT]:
        try:
            # Safely get values
            rank = lead.get('rank', 'N/A')
            repo = safe_text(lead.get('repo'))
            repo_url = safe_text(lead.get('repo_url'))
            owner = safe_text(lead.get('owner'))
            stars = lead.get('stars', 0)
            stars_per_month = lead.get('stars_per_month', 0)
            influencer = safe_text(lead.get('influencer'))
            influencer_followers = lead.get('influencer_followers', 0)
            description = safe_text(lead.get('description'), 200)
            sales_pitch = safe_text(lead.get('sales_pitch'), 800)
            
            # Format message for Discord
            message = {
                "content": None,
                "embeds": [
                    {
                        "title": f"🎯 HIGH-VALUE LEAD #{rank}: {repo}",
                        "url": repo_url if repo_url else None,
                        "color": 5814783,
                        "fields": [
                            {
                                "name": "📦 Repository",
                                "value": f"[{repo}]({repo_url})" if repo_url else repo,
                                "inline": True
                            },
                            {
                                "name": "👤 Owner",
                                "value": f"@{owner}" if owner else "Unknown",
                                "inline": True
                            },
                            {
                                "name": "⭐ Stars",
                                "value": f"{stars:,}" if stars else "0",
                                "inline": True
                            },
                            {
                                "name": "📈 Growth Rate",
                                "value": f"{stars_per_month:.1f} stars/month" if stars_per_month else "N/A",
                                "inline": True
                            },
                            {
                                "name": "🎭 Starred by",
                                "value": f"@{influencer} ({influencer_followers:,} followers)" if influencer else "Unknown",
                                "inline": True
                            },
                            {
                                "name": "📝 Description",
                                "value": description if description else "No description",
                                "inline": False
                            },
                            {
                                "name": "💡 AI Sales Pitch",
                                "value": sales_pitch if sales_pitch else "Generate pitch manually",
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
            
            # Remove None values
            if not repo_url:
                message["embeds"][0]["url"] = None
            
            response = requests.post(webhook_url, json=message)
            if response.status_code in [200, 204]:
                print(f"✅ Sent lead #{rank} to Discord")
                sent_count += 1
            else:
                print(f"❌ Failed to send lead #{rank}: {response.status_code}")
                print(f"   Response: {response.text[:100]}")
            
            time.sleep(1)  # Rate limiting
            
        except Exception as e:
            print(f"❌ Error sending lead #{lead.get('rank', '?')}: {e}")
            continue
    
    print(f"\n📊 Sent {sent_count} leads to Discord")
    return sent_count > 0

def send_to_slack(leads, webhook_url):
    """Send leads to Slack channel"""
    if not webhook_url:
        print("⚠️ No Slack webhook URL configured")
        return False
    
    if not leads:
        print("⚠️ No leads to send")
        return False
    
    sent_count = 0
    
    for lead in leads[:SEND_LIMIT]:
        try:
            # Safely get values
            rank = lead.get('rank', 'N/A')
            repo = safe_text(lead.get('repo'))
            repo_url = safe_text(lead.get('repo_url'))
            owner = safe_text(lead.get('owner'))
            stars = lead.get('stars', 0)
            stars_per_month = lead.get('stars_per_month', 0)
            influencer = safe_text(lead.get('influencer'))
            influencer_followers = lead.get('influencer_followers', 0)
            description = safe_text(lead.get('description'), 200)
            sales_pitch = safe_text(lead.get('sales_pitch'), 800)
            
            # Format message for Slack
            message = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"🎯 HIGH-VALUE LEAD #{rank}",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Repository:*\n<{repo_url}|{repo}>" if repo_url else f"*Repository:*\n{repo}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Owner:*\n@{owner}" if owner else "*Owner:*\nUnknown"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Stars:*\n⭐ {stars:,}" if stars else "*Stars:*\n0"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Growth:*\n📈 {stars_per_month:.1f} stars/month" if stars_per_month else "*Growth:*\nN/A"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Starred by:*\n@{influencer} ({influencer_followers:,} followers)" if influencer else "*Starred by:*\nUnknown"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Description:*\n{description}" if description else "*Description:*\nNo description"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*💡 AI Sales Pitch:*\n{sales_pitch}" if sales_pitch else "*💡 AI Sales Pitch:*\nGenerate pitch manually"
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
            
            response = requests.post(webhook_url, json=message)
            if response.status_code == 200:
                print(f"✅ Sent lead #{rank} to Slack")
                sent_count += 1
            else:
                print(f"❌ Failed to send lead #{rank}: {response.status_code}")
                print(f"   Response: {response.text[:100]}")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error sending lead #{lead.get('rank', '?')}: {e}")
            continue
    
    print(f"\n📊 Sent {sent_count} leads to Slack")
    return sent_count > 0

def send_simple_message(leads, webhook_url, platform="slack"):
    """Simple text-based message fallback"""
    if not webhook_url:
        return False
    
    sent_count = 0
    
    for lead in leads[:SEND_LIMIT]:
        try:
            rank = lead.get('rank', 'N/A')
            repo = safe_text(lead.get('repo'))
            owner = safe_text(lead.get('owner'))
            stars = lead.get('stars', 0)
            stars_per_month = lead.get('stars_per_month', 0)
            influencer = safe_text(lead.get('influencer'))
            description = safe_text(lead.get('description'), 150)
            sales_pitch = safe_text(lead.get('sales_pitch'), 300)
            
            message = f"""
🎯 HIGH-VALUE LEAD #{rank}

📦 Repo: {repo}
👤 Owner: @{owner}
⭐ Stars: {stars:,}
📈 Growth: {stars_per_month:.1f} stars/month
🎭 Starred by: @{influencer}
📝 Description: {description}

💡 PITCH:
{sales_pitch}

🔗 URL: {lead.get('repo_url', 'N/A')}
            """
            
            payload = {"text": message} if platform == "slack" else {"content": message}
            
            response = requests.post(webhook_url, json=payload)
            if response.status_code in [200, 204]:
                print(f"✅ Sent lead #{rank} to {platform}")
                sent_count += 1
            
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    
    return sent_count > 0

def main():
    print("🚀 Sending leads to Slack/Discord...")
    print("=" * 60)
    
    # Load leads
    leads = load_leads('emerging_leads.json')
    
    if not leads:
        print("❌ No leads to send!")
        return
    
    print(f"📊 Loaded {len(leads)} leads")
    print(f"📤 Will send first {min(len(leads), SEND_LIMIT)} leads\n")
    
    # Send to Discord
    if DISCORD_WEBHOOK_URL:
        print("📨 Sending to Discord...")
        success = send_to_discord(leads, DISCORD_WEBHOOK_URL)
        if not success:
            print("   Trying simple message format...")
            send_simple_message(leads, DISCORD_WEBHOOK_URL, "discord")
    else:
        print("⚠️ Discord not configured. Add DISCORD_WEBHOOK_URL to .env")
    
    print("\n" + "=" * 60)
    print("✅ Done!")

if __name__ == "__main__":
    main()