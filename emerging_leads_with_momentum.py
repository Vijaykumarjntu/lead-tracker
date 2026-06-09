# momentum_tracker.py - Track weekly growth rates
import requests
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
import os

load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

class MomentumTracker:
    def __init__(self, leads_file='emerging_leads_with_languages.json'):
        self.leads_file = leads_file
        self.state_file = 'momentum_state.json'
        self.load_state()
    
    def load_state(self):
        """Load previous tracking state"""
        try:
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
            print(f"✅ Loaded tracking state from {self.state['last_check']}")
        except:
            self.state = {
                'last_check': None,
                'historical_data': {},
                'momentum_scores': {}
            }
    
    def save_state(self):
        """Save current tracking state"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def get_current_stars(self, owner, repo):
        """Get current star count for a repo"""
        url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    'stars': data.get('stargazers_count', 0),
                    'updated_at': datetime.now().isoformat()
                }
        except Exception as e:
            print(f"Error fetching {owner}/{repo}: {e}")
        return None
    
    def calculate_momentum(self, repo_data, current_stars):
        """Calculate growth momentum"""
        repo_name = repo_data['repo']
        historical = self.state['historical_data'].get(repo_name, {})
        
        # Get initial stars (from when we first fetched)
        initial_stars = repo_data.get('stars', 0)
        initial_date = repo_data.get('fetched_at', repo_data.get('added_at'))
        
        # Get last check stars
        last_stars = historical.get('stars', initial_stars)
        last_date = historical.get('checked_at', initial_date)
        
        # Calculate time differences
        now = datetime.now()
        if initial_date:
            initial_date = datetime.fromisoformat(initial_date.replace('Z', '+00:00'))
        if last_date:
            last_date = datetime.fromisoformat(last_date.replace('Z', '+00:00'))
        
        days_since_initial = (now - initial_date).days if initial_date else 1
        days_since_last = (now - last_date).days if last_date else 1
        
        # Calculate growth rates
        total_growth = current_stars - initial_stars
        weekly_growth = (total_growth / days_since_initial) * 7 if days_since_initial > 0 else 0
        
        recent_growth = current_stars - last_stars
        recent_weekly = (recent_growth / days_since_last) * 7 if days_since_last > 0 else 0
        
        # Momentum score (weighted - recent growth matters more)
        momentum_score = (recent_weekly * 0.7) + (weekly_growth * 0.3)
        
        return {
            'current_stars': current_stars,
            'initial_stars': initial_stars,
            'total_growth': total_growth,
            'total_growth_percent': (total_growth / initial_stars * 100) if initial_stars > 0 else 0,
            'weekly_growth_rate': weekly_growth,
            'recent_weekly_growth': recent_weekly,
            'momentum_score': momentum_score,
            'days_since_initial': days_since_initial,
            'days_since_last': days_since_last
        }
    
    def check_all_repos(self, limit=100):
        """Check momentum for top repos"""
        
        # Load leads
        with open(self.leads_file, 'r') as f:
            leads = json.load(f)
        
        print(f"📊 Loaded {len(leads)} repos")
        print(f"🎯 Checking momentum for top {limit} repos...")
        print("=" * 70)
        
        # Sort by growth score to check most promising first
        leads.sort(key=lambda x: x.get('growth_score', 0), reverse=True)
        
        momentum_results = []
        
        for i, lead in enumerate(leads[:limit]):
            repo_name = lead['repo']
            owner, repo = repo_name.split('/')
            
            print(f"\n{i+1}/{limit}: {repo_name}")
            
            # Get current stars
            current = self.get_current_stars(owner, repo)
            if not current:
                continue
            
            # Calculate momentum
            momentum = self.calculate_momentum(lead, current['stars'])
            
            # Store result
            result = {
                'repo': repo_name,
                'owner': owner,
                'description': lead.get('description', ''),
                'language': lead.get('language', 'Unknown'),
                'initial_stars': momentum['initial_stars'],
                'current_stars': momentum['current_stars'],
                'total_growth': momentum['total_growth'],
                'total_growth_percent': momentum['total_growth_percent'],
                'weekly_growth_rate': momentum['weekly_growth_rate'],
                'recent_weekly_growth': momentum['recent_weekly_growth'],
                'momentum_score': momentum['momentum_score'],
                'days_tracked': momentum['days_since_initial'],
                'url': f"https://github.com/{repo_name}"
            }
            
            momentum_results.append(result)
            
            # Show change
            arrow = "📈" if momentum['recent_weekly_growth'] > 100 else "📊" if momentum['recent_weekly_growth'] > 10 else "📉"
            print(f"   {arrow} {momentum['initial_stars']:,} → {momentum['current_stars']:,} stars")
            print(f"   📈 Weekly growth: {momentum['recent_weekly_growth']:.0f} stars/week")
            print(f"   🚀 Momentum score: {momentum['momentum_score']:.0f}")
            
            # Update historical data
            self.state['historical_data'][repo_name] = {
                'stars': current['stars'],
                'checked_at': datetime.now().isoformat()
            }
            self.state['momentum_scores'][repo_name] = momentum['momentum_score']
            
            time.sleep(0.5)  # Rate limiting
        
        # Sort by momentum score (fastest growing NOW)
        momentum_results.sort(key=lambda x: x['momentum_score'], reverse=True)
        
        return momentum_results
    
    def generate_momentum_report(self, results, top_n=20):
        """Generate report of fastest growing repos"""
        
        print("\n" + "=" * 70)
        print("🚀 TOP 20 FASTEST GROWING REPOS (RIGHT NOW)")
        print("=" * 70)
        
        for i, repo in enumerate(results[:top_n], 1):
            print(f"\n{i}. 📦 {repo['repo']}")
            print(f"   🏷️  Language: {repo['language']}")
            print(f"   ⭐ {repo['initial_stars']:,} → {repo['current_stars']:,} (+{repo['total_growth']:,})")
            print(f"   📈 Weekly growth: {repo['recent_weekly_growth']:.0f} stars/week")
            print(f"   🚀 Momentum score: {repo['momentum_score']:.0f}")
            print(f"   📝 {repo['description'][:80]}...")
            
            # Highlight explosion
            if repo['recent_weekly_growth'] > 1000:
                print(f"   🔥 EXPLODING! +{repo['recent_weekly_growth']:.0f} stars this week!")
            elif repo['recent_weekly_growth'] > 500:
                print(f"   🚀 VIRAL! +{repo['recent_weekly_growth']:.0f} stars this week!")
        
        # Save report
        report = {
            'generated_at': datetime.now().isoformat(),
            'top_repos': results[:50],
            'summary': {
                'total_checked': len(results),
                'average_weekly_growth': sum(r['recent_weekly_growth'] for r in results) / len(results) if results else 0,
                'fastest_growing': results[0]['repo'] if results else None,
                'fastest_growth_rate': results[0]['recent_weekly_growth'] if results else 0
            }
        }
        
        with open('momentum_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Full report saved to momentum_report.json")
        
        return report
    
    def find_overtaking_repos(self, results):
        """Find repos that overtook others"""
        
        print("\n" + "=" * 70)
        print("🔄 REPOS THAT OVERTAKEN OTHERS")
        print("=" * 70)
        
        # Sort by current stars
        by_current = sorted(results, key=lambda x: x['current_stars'], reverse=True)
        # Sort by initial stars
        by_initial = sorted(results, key=lambda x: x['initial_stars'], reverse=True)
        
        # Create rankings
        current_rank = {r['repo']: i for i, r in enumerate(by_current)}
        initial_rank = {r['repo']: i for i, r in enumerate(by_initial)}
        
        # Find biggest climbers
        climbers = []
        for repo in results:
            rank_change = initial_rank.get(repo['repo'], 999) - current_rank.get(repo['repo'], 999)
            if rank_change > 5:  # Moved up more than 5 positions
                climbers.append({
                    'repo': repo['repo'],
                    'rank_change': rank_change,
                    'initial_rank': initial_rank.get(repo['repo'], 0) + 1,
                    'current_rank': current_rank.get(repo['repo'], 0) + 1,
                    'weekly_growth': repo['recent_weekly_growth']
                })
        
        climbers.sort(key=lambda x: x['rank_change'], reverse=True)
        
        for climber in climbers[:10]:
            print(f"\n📈 {climber['repo']}")
            print(f"   Rank: #{climber['initial_rank']} → #{climber['current_rank']} (+{climber['rank_change']} spots)")
            print(f"   Weekly growth: {climber['weekly_growth']:.0f} stars/week")
        
        return climbers
    
    def run(self, check_limit=100):
        """Run full momentum check"""
        
        print("🚀 MOMENTUM TRACKER")
        print("=" * 70)
        print("Tracking which repos are growing FASTEST right now")
        print()
        
        # Check all repos
        results = self.check_all_repos(limit=check_limit)
        
        # Generate report
        report = self.generate_momentum_report(results)
        
        # Find overtaking repos
        climbers = self.find_overtaking_repos(results)
        
        # Save state
        self.save_state()
        
        print("\n" + "=" * 70)
        print("✅ Momentum check complete!")
        print(f"📊 Checked {len(results)} repos")
        print(f"🚀 Fastest growing: {report['summary']['fastest_growing']}")
        print(f"📈 Average growth: {report['summary']['average_weekly_growth']:.0f} stars/week")
        
        return results

def main():
    tracker = MomentumTracker('emerging_leads.json')
    tracker.run(check_limit=100)

if __name__ == "__main__":
    main()