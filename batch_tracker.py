import requests
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict
from collections import defaultdict
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Thresholds
MAX_STARS = 2500
MIN_STARS = 100
GROWTH_WINDOW_MONTHS = 6

# Checkpoint file
CHECKPOINT_FILE = 'tracking_checkpoint.json'

def load_checkpoint():
    """Load last processed influencer index"""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            checkpoint = json.load(f)
            print(f"✅ Resuming from influencer #{checkpoint['last_index'] + 1}")
            return checkpoint
    return {'last_index': -1, 'processed_repos': []}

def save_checkpoint(last_index, processed_repos):
    """Save current progress"""
    checkpoint = {
        'last_index': last_index,
        'processed_repos': processed_repos,
        'last_updated': datetime.now().isoformat()
    }
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    print(f"💾 Checkpoint saved at influencer #{last_index + 1}")

def get_recent_stars(username: str, limit: int = 20) -> List[Dict]:
    """Get last N repos starred by a user"""
    url = f"https://api.github.com/users/{username}/starred"
    params = {
        "per_page": limit,
        "sort": "created",
        "direction": "desc"
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def get_repo_full_details(repo_full_name: str) -> Dict:
    """Get repo details including creation date"""
    url = f"https://api.github.com/repos/{repo_full_name}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            created_at = datetime.strptime(data['created_at'], '%Y-%m-%dT%H:%M:%SZ')
            age_months = max(1, (datetime.now() - created_at).days / 30)
            stars = data.get('stargazers_count', 0)
            stars_per_month = stars / age_months
            
            return {
                'full_name': repo_full_name,
                'stars': stars,
                'description': data.get('description', ''),
                'language': data.get('language', 'Unknown'),
                'owner': data['owner']['login'],
                'created_at': data['created_at'],
                'age_months': age_months,
                'stars_per_month': stars_per_month,
                'url': data.get('html_url', '')
            }
    except:
        return None
    return None

def calculate_growth_score(repo_details: Dict) -> float:
    """Calculate growth velocity score"""
    stars = repo_details['stars']
    
    if stars > MAX_STARS:
        return 0
    
    stars_per_month = repo_details['stars_per_month']
    growth_score = stars_per_month
    
    age_months = repo_details['age_months']
    if age_months < 6:
        growth_score *= 1.5
    elif age_months < 12:
        growth_score *= 1.2
    
    return growth_score

def find_emerging_repos(influencers_file: str, target_count: int = 100, batch_size: int = 50):
    """Find emerging repos from influencers WITH CHECKPOINT RESUME"""
    
    with open(influencers_file, 'r') as f:
        influencers = json.load(f)
    
    # Load checkpoint
    checkpoint = load_checkpoint()
    start_index = checkpoint['last_index'] + 1
    processed_repos = set(checkpoint['processed_repos'])
    
    print(f"🚀 Scanning {len(influencers)} influencers for EMERGING repos...")
    print(f"🎯 Target: Repos with <{MAX_STARS} stars but high growth")
    print(f"📌 Resuming from influencer #{start_index + 1}")
    print("=" * 80)
    
    repo_candidates = {}
    # total_influencers = len(influencers[:240])  # Your limit
    total_influencers = len(influencers)  # Your limit
    failed_at = None
    
    for idx in range(start_index, min(start_index + batch_size, total_influencers)):
        influencer = influencers[idx]
        username = influencer['username']
        
        print(f"\n{idx + 1}/{total_influencers} 👤 @{username} (Followers: {influencer['followers']})")
        
        try:
            # Get recent stars
            recent_stars = get_recent_stars(username, limit=20)
            
            if not recent_stars:
                print(f"   ❌ No recent stars")
                continue
            
            # Filter out repos that are too big
            eligible_repos = []
            for repo in recent_stars:
                repo_stars = repo.get('stargazers_count', 0)
                if repo_stars < MAX_STARS and repo_stars > MIN_STARS:
                    eligible_repos.append(repo)
            
            print(f"   📁 Found {len(eligible_repos)} eligible repos (<{MAX_STARS} stars)")
            
            if not eligible_repos:
                continue
            
            # Get detailed info for each eligible repo
            repos_with_growth = []
            for repo in eligible_repos:
                repo_full_name = repo['full_name']
                
                # Skip if already processed
                if repo_full_name in processed_repos or repo_full_name in repo_candidates:
                    continue
                
                # Get full details
                details = get_repo_full_details(repo_full_name)
                if not details:
                    continue
                
                growth_score = calculate_growth_score(details)
                
                repo_data = {
                    'repo': repo_full_name,
                    'details': details,
                    'growth_score': growth_score,
                    'influencer': username,
                    'influencer_followers': influencer['followers'],
                    'starred_at': repo.get('starred_at', '')
                }
                
                repo_candidates[repo_full_name] = repo_data
                processed_repos.add(repo_full_name)
                repos_with_growth.append(repo_data)
                
                print(f"   📈 {repo_full_name} - {details['stars']} stars | "
                      f"{details['stars_per_month']:.1f} stars/month | "
                      f"Growth Score: {growth_score:.2f}")
            
            # SAVE CHECKPOINT after each successful influencer
            save_checkpoint(idx, list(processed_repos))
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ FAILED at {username}: {e}")
            failed_at = idx
            break
    
    print(f"\n📊 Processed {idx + 1 if not failed_at else failed_at} influencers")
    print(f"📦 Found {len(repo_candidates)} unique repos")
    
    if failed_at is not None:
        print(f"\n⚠️ Stopped at influencer #{failed_at + 1}")
        print(f"💡 Run script again to resume from checkpoint")
        return None
    
    # Convert to list and sort by growth score
    all_repos = list(repo_candidates.values())
    all_repos.sort(key=lambda x: x['growth_score'], reverse=True)
    
    top_emerging = all_repos[:target_count]
    
    # Clear checkpoint on successful completion
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        print("✅ Checkpoint cleared (batch complete)")
    
    return top_emerging

def generate_emerging_report(emerging_repos: List[Dict], output_file: str = 'emerging_leads_new.json'):
    """Generate report with sales pitches for emerging repos"""
    
    print("\n" + "=" * 80)
    print(f"🏆 TOP {len(emerging_repos)} EMERGING REPOSITORIES")
    print("=" * 80)
    
    leads = []
    
    for idx, repo_data in enumerate(emerging_repos, 1):
        details = repo_data['details']
        
        print(f"\n{idx}. 📦 {repo_data['repo']}")
        print(f"   ⭐ {details['stars']} total stars")
        print(f"   📈 {details['stars_per_month']:.1f} stars/month")
        print(f"   🎂 Age: {details['age_months']:.1f} months")
        print(f"   👤 Owner: @{details['owner']}")
        print(f"   🎭 Starred by: @{repo_data['influencer']} ({repo_data['influencer_followers']} followers)")
        
        # Generate pitch
        pitch = f"🎯 Hey @{details['owner']}! Your {details['full_name']} was just starred by "
        pitch += f"@{repo_data['influencer']} (influencer with {repo_data['influencer_followers']}+ followers). "
        pitch += f"Your project is gaining {details['stars_per_month']:.0f} new stars/month - "
        pitch += f"amazing growth! We help emerging open-source projects like yours get discovered by "
        pitch += f"more developers and potential sponsors. Would you be open to chatting about "
        pitch += f"growth opportunities?\n"
        if details['description']:
            pitch += f"\n📊 Context: {details['description'][:100]}"
        
        print(f"\n   💡 SALES PITCH:\n   {pitch}")
        
        leads.append({
            'rank': idx,
            'repo': repo_data['repo'],
            'owner': details['owner'],
            'stars': details['stars'],
            'stars_per_month': details['stars_per_month'],
            'age_months': details['age_months'],
            'growth_score': repo_data['growth_score'],
            'influencer': repo_data['influencer'],
            'influencer_followers': repo_data['influencer_followers'],
            'sales_pitch': pitch,
            'repo_url': details['url'],
            'description': details['description']
        })
    
    # Save to file
    with open(output_file, 'w') as f:
        json.dump(leads, f, indent=2)
    
    print("\n" + "=" * 80)
    print(f"✅ Generated {len(leads)} EMERGING leads!")
    print(f"💾 Saved to {output_file}")
    
    return leads

def main():
    print("🚀 GitHub EMERGING Repo Tracker (WITH CHECKPOINT RESUME)")
    print("=" * 80)
    print(f"🎯 Finding repos with <{MAX_STARS} stars but HIGH GROWTH")
    print(f"📊 Looking at last {GROWTH_WINDOW_MONTHS} months of activity")
    print()
    
    # Find emerging repos with checkpoint
    emerging = find_emerging_repos("influencers.json", target_count=125, batch_size=50)
    
    if emerging is None:
        print("\n⚠️ Batch incomplete. Run script again to resume from checkpoint.")
        return
    
    if not emerging:
        print("❌ No emerging repos found! Try adjusting thresholds.")
        return
    
    # Generate report
    leads = generate_emerging_report(emerging, "emerging_leads_new_batch.json")
    
    print("\n🎯 Ready to reach out to owners of GROWING projects!")

if __name__ == "__main__":
    main()