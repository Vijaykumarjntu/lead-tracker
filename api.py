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

def load_repos():
    """Load emerging leads"""
    try:
        with open('emerging_leads3_with_languages.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def get_language_stats(repos):
    """Get language distribution stats"""
    stats = defaultdict(int)
    for repo in repos:
        lang = repo.get('language', 'Unknown')
        stats[lang] += 1
    return dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))

@app.get("/")
def root():
    repos = load_repos()
    lang_stats = get_language_stats(repos)
    
    return {
        "message": "Emerging GitHub Repos API",
        "version": "2.0",
        "total_repos": len(repos),
        "languages_available": list(lang_stats.keys()),
        "endpoints": {
            "/repos/trending": "Get all trending repos",
            "/repos/beginner-friendly": "Get beginner-friendly repos",
            "/python": "Get Python repos only",
            "/javascript": "Get JavaScript repos only", 
            "/go": "Get Go repos only",
            "/rust": "Get Rust repos only",
            "/java": "Get Java repos only",
            "/cpp": "Get C++ repos only",
            "/language/{language}": "Get repos by specific language",
            "/languages": "Get all languages and counts",
            "/stats": "Get statistics"
        }
    }

@app.get("/languages")
def get_languages():
    """Get all available languages with counts"""
    repos = load_repos()
    lang_stats = get_language_stats(repos)
    
    return {
        "total_repos": len(repos),
        "languages": lang_stats,
        "top_5_languages": dict(list(lang_stats.items())[:5])
    }

@app.get("/python")
def get_python_repos(limit: int = Query(50, ge=1, le=200)):
    """Get Python repositories only"""
    repos = load_repos()
    
    python_repos = [
        repo for repo in repos 
        if repo.get('language', '').lower() == 'python'
    ]
    
    # Sort by growth score
    python_repos.sort(key=lambda x: x.get('growth_score', 0), reverse=True)
    
    return {
        "language": "Python",
        "count": len(python_repos),
        "repos": python_repos[:limit]
    }

@app.get("/javascript")
def get_javascript_repos(limit: int = Query(50, ge=1, le=200)):
    """Get JavaScript repositories only"""
    repos = load_repos()
    
    js_repos = [
        repo for repo in repos 
        if repo.get('language', '').lower() in ['javascript', 'js', 'node']
    ]
    
    js_repos.sort(key=lambda x: x.get('growth_score', 0), reverse=True)
    
    return {
        "language": "JavaScript",
        "count": len(js_repos),
        "repos": js_repos[:limit]
    }

@app.get("/typescript")
def get_typescript_repos(limit: int = Query(50, ge=1, le=200)):
    """Get TypeScript repositories only"""
    repos = load_repos()
    
    ts_repos = [
        repo for repo in repos 
        if repo.get('language', '').lower() in ['typescript', 'ts']
    ]
    
    ts_repos.sort(key=lambda x: x.get('growth_score', 0), reverse=True)
    
    return {
        "language": "TypeScript",
        "count": len(ts_repos),
        "repos": ts_repos[:limit]
    }

@app.get("/go")
def get_go_repos(limit: int = Query(50, ge=1, le=200)):
    """Get Go repositories only"""
    repos = load_repos()
    
    go_repos = [
        repo for repo in repos 
        if repo.get('language', '').lower() in ['go', 'golang']
    ]
    
    go_repos.sort(key=lambda x: x.get('growth_score', 0), reverse=True)
    
    return {
        "language": "Go",
        "count": len(go_repos),
        "repos": go_repos[:limit]
    }

@app.get("/rust")
def get_rust_repos(limit: int = Query(50, ge=1, le=200)):
    """Get Rust repositories only"""
    repos = load_repos()
    
    rust_repos = [
        repo for repo in repos 
        if repo.get('language', '').lower() == 'rust'
    ]
    
    rust_repos.sort(key=lambda x: x.get('growth_score', 0), reverse=True)
    
    return {
        "language": "Rust",
        "count": len(rust_repos),
        "repos": rust_repos[:limit]
    }

@app.get("/java")
def get_java_repos(limit: int = Query(50, ge=1, le=200)):
    """Get Java repositories only"""
    repos = load_repos()
    
    java_repos = [
        repo for repo in repos 
        if repo.get('language', '').lower() == 'java'
    ]
    
    java_repos.sort(key=lambda x: x.get('growth_score', 0), reverse=True)
    
    return {
        "language": "Java",
        "count": len(java_repos),
        "repos": java_repos[:limit]
    }

@app.get("/cpp")
def get_cpp_repos(limit: int = Query(50, ge=1, le=200)):
    """Get C++ repositories only"""
    repos = load_repos()
    
    cpp_repos = [
        repo for repo in repos 
        if repo.get('language', '').lower() in ['c++', 'cpp', 'c']
    ]
    
    cpp_repos.sort(key=lambda x: x.get('growth_score', 0), reverse=True)
    
    return {
        "language": "C/C++",
        "count": len(cpp_repos),
        "repos": cpp_repos[:limit]
    }

@app.get("/language/{language}")
def get_by_language(
    language: str,
    limit: int = Query(50, ge=1, le=200)
):
    """Get repos by any language"""
    repos = load_repos()
    
    filtered = [
        repo for repo in repos 
        if repo.get('language', '').lower() == language.lower()
    ]
    
    if not filtered:
        raise HTTPException(status_code=404, detail=f"No repos found for language: {language}")
    
    filtered.sort(key=lambda x: x.get('growth_score', 0), reverse=True)
    
    return {
        "language": language,
        "count": len(filtered),
        "repos": filtered[:limit]
    }

@app.get("/repos/trending")
def get_trending_repos(
    limit: int = Query(50, ge=1, le=200),
    min_stars: int = Query(50, ge=0, le=10000),
    max_stars: int = Query(5000, ge=0, le=50000),
    language: Optional[str] = None
):
    """Get trending repos with filters"""
    repos = load_repos()
    
    filtered = []
    for repo in repos:
        if repo.get('stars', 0) < min_stars or repo.get('stars', 0) > max_stars:
            continue
        if language and repo.get('language', '').lower() != language.lower():
            continue
        filtered.append(repo)
    
    filtered.sort(key=lambda x: x.get('growth_score', 0), reverse=True)
    
    return {
        "count": len(filtered[:limit]),
        "filters": {
            "min_stars": min_stars,
            "max_stars": max_stars,
            "language": language
        },
        "repos": filtered[:limit]
    }

@app.get("/repos/beginner-friendly")
def get_beginner_friendly(limit: int = Query(50, ge=1, le=100)):
    """Get beginner-friendly repos"""
    repos = load_repos()
    
    friendly = []
    for repo in repos:
        if repo.get('stars', 0) > 3000:
            continue
        
        score = repo.get('growth_score', 0)
        if repo.get('description'):
            score += 10
        
        friendly.append({
            **repo,
            'beginner_score': score
        })
    
    friendly.sort(key=lambda x: x['beginner_score'], reverse=True)
    
    return {
        "count": len(friendly[:limit]),
        "repos": friendly[:limit]
    }

@app.get("/stats")
def get_stats():
    """Get statistics"""
    repos = load_repos()
    lang_stats = get_language_stats(repos)
    
    return {
        'total_repos': len(repos),
        'average_stars': sum(r.get('stars', 0) for r in repos) / len(repos) if repos else 0,
        'average_growth': sum(r.get('growth_score', 0) for r in repos) / len(repos) if repos else 0,
        'languages': lang_stats,
        'top_languages': dict(list(lang_stats.items())[:5])
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)