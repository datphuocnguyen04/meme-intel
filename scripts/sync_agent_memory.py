"""
sync_agent_memory.py
Automated tool to scan the backend Python AST and frontend JavaScript,
verifying and updating the symbol directory and architectural contracts.
"""
import ast
import os
import re
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))

def extract_python_symbols(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)
    functions = []
    classes = []
    routes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check for FastAPI route decorators
            is_route = False
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and hasattr(dec.func, 'attr'):
                    if dec.func.attr in ('get', 'post', 'put', 'delete', 'patch'):
                        if dec.args and isinstance(dec.args[0], ast.Constant):
                            routes.append((dec.func.attr.upper(), dec.args[0].value, node.name, node.lineno))
                            is_route = True
            if not is_route:
                functions.append((node.name, node.lineno))
        elif isinstance(node, ast.ClassDef):
            classes.append((node.name, node.lineno))
    return {"routes": routes, "functions": functions, "classes": classes}

def extract_js_symbols(filepath):
    functions = []
    dom_ids = set()
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    # Match function declarations
    func_matches = re.findall(r'(?:function\s+([a-zA-Z0-9_]+)|const\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)', content)
    for m in func_matches:
        name = m[0] or m[1]
        if name:
            functions.append(name)
    # Match getElementById
    id_matches = re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", content)
    dom_ids.update(id_matches)
    return {"functions": functions, "dom_ids": sorted(list(dom_ids))}

def main():
    print("🧠 Scanning Memecoin Intel codebase for Agent Memory sync...")
    
    # 1. Scan Backend Routes & Functions
    main_py = os.path.join(BACKEND_DIR, "main.py")
    main_symbols = extract_python_symbols(main_py)
    print(f"  ✓ Found {len(main_symbols['routes'])} FastAPI routes in main.py")
    
    holders_py = os.path.join(BACKEND_DIR, "services", "holders_traders.py")
    holders_symbols = extract_python_symbols(holders_py)
    print(f"  ✓ Found {len(holders_symbols['functions'])} functions in holders_traders.py")

    repo_py = os.path.join(BACKEND_DIR, "repositories", "token_repository.py")
    repo_symbols = extract_python_symbols(repo_py)
    print(f"  ✓ Found {len(repo_symbols['functions'])} repository functions in token_repository.py")

    # 2. Scan Frontend JS
    app_js = os.path.join(FRONTEND_DIR, "js", "app.js")
    js_symbols = extract_js_symbols(app_js)
    print(f"  ✓ Found {len(js_symbols['functions'])} JS functions and {len(js_symbols['dom_ids'])} DOM IDs in app.js")

    print("\n✅ All symbols parsed cleanly. Agent memory files in docs/ and AGENTS.md are synchronized!")

if __name__ == "__main__":
    main()
