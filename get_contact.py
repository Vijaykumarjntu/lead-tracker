# get_contacts.py
import requests
import json
import time
import os
from dotenv import load_dotenv
load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

def get_user_contact_info(username):
    """Fetch user's GitHub profile for contact info"""
    url = f"https://api.github.com/users/{username}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        return None
    
    user_data = response.json()
    
    # These are the fields GitHub provides
    contact_info = {
        'username': username,
        'name': user_data.get('name'),
        'email': user_data.get('email'),  # Usually None unless public
        'twitter': user_data.get('twitter_username'),
        'blog': user_data.get('blog'),  # Personal website
        'company': user_data.get('company'),
        'bio': user_data.get('bio'),
        'location': user_data.get('location'),
        'html_url': user_data.get('html_url')
    }
    
    return contact_info

def get_contacts_from_leads(leads_file='emerging_leads.json', limit=50):
    """Get contact info for all leads"""
    
    with open(leads_file, 'r') as f:
        leads = json.load(f)
    
    print(f"🔍 Fetching contact info for {min(len(leads), limit)} repo owners...")
    print("=" * 70)
    
    all_contacts = []
    
    for idx, lead in enumerate(leads[:limit], 1):
        owner = lead['owner']
        repo = lead['repo']
        
        print(f"\n{idx}. Checking @{owner}...")
        
        # Get their GitHub profile
        contact = get_user_contact_info(owner)
        
        if contact:
            contact['repo'] = repo
            contact['repo_stars'] = lead.get('stars')
            contact['growth_score'] = lead.get('growth_score')
            contact['influencer'] = lead.get('influencer')
            
            all_contacts.append(contact)
            
            # Show what we found
            if contact['twitter']:
                print(f"   🐦 Twitter: @{contact['twitter']}")
            if contact['email']:
                print(f"   📧 Email: {contact['email']}")
            if contact['blog']:
                print(f"   🌐 Website: {contact['blog']}")
            if contact['company']:
                print(f"   💼 Company: {contact['company']}")
            if not any([contact['twitter'], contact['email'], contact['blog']]):
                print(f"   ⚠️ No public contact info")
        
        time.sleep(0.3)  # Avoid rate limits
    
    # Save results
    with open('owner_contacts.json', 'w') as f:
        json.dump(all_contacts, f, indent=2)
    
    print("\n" + "=" * 70)
    print(f"✅ Found {len(all_contacts)} profiles")
    print(f"💾 Saved to owner_contacts.json")
    
    # Summary
    twitter_count = len([c for c in all_contacts if c.get('twitter')])
    email_count = len([c for c in all_contacts if c.get('email')])
    blog_count = len([c for c in all_contacts if c.get('blog')])
    
    print(f"\n📊 Summary:")
    print(f"   🐦 Twitter handles: {twitter_count}/{len(all_contacts)}")
    print(f"   📧 Public emails: {email_count}/{len(all_contacts)}")
    print(f"   🌐 Personal websites: {blog_count}/{len(all_contacts)}")
    
    return all_contacts

def generate_outreach_list(contacts_file='owner_contacts.json'):
    """Generate list of reachable owners"""
    
    with open(contacts_file, 'r') as f:
        contacts = json.load(f)
    
    print("\n📋 REACHABLE OWNERS")
    print("=" * 70)
    
    # Sort by reachable method
    twitter_contacts = [c for c in contacts if c.get('twitter')]
    email_contacts = [c for c in contacts if c.get('email')]
    website_contacts = [c for c in contacts if c.get('blog')]
    
    print(f"\n🎯 Twitter DM (Best): {len(twitter_contacts)} owners")
    for contact in twitter_contacts[:10]:
        print(f"   • @{contact['username']} - {contact['repo']} | Twitter: @{contact['twitter']}")
    
    print(f"\n📧 Email: {len(email_contacts)} owners")
    for contact in email_contacts[:5]:
        print(f"   • @{contact['username']} - {contact['repo']} | Email: {contact['email']}")
    
    print(f"\n🌐 Website Contact Form: {len(website_contacts)} owners")
    for contact in website_contacts[:5]:
        print(f"   • @{contact['username']} - {contact['repo']} | Website: {contact['blog']}")
    
    # Save sorted lists
    with open('reachable_twitter.json', 'w') as f:
        json.dump(twitter_contacts, f, indent=2)
    
    with open('reachable_email.json', 'w') as f:
        json.dump(email_contacts, f, indent=2)
    
    print(f"\n💾 Saved reachable lists:")
    print(f"   • reachable_twitter.json ({len(twitter_contacts)} owners)")
    print(f"   • reachable_email.json ({len(email_contacts)} owners)")
    
    return twitter_contacts, email_contacts

def main():
    # Step 1: Get contact info
    contacts = get_contacts_from_leads('emerging_leads.json', limit=100)
    
    # Step 2: Generate outreach list
    twitter_contacts, email_contacts = generate_outreach_list()
    
    print("\n" + "=" * 70)
    print("🚀 NEXT STEPS:")
    print("   1. Check reachable_twitter.json for owners to DM")
    print("   2. Check reachable_email.json for email outreach")
    print("   3. For others, create GitHub issues on their repos")
    print("   4. Use the sales pitch from emerging_leads.json")

if __name__ == "__main__":
    main()