# api.py - Add these new endpoints
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import json
from collections import defaultdict
import os

app = FastAPI(
    title="Emerging GitHub Repos API",
    description="Find fast-growing, approachable GitHub repos by language",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_repos(x):
    """Load repos from JSON file"""
    try:
        if x==2500:
            with open('emerging_leads_new_with_languages.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        elif x==10000:
            with open('emerging_leads3_10000_with_languages.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open('emerging_leads_25000_with_languages.json', 'r', encoding='utf-8') as f:
                return json.load(f)

    except:
        try:
            with open('emerging_leads.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []


@app.get("/")
def root():
    return {
        "message": "Emerging GitHub Repos API",
        "endpoints": {
            "/repos/under-2500": "Repos with less than 2,500 stars",
            "/repos/under-10000": "Repos with less than 10,000 stars"
        }
    }

@app.get("/repos/under-2500")
def get_under_2500():
    """Get repos with less than 2,500 stars"""
    repos = load_repos(2500)
    
    # Filter: stars < 2500
    # filtered = [r for r in repos if r.get('stars', 0) < 2500]
    
    # Sort by growth score
    repos.sort(key=lambda x: x.get('growth_score', 0), reverse=True)
    return {
        "category": "Under 2.5k stars",
        "count": len(repos),
        "repos": repos
    }

    
@app.get("/repos/under-10000")
def get_under_10000():
    """Get repos with less than 10,000 stars"""
    repos = load_repos(10000)
    
    # Filter: stars < 10000
    # filtered = [r for r in repos if r.get('stars', 0) < 10000]
    
    # Sort by growth score
    repos.sort(key=lambda x: x.get('growth_score', 0), reverse=True)
    return {
        "category": "Under 10k stars",
        "count": len(repos),
        "repos": repos 
    }

@app.get("/repos/under-25000")
def get_under_2500():
    """Get repos with less than 2,500 stars"""
    repos = load_repos(25000)
    
    # Filter: stars < 2500
    # filtered = [r for r in repos if r.get('stars', 0) < 2500]
    
    # Sort by growth score
    repos.sort(key=lambda x: x.get('growth_score', 0), reverse=True)
    return {
        "category": "Under 2.5k stars",
        "count": len(repos),
        "repos": repos
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)    

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)