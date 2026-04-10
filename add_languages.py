# add_languages_safe.py
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv
import os
import shutil

load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

def get_repo_languages(owner, repo):
    """Get ALL languages and their percentages"""
    url = f"https://api.github.com/repos/{owner}/{repo}/languages"
    
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            if data:
                primary = max(data, key=data.get)
                return primary, data
    except Exception as e:
        print(f"Error: {e}")
    
    return "Unknown", {}

def add_languages_to_leads():
    """Create NEW file with languages - don't overwrite original"""
    
    # 1. Create backup of original
    print("📦 Creating backup...")
    shutil.copy('emerging_leads.json', 'emerging_leads_backup.json')
    print("✅ Backup saved as: emerging_leads_backup.json")
    
    # 2. Load original
    with open('emerging_leads.json', 'r') as f:
        leads = json.load(f)
    
    print(f"\n📊 Loaded {len(leads)} leads")
    print("🔍 Fetching languages from GitHub...")
    print("=" * 60)
    
    # 3. Create new enriched data
    enriched_leads = []
    stats = {}
    
    for i, lead in enumerate(leads):
        repo_full = lead['repo']
        owner, repo = repo_full.split('/')
        
        print(f"{i+1}/{len(leads)}: {repo_full}...", end=" ")
        
        # Get languages
        primary, all_langs = get_repo_languages(owner, repo)
        
        # Create enriched lead (original + new fields)
        enriched_lead = lead.copy()  # Keep all original data
        enriched_lead['language'] = primary
        enriched_lead['all_languages'] = all_langs
        enriched_lead['language_last_updated'] = datetime.now().isoformat()
        
        enriched_leads.append(enriched_lead)
        
        # Track stats
        stats[primary] = stats.get(primary, 0) + 1
        
        print(f"✅ {primary}")
        
        time.sleep(0.3)  # Rate limiting
    
    # 4. Save to NEW file
    new_filename = f'emerging_leads_with_languages.json'
    with open(new_filename, 'w') as f:
        json.dump(enriched_leads, f, indent=2)
    
    # 5. Save statistics
    stats_filename = f'language_stats_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(stats_filename, 'w') as f:
        json.dump({
            'total_repos': len(enriched_leads),
            'languages': stats,
            'generated_at': datetime.now().isoformat()
        }, f, indent=2)
    
    # 6. Show results
    print("\n" + "=" * 60)
    print("📊 LANGUAGE STATISTICS:")
    print("=" * 60)
    
    for lang, count in sorted(stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        percentage = (count / len(enriched_leads)) * 100
        print(f"   {lang}: {count} repos ({percentage:.1f}%)")
    
    print("\n" + "=" * 60)
    print("✅ FILES CREATED:")
    print(f"   1. emerging_leads_backup.json - Original backup")
    print(f"   2. {new_filename} - New enriched data")
    print(f"   3. {stats_filename} - Language statistics")
    print("\n💡 To use the new file:")
    print("   cp emerging_leads_with_languages.json emerging_leads.json")
    print("   (After verifying everything looks correct)")

if __name__ == "__main__":
    print("🚀 SAFE LANGUAGE ENRICHMENT TOOL")
    print("=" * 60)
    print("This will:")
    print("  ✅ Keep your original file untouched")
    print("  ✅ Create a backup automatically")
    print("  ✅ Create a new file with languages added")
    print("  ✅ Generate statistics file")
    print()
    
    confirm = input("Continue? (y/n): ")
    if confirm.lower() == 'y':
        add_languages_to_leads()
    else:
        print("Cancelled.")