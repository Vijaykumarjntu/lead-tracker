# code_mapper.py - Vertical flow, no horizontal scrolling
import requests
import json
import re
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import time
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

def get_repo_tree(owner: str, repo: str) -> List[str]:
    """Get all files in repo"""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1"
        response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"   ⚠️ Cannot access repo: {response.status_code}")
        return []
    
    data = response.json()
    if 'tree' not in data:
        return []
    
    return [item['path'] for item in data['tree'] if item['type'] == 'blob']

def read_file_content(owner: str, repo: str, file_path: str) -> str:
    """Read raw file content"""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        import base64
        try:
            content = response.json().get('content', '')
            if content:
                return base64.b64decode(content).decode('utf-8')
        except:
            return ""
    return ""

def find_imports_and_calls(content: str, file_path: str) -> Tuple[List[str], List[str]]:
    """Find imports and function calls"""
    imports = []
    calls = []
    
    if not content:
        return imports, calls
    
    import_patterns = [
        r'import\s+(\w+)',
        r'from\s+(\w+)\s+import',
        r'require\([\'"]([^\'"]+)[\'"]\)',
        r'#include\s+[<"]([^>"]+)[>"]',
    ]
    
    call_patterns = [
        r'(\w+)\([^)]*\)',
        r'(\w+)\.(\w+)\(',
        r'self\.(\w+)\(',
        r'this\.(\w+)\(',
    ]
    
    for pattern in import_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if isinstance(match, tuple):
                imports.extend(list(match))
            else:
                imports.append(match)
    
    for pattern in call_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if isinstance(match, tuple):
                calls.extend([m for m in match if len(m) > 1])
            else:
                calls.append(match)
    
    imports = list(set([i.split('.')[0] for i in imports if len(i) > 2]))[:10]
    calls = list(set(calls))[:10]
    
    return imports, calls

def resolve_import_to_file(import_name: str, all_files: List[str]) -> str:
    """Resolve import to actual file"""
    possibilities = [
        f"{import_name}.py", f"{import_name}.js", f"{import_name}.go",
        f"lib/{import_name}.py", f"src/{import_name}.py",
        f"{import_name}/{import_name}.py",
    ]
    
    for poss in possibilities:
        if poss in all_files:
            return poss
    
    for file in all_files:
        if import_name.lower() in file.lower():
            return file
    
    return None

def trace_execution_flow(owner: str, repo: str, entry_file: str, max_depth: int = 4) -> Dict:
    """Trace execution flow - VERTICAL only"""
    
    all_files = get_repo_tree(owner, repo)
    if not all_files or entry_file not in all_files:
        return None
    
    graph = {
        'nodes': {},
        'edges': [],
        'entry': entry_file
    }
    
    visited = set()
    to_process = [(entry_file, 0, 'start')]
    
    while to_process:
        current_file, depth, caller = to_process.pop(0)
        
        if current_file in visited or depth > max_depth:
            continue
        
        visited.add(current_file)
        content = read_file_content(owner, repo, current_file)
        
        if content:
            imports, calls = find_imports_and_calls(content, current_file)
            graph['nodes'][current_file] = {'imports': imports, 'calls': calls, 'depth': depth}
            
            if caller != 'start':
                graph['edges'].append({'from': caller, 'to': current_file})
            
            for imp in imports[:3]:
                resolved = resolve_import_to_file(imp, all_files)
                if resolved and resolved not in visited:
                    to_process.append((resolved, depth + 1, current_file))
    
    return graph

def generate_vertical_ascii_diagram(graph: Dict, use_case: str) -> str:
    """Generate VERTICAL flow diagram (no horizontal scrolling)"""
    
    if not graph or 'nodes' not in graph or len(graph['nodes']) == 0:
        return f"\n⚠️ No flow diagram available for {use_case}\n"
    
    lines = []
    lines.append(f"\n{'='*50}")
    lines.append(f"📊 {use_case}")
    lines.append(f"{'='*50}")
    lines.append(f"\n📍 ENTRY: {graph['entry'].split('/')[-1]}")
    lines.append("")
    lines.append("    ▼")
    
    # Group by depth
    nodes_by_depth = defaultdict(list)
    for file, data in graph['nodes'].items():
        nodes_by_depth[data['depth']].append(file)
    
    # Create vertical chain
    chain = []
    for depth in sorted(nodes_by_depth.keys()):
        for file in nodes_by_depth[depth]:
            short_name = file.split('/')[-1]
            chain.append(short_name)
    
    # Draw vertical flow
    for i, node in enumerate(chain):
        if i == 0:
            lines.append(f"    {node}")
        else:
            lines.append(f"        ▼")
            lines.append(f"    {node}")
    
    lines.append("        ▼")
    lines.append("    [RESULT]")
    
    # Add function calls info (compact)
    lines.append(f"\n{'─'*50}")
    lines.append("📞 FUNCTION CALLS (by file):")
    lines.append(f"{'─'*50}")
    
    for file, data in graph['nodes'].items():
        if data.get('calls'):
            short_name = file.split('/')[-1]
            call_preview = ', '.join(data['calls'][:4])
            lines.append(f"  📄 {short_name}")
            lines.append(f"     └─ calls: {call_preview}")
    
    return "\n".join(lines)

