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
MAX_STARS = 10000  # Don't want repos this big
MIN_STARS = 100    # Need some traction
GROWTH_WINDOW_MONTHS = 6  # Look at growth over last 6 months

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
            
            # Calculate growth metrics
            created_at = datetime.strptime(data['created_at'], '%Y-%m-%dT%H:%M:%SZ')
            age_months = max(1, (datetime.now() - created_at).days / 30)
            stars = data.get('stargazers_count', 0)
            
            # Stars per month (overall)
            stars_per_month = stars / age_months
            
            # Get star history from GitHub API
            star_history = get_star_history(repo_full_name)
            
            return {
                'full_name': repo_full_name,
                'stars': stars,
                'description': data.get('description', ''),
                'language': data.get('language', 'Unknown'),
                'owner': data['owner']['login'],
                'created_at': data['created_at'],
                'age_months': age_months,
                'stars_per_month': stars_per_month,
                'star_history': star_history,
                'url': data.get('html_url', '')
            }
    except:
        return None
    return None

def get_star_history(repo_full_name: str) -> Dict:
    """Get star count over time using GitHub's stars timeline"""
    # GitHub doesn't have a direct API for star history
    # We'll use the stargazers timeline API
    url = f"https://api.github.com/repos/{repo_full_name}/stargazers"
    params = {"per_page": 100, "page": 1}
    
    try:
        # Get first page to get total count and timeline
        response = requests.get(url, headers=HEADERS, params=params)
        
        if response.status_code == 200:
            # Get timestamps of recent stars
            stars_data = response.json()
            recent_stars = []
            
            for star in stars_data[:20]:  # Get last 20 stars
                if 'starred_at' in star:
                    recent_stars.append(star['starred_at'])
            
            if recent_stars:
                # Calculate recent growth (last 3 months)
                three_months_ago = datetime.now() - timedelta(days=90)
                recent_count = sum(1 for s in recent_stars 
                                  if datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ') > three_months_ago)
                
                return {
                    'recent_stars_3m': recent_count,
                    'has_data': True
                }
    except:
        pass
    
    return {'recent_stars_3m': 0, 'has_data': False}

def calculate_growth_score(repo_details: Dict) -> float:
    """Calculate growth velocity score"""
    stars = repo_details['stars']
    
    # Penalize if too big
    if stars > MAX_STARS:
        return 0
    
    # Base score on stars per month
    stars_per_month = repo_details['stars_per_month']
    
    # Bonus for recent activity
    recent_bonus = 1.0
    if repo_details['star_history'].get('has_data'):
        recent_stars = repo_details['star_history']['recent_stars_3m']
        if recent_stars > 10:
            recent_bonus = min(2.0, 1 + (recent_stars / 100))
    
    # Growth score (higher is better for emerging repos)
    # We want repos with good momentum but not too big
    growth_score = stars_per_month * recent_bonus
    
    # Bonus for newer repos
    age_months = repo_details['age_months']
    if age_months < 6:
        growth_score *= 1.5
    elif age_months < 12:
        growth_score *= 1.2
    
    return growth_score

def find_emerging_repos(influencers_file: str, target_count: int = 100):
    """Find emerging repos from influencers"""
    
    with open(influencers_file, 'r') as f:
        influencers = json.load(f)
    
    print(f"🚀 Scanning {len(influencers)} influencers for EMERGING repos...")
    print(f"🎯 Target: Repos with <{MAX_STARS} stars but high growth")
    print("=" * 80)
    
    repo_candidates = {}
    influencers_processed = 0

    for idx, influencer in enumerate(influencers[:250], 1):  # Start with 50 influencers
        username = influencer['username']
        print(f"\n{idx}/{len(influencers[:250])} 👤 @{username} (Followers: {influencer['followers']})")
        influencers_processed += 1
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
            if repo_full_name in repo_candidates:
                repos_with_growth.append(repo_candidates[repo_full_name])
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
            repos_with_growth.append(repo_data)
            
            print(f"   📈 {repo_full_name} - {details['stars']} stars | "
                  f"{details['stars_per_month']:.1f} stars/month | "
                  f"Growth Score: {growth_score:.2f}")
        
        time.sleep(0.5)
    
    print("these are the influencers processed")
    print(influencers_processed)
    # Convert to list and sort by growth score
    all_repos = list(repo_candidates.values())
    all_repos.sort(key=lambda x: x['growth_score'], reverse=True)
    
    # Take top N
    print("these are the repos we got and its length")
    print(len(all_repos))
    # top_emerging = all_repos[:target_count]
    top_emerging = all_repos
    
    return top_emerging

def generate_emerging_report(emerging_repos: List[Dict], output_file: str = 'emerging_leads3.json'):
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
    print("🚀 GitHub EMERGING Repo Tracker")
    print("=" * 80)
    print(f"🎯 Finding repos with <{MAX_STARS} stars but HIGH GROWTH")
    print(f"📊 Looking at last {GROWTH_WINDOW_MONTHS} months of activity")
    print()
    
    # Find emerging repos
    emerging = find_emerging_repos("influencers1.json", target_count=250)
    
    if not emerging:
        print("❌ No emerging repos found! Try adjusting thresholds.")
        return
    
    # Generate report
    leads = generate_emerging_report(emerging, "emerging_leads3.json")
    
    print("\n🎯 Ready to reach out to owners of GROWING projects!")

if __name__ == "__main__":
    main()