# api.py - FastAPI backend
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import json
from datetime import datetime
import os

app = FastAPI(
    title="Emerging GitHub Repos API",
    description="Find fast-growing, approachable GitHub repos before they become mainstream",
    version="1.0.0"
)

# Enable CORS for anyone to use
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class RepoResponse(BaseModel):
    rank: int
    repo: str
    owner: str
    stars: int
    stars_per_month: float
    age_months: float
    growth_score: float
    description: str
    repo_url: str
    language: Optional[str]
    influencer: str
    influencer_followers: int
    sales_pitch: str

class FilterParams(BaseModel):
    min_stars: Optional[int] = 50
    max_stars: Optional[int] = 5000
    min_growth_score: Optional[float] = 10
    language: Optional[str] = None
    limit: Optional[int] = 50

# Load data
def load_repos():
    try:
        with open('emerging_leads.json', 'r') as f:
            return json.load(f)
    except:
        return []

def load_contacts():
    try:
        with open('owner_contacts.json', 'r') as f:
            return json.load(f)
    except:
        return []

@app.get("/")
def root():
    return {
        "message": "Emerging GitHub Repos API",
        "docs": "/docs",
        "endpoints": [
            "/repos/trending",
            "/repos/beginner-friendly",
            "/repos/by-language/{language}",
            "/repos/{owner}/{repo}"
        ]
    }

@app.get("/repos/trending", response_model=List[RepoResponse])
def get_trending_repos(
    limit: int = Query(50, ge=1, le=200),
    min_stars: int = Query(50, ge=0, le=10000),
    max_stars: int = Query(5000, ge=0, le=50000),
    min_growth: float = Query(10, ge=0, le=1000),
    language: Optional[str] = None
):
    """Get emerging repos with growth potential"""
    
    repos = load_repos()
    
    if not repos:
        raise HTTPException(status_code=404, detail="No repos found")
    
    # Apply filters
    filtered = []
    for repo in repos:
        if repo['stars'] < min_stars or repo['stars'] > max_stars:
            continue
        if repo.get('growth_score', 0) < min_growth:
            continue
        if language and repo.get('language', '').lower() != language.lower():
            continue
        filtered.append(repo)
    
    # Sort by growth score
    filtered.sort(key=lambda x: x.get('growth_score', 0), reverse=True)
    
    return filtered[:limit]

@app.get("/repos/beginner-friendly")
def get_beginner_friendly(
    limit: int = Query(50, ge=1, le=100)
):
    """Find repos good for first-time contributors"""
    
    repos = load_repos()
    contacts = load_contacts()
    
    # Criteria for beginner-friendly:
    # 1. Has good description
    # 2. Owner has contact info (approachable)
    # 3. Not too big (< 3000 stars)
    # 4. Has growth momentum
    
    friendly = []
    for repo in repos:
        if repo['stars'] > 3000:
            continue
        
        # Find owner contact
        owner_contact = next(
            (c for c in contacts if c.get('username') == repo['owner']),
            {}
        )
        
        # Bonus if owner has Twitter or blog (approachable)
        approachable_score = 0
        if owner_contact.get('twitter'):
            approachable_score += 20
        if owner_contact.get('blog'):
            approachable_score += 10
        
        total_score = repo.get('growth_score', 0) + approachable_score
        
        friendly.append({
            **repo,
            'approachable_score': approachable_score,
            'total_score': total_score,
            'owner_twitter': owner_contact.get('twitter'),
            'owner_blog': owner_contact.get('blog')
        })
    
    friendly.sort(key=lambda x: x['total_score'], reverse=True)
    
    return friendly[:limit]

@app.get("/repos/by-language/{language}")
def get_by_language(
    language: str,
    limit: int = Query(50, ge=1, le=100)
):
    """Get trending repos by programming language"""
    
    repos = load_repos()
    
    filtered = [r for r in repos if r.get('language', '').lower() == language.lower()]
    filtered.sort(key=lambda x: x.get('growth_score', 0), reverse=True)
    
    return filtered[:limit]

@app.get("/repos/{owner}/{repo}")
def get_repo_details(owner: str, repo: str):
    """Get detailed info about a specific repo"""
    
    repos = load_repos()
    contacts = load_contacts()
    
    # Find repo
    repo_data = next(
        (r for r in repos if r['owner'].lower() == owner.lower() and r['repo'].lower() == f"{owner}/{repo}".lower()),
        None
    )
    
    if not repo_data:
        raise HTTPException(status_code=404, detail="Repo not found")
    
    # Find owner contact
    owner_contact = next(
        (c for c in contacts if c.get('username') == owner),
        {}
    )
    
    return {
        'repo': repo_data,
        'owner_contact': owner_contact,
        'outreach_tips': {
            'best_channel': 'Twitter DM' if owner_contact.get('twitter') else 'GitHub Issue',
            'twitter': owner_contact.get('twitter'),
            'suggested_message': repo_data.get('sales_pitch', 'Check out this growing project!')
        }
    }

@app.get("/stats")
def get_stats():
    """Get overall statistics"""
    
    repos = load_repos()
    
    if not repos:
        return {"error": "No data"}
    
    languages = {}
    for repo in repos:
        lang = repo.get('language', 'Unknown')
        languages[lang] = languages.get(lang, 0) + 1
    
    return {
        'total_repos': len(repos),
        'average_stars': sum(r['stars'] for r in repos) / len(repos),
        'average_growth': sum(r.get('growth_score', 0) for r in repos) / len(repos),
        'top_languages': sorted(languages.items(), key=lambda x: x[1], reverse=True)[:10],
        'last_updated': datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)