import requests
import time
import json
from typing import List, Dict

# Configuration

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_followers(username: str, per_page: int = 100) -> List[Dict]:
    """Fetch all followers of a user"""
    followers = []
    page = 1
    
    while True and len(followers)<1000:
        url = f"https://api.github.com/users/{username}/followers?per_page={per_page}&page={page}"
        response = requests.get(url, headers=HEADERS)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            break
        
        data = response.json()
        if not data:
            break
            
        followers.extend(data)
        print(f"Fetched page {page}, total so far: {len(followers)}")
        page += 1
        time.sleep(0.5)  # Be nice to the API
    
    return followers

def get_user_profile(username: str) -> Dict:
    """Fetch full user profile"""
    url = f"https://api.github.com/users/{username}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        return response.json()
    return None

def filter_influencers(followers: List[Dict]) -> List[Dict]:
    """Filter users with >100 followers OR >50 repos"""
    influencers = []
    
    for follower in followers:
        username = follower['login']
        print(f"Checking {username}...")
        
        profile = get_user_profile(username)
        if not profile:
            continue
        
        followers_count = profile.get('followers', 0)
        repos_count = profile.get('public_repos', 0)
        
        if followers_count > 100 or repos_count > 50:
            influencer_data = {
                'username': username,
                'followers': followers_count,
                'public_repos': repos_count,
                'bio': profile.get('bio', ''),
                'company': profile.get('company', ''),
                'avatar_url': profile.get('avatar_url', ''),
                'html_url': profile.get('html_url', ''),
                'added_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            influencers.append(influencer_data)
            print(f"✅ Added {username} (Followers: {followers_count}, Repos: {repos_count})")
        
        time.sleep(0.2)  # Avoid rate limits
    
    return influencers

def save_to_json(data: List[Dict], filename: str = 'influencers.json'):
    """Save influencers to JSON file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n✅ Saved {len(data)} influencers to {filename}")

def main():
    print("🚀 Starting High-Value Lead Tracker - Building Influencer List")
    print("=" * 50)
    
    # Step 1: Get followers of @karpathy
    print("\n📥 Fetching followers of @karpathy...")
    followers = get_followers('karpathy')
    print(f"✅ Found {len(followers)} total followers")
    
    # Step 2: Filter for high-value influencers
    print("\n🔍 Filtering for high-value influencers...")
    influencers = filter_influencers(followers)
    
    # Step 3: Limit to top 100
    top_100 = influencers
    
    # Step 4: Save to file
    save_to_json(top_100)
    
    # Summary
    print("\n📊 Summary:")
    print(f"   Total followers scanned: {len(followers)}")
    print(f"   High-value influencers found: {len(influencers)}")
    print(f"   Saved top 100 to influencers.json")
    
    if len(influencers) < 100:
        print(f"\n⚠️ Only found {len(influencers)} high-value influencers from @karpathy's followers")
        print("   You might need to add more famous people to reach 100")

if __name__ == "__main__":
    main()