def generate_mermaid_diagram(graph: Dict, use_case: str) -> str:
    """Generate VERTICAL Mermaid diagram"""
    
    if not graph or 'nodes' not in graph or len(graph['nodes']) == 0:
        return ""
    
    lines = []
    lines.append("```mermaid")
    lines.append("flowchart TD")
    lines.append(f"    title {use_case}")
    lines.append("")
    
    # Create node IDs (short names)
    node_ids = {}
    for i, file in enumerate(graph['nodes'].keys()):
        node_id = f"N{i}"
        display_name = file.split('/')[-1][:30]  # Short name
        node_ids[file] = node_id
        lines.append(f"    {node_id}[\"{display_name}\"]")
    
    lines.append("")
    
    # Add edges (vertical flow)
    for edge in graph['edges']:
        from_id = node_ids.get(edge['from'])
        to_id = node_ids.get(edge['to'])
        if from_id and to_id:
            lines.append(f"    {from_id} --> {to_id}")
    
    # Highlight entry
    entry_id = node_ids.get(graph['entry'])
    if entry_id:
        lines.append(f"    style {entry_id} fill:#ff6b6b,stroke:#333,stroke-width:2px")
    
    lines.append("```")
    
    return "\n".join(lines)

def analyze_repo_complete(owner: str, repo: str):
    """Complete analysis"""
    
    print(f"\n{'='*60}")
    print(f"🔍 ANALYZING: {owner}/{repo}")
    print('='*60)
    
    all_files = get_repo_tree(owner, repo)
    if not all_files:
        print(f"❌ Cannot access repo")
        return None
    
    print(f"📁 {len(all_files)} files found")
    
    # Find entry files
    entry_candidates = ['main.py', 'cli.py', 'app.py', '__main__.py', 'index.js', 'main.go']
    entry_files = [f for f in entry_candidates if f in all_files]
    
    if not entry_files:
        entry_files = [f for f in all_files if 'main' in f.lower()][:1]
    
    if not entry_files and all_files:
        entry_files = [all_files[0]]
    
    if not entry_files:
        return None
    
    print(f"🚪 Entry: {entry_files[0]}")
    
    # Infer use case
    readme = read_file_content(owner, repo, 'README.md')
    use_case = "Code Execution Flow"
    if readme and 'api' in readme.lower():
        use_case = "API Call Flow"
    elif readme and 'cli' in readme.lower():
        use_case = "CLI Command Flow"
    
    # Trace flow
    graph = trace_execution_flow(owner, repo, entry_files[0], max_depth=4)
    
    if not graph or len(graph['nodes']) < 2:
        return None
    
    ascii_diagram = generate_vertical_ascii_diagram(graph, use_case)
    mermaid_diagram = generate_mermaid_diagram(graph, use_case)
    
    return {
        'repo': f"{owner}/{repo}",
        'use_case': use_case,
        'entry_file': entry_files[0],
        'files_involved': list(graph['nodes'].keys()),
        'ascii_diagram': ascii_diagram,
        'mermaid_diagram': mermaid_diagram,
        'stats': {
            'files_traced': len(graph['nodes']),
            'max_depth': max([d['depth'] for d in graph['nodes'].values()]) if graph['nodes'] else 0
        }
    }

def main():
    # Load repos
    try:
        with open('emerging_leads.json', 'r') as f:
            leads = json.load(f)
        print(f"✅ Loaded {len(leads)} leads")
    except:
        print("❌ emerging_leads.json not found")
        return
    
    all_results = []
    
    # Analyze first 3 repos
    for lead in leads[:3]:
        owner = lead['owner']
        repo_name = lead['repo'].split('/')[-1]
        
        result = analyze_repo_complete(owner, repo_name)
        
        if result:
            all_results.append(result)
            
            # Print ASCII diagram
            print(result['ascii_diagram'])
            
            # Print Mermaid diagram
            print("\n" + result['mermaid_diagram'])
        
        time.sleep(2)
    
    # Save results
    if all_results:
        with open('flow_diagrams.json', 'w') as f:
            json.dump(all_results, f, indent=2)
        
        # Save Mermaid diagrams to separate file
        with open('mermaid_diagrams.md', 'w') as f:
            for result in all_results:
                f.write(f"## {result['repo']} - {result['use_case']}\n\n")
                f.write(result['mermaid_diagram'])
                f.write("\n\n---\n\n")
        
        print(f"\n{'='*50}")
        print(f"✅ Done! Analyzed {len(all_results)} repos")
        print(f"📁 flow_diagrams.json - Full data")
        print(f"📊 mermaid_diagrams.md - Visual diagrams")

if __name__ == "__main__":
    main()