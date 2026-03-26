import requests
import time
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Set

# Configuration

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Database setup
DB_PATH = "star_history.db"

def init_db():
    """Initialize SQLite database to track seen stars"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seen_stars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            influencer TEXT,
            repo_full_name TEXT,
            starred_at TEXT,
            UNIQUE(influencer, repo_full_name)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerted_repos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_full_name TEXT,
            repo_owner TEXT,
            repo_description TEXT,
            influencer TEXT,
            alerted_at TEXT,
            UNIQUE(repo_full_name, influencer)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_seen_stars() -> Set[str]:
    """Get all already processed star events"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT influencer || ':' || repo_full_name FROM seen_stars")
    seen = {row[0] for row in cursor.fetchall()}
    conn.close()
    return seen

def mark_star_as_seen(influencer: str, repo_full_name: str, starred_at: str):
    """Mark a star event as processed"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO seen_stars (influencer, repo_full_name, starred_at) VALUES (?, ?, ?)",
        (influencer, repo_full_name, starred_at)
    )
    conn.commit()
    conn.close()

def get_user_starred_repos(username: str, since_date: str = None) -> List[Dict]:
    """Get repos starred by a user"""
    url = f"https://api.github.com/users/{username}/starred"
    params = {"per_page": 100, "sort": "created", "direction": "desc"}
    
    if since_date:
        params["since"] = since_date
    
    repos = []
    page = 1
    
    while True:
        params["page"] = page
        response = requests.get(url, headers=HEADERS, params=params)
        
        if response.status_code != 200:
            print(f"  Error fetching {username}: {response.status_code}")
            break
        
        data = response.json()
        if not data:
            break
            
        repos.extend(data)
        
        # Check if we've gone back far enough
        if since_date and len(data) > 0:
            last_starred = data[-1].get('starred_at', '')
            if last_starred < since_date:
                # Filter to only recent ones
                repos = [r for r in repos if r.get('starred_at', '') >= since_date]
                break
        
        page += 1
        time.sleep(0.2)
    
    return repos

def get_repo_details(repo_full_name: str) -> Dict:
    """Get detailed repository information"""
    url = f"https://api.github.com/repos/{repo_full_name}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        return response.json()
    return None

def get_user_details(username: str) -> Dict:
    """Get user profile for sales pitch"""
    url = f"https://api.github.com/users/{username}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        return response.json()
    return None

def generate_sales_pitch(repo_owner: Dict, repo: Dict, influencer: str) -> str:
    """Generate AI sales pitch (simplified for now, can integrate with real LLM)"""
    # For now, template-based pitch
    # Later you can replace with OpenAI/Anthropic API
    
    owner_name = repo_owner.get('name') or repo_owner.get('login')
    repo_name = repo.get('name')
    repo_desc = repo.get('description', '')[:100]
    influencer_followers = get_user_details(influencer).get('followers', 0)
    
    pitch = f"Hey {owner_name}! Your {repo_name} was just starred by {influencer} "
    pitch += f"(GitHub influencer with {influencer_followers}+ followers). "
    pitch += f"This signals your project is gaining traction! We help developers like you "
    pitch += f"amplify visibility through our network. Want to discuss exposure opportunities?"
    
    return pitch

def send_to_slack(message: str, webhook_url: str):
    """Send alert to Slack"""
    payload = {"text": message}
    response = requests.post(webhook_url, json=payload)
    return response.status_code == 200

def send_to_discord(message: str, webhook_url: str):
    """Send alert to Discord"""
    payload = {"content": message}
    response = requests.post(webhook_url, json=payload)
    return response.status_code == 204

def monitor_influencers(influencers_file: str, last_run_file: str = "last_run.json"):
    """Main monitoring function"""
    
    # Load influencers
    with open(influencers_file, 'r') as f:
        influencers = json.load(f)
    
    # Get last run time
    try:
        with open(last_run_file, 'r') as f:
            last_run = json.load(f)
            since_date = last_run.get('last_check', '')
    except:
        since_date = (datetime.now() - timedelta(hours=24)).isoformat()
    
    init_db()
    seen_stars = get_seen_stars()
    
    print(f"🔍 Monitoring {len(influencers)} influencers...")
    print(f"📅 Checking stars since: {since_date}")
    print("=" * 60)
    
    new_stars_found = []
    
    for influencer in influencers:
        username = influencer['username']
        print(f"\n👤 Checking {username} (Followers: {influencer['followers']})...")
        
        starred_repos = get_user_starred_repos(username, since_date)
        
        for repo in starred_repos:
            repo_full_name = repo.get('full_name')
            starred_at = repo.get('starred_at', '')
            
            star_key = f"{username}:{repo_full_name}"
            
            if star_key not in seen_stars:
                print(f"  ⭐ NEW STAR: {repo_full_name} at {starred_at}")
                
                # Get repo details
                repo_details = get_repo_details(repo_full_name)
                if not repo_details:
                    continue
                
                # Get repo owner details
                owner_username = repo_details['owner']['login']
                owner_details = get_user_details(owner_username)
                if not owner_details:
                    continue
                
                # Generate pitch
                pitch = generate_sales_pitch(owner_details, repo_details, username)
                
                new_star = {
                    'influencer': username,
                    'repo': repo_full_name,
                    'repo_owner': owner_username,
                    'repo_description': repo_details.get('description', ''),
                    'repo_stars': repo_details.get('stargazers_count', 0),
                    'starred_at': starred_at,
                    'pitch': pitch
                }
                
                new_stars_found.append(new_star)
                mark_star_as_seen(username, repo_full_name, starred_at)
                
                # For now, just print. Later send to Slack/Discord
                print(f"    📝 Pitch: {pitch}")
        
        time.sleep(1)  # Rate limiting
    
    # Save last run time
    with open(last_run_file, 'w') as f:
        json.dump({'last_check': datetime.now().isoformat()}, f)
    
    print("\n" + "=" * 60)
    print(f"📊 Summary: Found {len(new_stars_found)} new stars from {len(influencers)} influencers")
    
    return new_stars_found

def main():
    print("🚀 High-Value Lead Tracker - Monitoring Mode")
    print("=" * 60)
    
    # Monitor influencers
    new_stars = monitor_influencers("influencers.json")
    
    # If you have Slack/Discord webhooks, uncomment below
    # SLACK_WEBHOOK = "YOUR_SLACK_WEBHOOK_URL"
    # DISCORD_WEBHOOK = "YOUR_DISCORD_WEBHOOK_URL"
    
    for star in new_stars:
        message = f"""
🎯 **HIGH-VALUE LEAD ALERT**

**Repository:** {star['repo']}
**Owner:** @{star['repo_owner']}
**Influencer who starred:** @{star['influencer']}
**Description:** {star['repo_description']}

**AI Sales Pitch:**
{star['pitch']}

---
_Action: Send outreach to @{star['repo_owner']}_
        """
        
        print(message)
        
        # Send to Slack/Discord if configured
        # send_to_slack(message, SLACK_WEBHOOK)
        # send_to_discord(message, DISCORD_WEBHOOK)

if __name__ == "__main__":
    main()