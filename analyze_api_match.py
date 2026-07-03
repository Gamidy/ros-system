#!/usr/bin/env python3
"""Cross-analysis of frontend-backend API matching for ROS system."""

import json
import re
import os
from collections import defaultdict, Counter

WORKDIR = "/Users/gamidy/ros-source/ros-system"

# ── 1. Load data ────────────────────────────────────────────────────────
with open(os.path.join(WORKDIR, "backend_api_inventory.json")) as f:
    backend_raw = json.load(f)

with open(os.path.join(WORKDIR, "frontend_scan_result.json")) as f:
    frontend_raw = json.load(f)

print(f"Backend endpoints loaded: {len(backend_raw)}")
print(f"Frontend routes loaded: {len(frontend_raw['frontend_routes'])}")
print(f"Frontend API files: {len(frontend_raw['api_files'])}")

# Flatten frontend_api_calls
frontend_api_calls = []
for group in frontend_raw.get("frontend_api_calls", []):
    file_name = group.get("file", "")
    for ep in group.get("endpoints", []):
        frontend_api_calls.append({
            "file": file_name,
            "method": ep["method"],
            "path": ep["path"],
            "source_type": "api_file"
        })
    for ep in group.get("in_view_calls", []):
        frontend_api_calls.append({
            "file": ep["file"],
            "method": ep["method"],
            "path": ep["path"],
            "source_type": "in_view"
        })

print(f"Total frontend API call references: {len(frontend_api_calls)}")

# ── 2. Normalize paths ──────────────────────────────────────────────────
def normalize_backend_path(path):
    """Strip /api prefix, remove trailing slashes."""
    p = path
    if p.startswith("/api"):
        p = p[4:]
    if p != "/" and p.endswith("/"):
        p = p.rstrip("/")
    return p

def normalize_frontend_path(path):
    """Remove trailing slashes, keep as-is (no /api prefix)."""
    p = path
    if p != "/" and p.endswith("/"):
        p = p.rstrip("/")
    return p

for ep in backend_raw:
    ep["normalized"] = normalize_backend_path(ep["path"])

for ep in frontend_api_calls:
    ep["normalized"] = normalize_frontend_path(ep["path"])

# ── 3. Module classification ────────────────────────────────────────────
MODULE_PATTERNS = [
    (r"^/auth", "auth"),
    (r"^/admin", "admin"),
    (r"^/products", "products"),
    (r"^/bom", "bom"),
    (r"^/projects?", "projects"),
    (r"^/project-templates", "project-templates"),
    (r"^/certifications?", "certifications"),
    (r"^/cert/", "cert-impact"),
    (r"^/cert", "certifications"),
    (r"^/s2/", "s2-cert"),
    (r"^/eco", "eco"),
    (r"^/ecr", "ecr"),
    (r"^/purchase(?:s)?/rfq", "purchase-rfq"),
    (r"^/purchase(?:s)?/supplier", "purchase-supplier"),
    (r"^/purchase(?:s)?/", "purchases"),
    (r"^/inventory", "inventory"),
    (r"^/cost-accounting", "cost-accounting"),
    (r"^/cost-alert", "cost-alert"),
    (r"^/cost-recalc", "cost-recalc"),
    (r"^/bi/", "bi-analytics"),
    (r"^/product-plans?", "product-plans"),
    (r"^/product-requirements?", "product-requirements"),
    (r"^/plan-templates", "plan-templates"),
    (r"^/review-templates", "review-templates"),
    (r"^/reviews?", "reviews"),
    (r"^/tasks?", "tasks"),
    (r"^/target-markets?", "target-markets"),
    (r"^/pm/", "pm"),
    (r"^/prototypes?", "prototypes"),
    (r"^/tests?", "tests"),
    (r"^/verification-requirements?", "verification-requirements"),
    (r"^/test-requests?", "test-requests"),
    (r"^/test-executions?", "test-executions"),
    (r"^/gate-rules?", "gate-rules"),
    (r"^/quality/", "quality"),
    (r"^/dfm/", "dfm"),
    (r"^/safety/", "safety"),
    (r"^/outsource/", "outsource"),
    (r"^/notifications?", "notifications"),
    (r"^/alert(?:-rules?)?", "alerts"),
    (r"^/approval/", "approvals"),
    (r"^/audit-logs?", "audit-logs"),
    (r"^/events?", "events"),
    (r"^/kb/", "knowledge-base"),
    (r"^/knowledge-base/", "knowledge-base"),
    (r"^/knowledge/", "knowledge"),
    (r"^/standards?", "standards"),
    (r"^/dashboard/", "dashboard"),
    (r"^/process/", "process"),
    (r"^/prototypes?", "prototypes"),
    (r"^/ai/", "ai"),
    (r"^/api/v2/", "ci-v2"),
    (r"^/admin/config", "admin"),
    (r"^/admin/ai", "admin-ai"),
    (r"^/admin/standards", "admin-standards"),
    (r"^/admin/tenants?", "admin-tenant"),
]

def classify_module(path):
    for pattern, module in MODULE_PATTERNS:
        if re.match(pattern, path):
            return module
    return "other"

print("\n" + "="*80)
print("PART 1: BACKEND API MODULE BREAKDOWN")
print("="*80)

backend_modules = defaultdict(list)
for ep in backend_raw:
    module = classify_module(ep["normalized"])
    backend_modules[module].append(ep)

for module in sorted(backend_modules.keys(), key=lambda m: -len(backend_modules[m])):
    endpoints = backend_modules[module]
    print(f"  {module:25s}: {len(endpoints):4d} endpoints")

# ── 4. Frontend module breakdown ────────────────────────────────────────
print("\n" + "="*80)
print("PART 2: FRONTEND API CALL MODULE BREAKDOWN")
print("="*80)

frontend_modules = defaultdict(list)
for ep in frontend_api_calls:
    module = classify_module(ep["normalized"])
    frontend_modules[module].append(ep)

for module in sorted(frontend_modules.keys(), key=lambda m: -len(frontend_modules[m])):
    endpoints = frontend_modules[module]
    print(f"  {module:25s}: {len(endpoints):4d} calls")

# ── 5. Path comparison helper ───────────────────────────────────────────
def path_to_pattern(p):
    """Convert a URL path with :param or {param} to a regex pattern."""
    # Replace {param} and :param with regex capture group
    p = re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', p)
    p = re.sub(r':(\w+)', r'(?P<\1>[^/]+)', p)
    return '^' + p + '$'

def paths_match(fe_path, be_path):
    """Check if frontend path matches backend path, handling parameter styles."""
    # Both should be normalized (no /api prefix on backend, no trailing slashes)
    fe = fe_path.rstrip("/") if fe_path != "/" else "/"
    be = be_path.rstrip("/") if be_path != "/" else "/"
    
    # Direct match
    if fe == be:
        return True
    
    # Try matching with parameter patterns
    pattern = path_to_pattern(fe)
    if re.match(pattern, be):
        return True
    
    pattern = path_to_pattern(be)
    if re.match(pattern, fe):
        return True
    
    return False

def methods_compatible(fe_method, be_method):
    """Check if HTTP methods match."""
    return fe_method.upper() == be_method.upper()

# ── 6. Cross-reference: Backend → Frontend ──────────────────────────────
print("\n" + "="*80)
print("PART 3: BACKEND-TO-FRONTEND CROSS-REFERENCE")
print("="*80)

matched_backend = set()
unmatched_backend = []  # P1: orphan APIs

for be_ep in backend_raw:
    be_norm = be_ep["normalized"]
    be_method = be_ep["method"]
    
    # Find matching frontend calls
    found = False
    matching_fes = []
    for fe_ep in frontend_api_calls:
        if paths_match(fe_ep["normalized"], be_norm):
            # Check method
            if methods_compatible(fe_ep["method"], be_method):
                found = True
                matching_fes.append((fe_ep["file"], fe_ep["method"]))
    
    if not found:
        unmatched_backend.append(be_ep)
        # Also check if there's a path match but method mismatch
        method_mismatch = False
        for fe_ep in frontend_api_calls:
            if paths_match(fe_ep["normalized"], be_norm):
                if not methods_compatible(fe_ep["method"], be_method):
                    method_mismatch = True
                    break
        be_ep["_method_mismatch"] = method_mismatch
    else:
        matched_backend.add(be_ep["path"])

print(f"\n  Matched backend endpoints: {len(matched_backend)}")
print(f"  Unmatched backend endpoints: {len(unmatched_backend)}")

# P1: Orphan APIs — backend exists, no frontend calls it
print("\n  --- P1: ORPHAN BACKEND APIS (no frontend caller) ---")
orphan_count = 0
for ep in unmatched_backend:
    if not ep.get("_method_mismatch"):
        if orphan_count < 30:  # limit output
            print(f"    {ep['method']:6s} {ep['normalized']:50s} [{ep['file']}]")
        orphan_count += 1
print(f"  Total orphan APIs: {orphan_count}")

# P3: Method mismatches
print("\n  --- P3: HTTP METHOD MISMATCHES ---")
method_mismatch_count = 0
for ep in unmatched_backend:
    if ep.get("_method_mismatch"):
        # Find what frontend uses
        for fe_ep in frontend_api_calls:
            if paths_match(fe_ep["normalized"], ep["normalized"]):
                print(f"    Backend: {ep['method']:6s} {ep['normalized']:50s} vs Frontend: {fe_ep['method']:6s} [{fe_ep['file']}]")
                method_mismatch_count += 1
                break
print(f"  Total method mismatches: {method_mismatch_count}")

# ── 7. Cross-reference: Frontend → Backend ──────────────────────────────
print("\n" + "="*80)
print("PART 4: FRONTEND-TO-BACKEND CROSS-REFERENCE")
print("="*80)

unmatched_frontend = []  # P0: frontend page exists, no backend API

for fe_ep in frontend_api_calls:
    fe_norm = fe_ep["normalized"]
    fe_method = fe_ep["method"]
    
    found = False
    for be_ep in backend_raw:
        if paths_match(fe_ep["normalized"], normalize_backend_path(be_ep["path"])):
            if methods_compatible(fe_method, be_ep["method"]):
                found = True
                break
    
    if not found:
        unmatched_frontend.append(fe_ep)

print(f"\n  Matched frontend calls: {len(frontend_api_calls) - len(unmatched_frontend)}")
print(f"  Unmatched frontend calls: {len(unmatched_frontend)}")

# P0: Frontend calls with no backend
print("\n  --- P0: MISSING BACKEND API (frontend calls with no backend) ---")
p0_by_module = defaultdict(list)
for ep in unmatched_frontend:
    module = classify_module(ep["normalized"])
    p0_by_module[module].append(ep)
    print(f"    [{module:20s}] {ep['method']:6s} {ep['normalized']:50s} [{ep['file']}]")

print(f"\n  Total P0 issues: {len(unmatched_frontend)}")
for mod in sorted(p0_by_module.keys(), key=lambda m: -len(p0_by_module[m])):
    print(f"    {mod:25s}: {len(p0_by_module[mod])} missing APIs")

# ── 8. P2: Path prefix inconsistencies ──────────────────────────────────
print("\n" + "="*80)
print("PART 5: PATH INCONSISTENCIES (P2)")
print("="*80)

# Look for paths that differ only by prefix variations
backend_paths = set(ep["normalized"] for ep in backend_raw)
frontend_paths_set = set(ep["normalized"] for ep in frontend_api_calls)

# Check common prefixes
prefix_pairs = [
    ("/purchases/", "/purchase/"),
    ("/inventory/items", "/inventory/"),
    ("/certifications/prototypes", "/prototypes"),
]

inconsistencies = []
for fe_ep in frontend_api_calls:
    fe_norm = fe_ep["normalized"]
    # Skip if already matched
    already_found = False
    for be_ep in backend_raw:
        if paths_match(fe_norm, normalize_backend_path(be_ep["path"])):
            if methods_compatible(fe_ep["method"], be_ep["method"]):
                already_found = True
                break
    
    if already_found:
        continue
    
    # Try alternate prefixes
    for be_ep in backend_raw:
        be_norm = normalize_backend_path(be_ep["path"])
        
        # Check if paths are close but not matching
        # Different parameter style
        if fe_norm.replace(":", "").replace("{", "").replace("}", "") == be_norm.replace(":", "").replace("{", "").replace("}", ""):
            if fe_norm != be_norm:
                inconsistencies.append({
                    "fe_path": fe_norm,
                    "fe_method": fe_ep["method"],
                    "fe_file": fe_ep["file"],
                    "be_path": be_norm,
                    "be_method": be_ep["method"],
                    "type": "param_style"
                })
                break
        
        # Prefix mismatch
        fe_parts = fe_norm.split("/")
        be_parts = be_norm.split("/")
        if len(fe_parts) >= 2 and len(be_parts) >= 2 and fe_parts[1] != be_parts[1]:
            # Different first-level path - just note it
            pass
    
    # Check for singular/plural differences
    be_path_no_params = re.sub(r'\{?\w+\}?', '', be_norm).strip('/').split('/')
    fe_path_no_params = re.sub(r'\{?\w+\}?', '', fe_norm).strip('/').split('/')
    
    if be_path_no_params and fe_path_no_params:
        be_prefix = '/'.join(p.rstrip('s') for p in be_path_no_params[:2])
        fe_prefix = '/'.join(p.rstrip('s') for p in fe_path_no_params[:2])
        if be_prefix == fe_prefix and be_norm != fe_norm:
            inconsistencies.append({
                "fe_path": fe_norm,
                "fe_method": fe_ep["method"],
                "fe_file": fe_ep["file"],
                "be_path": be_norm,
                "be_method": be_ep["method"],
                "type": "plural_vs_singular"
            })
            break

# Deduplicate
seen_inc = set()
unique_incs = []
for inc in inconsistencies:
    key = (inc["fe_path"], inc["be_path"])
    if key not in seen_inc:
        seen_inc.add(key)
        unique_incs.append(inc)

for inc in unique_incs[:20]:
    print(f"  {inc['type']:20s} | FE: {inc['fe_method']:6s} {inc['fe_path']:45s} vs BE: {inc['be_method']:6s} {inc['be_path']}")

print(f"\n  Total potential path inconsistencies: {len(unique_incs)}")

# ── 9. Module-level summary ─────────────────────────────────────────────
print("\n" + "="*80)
print("PART 6: MODULE-LEVEL MATCH SUMMARY")
print("="*80)

all_modules = set(list(backend_modules.keys()) + list(frontend_modules.keys()))
for module in sorted(all_modules):
    be_count = len(backend_modules.get(module, []))
    fe_count = len(frontend_modules.get(module, []))
    
    # Count actual matches
    match_count = 0
    for be_ep in backend_modules.get(module, []):
        for fe_ep in frontend_modules.get(module, []):
            if paths_match(fe_ep["normalized"], normalize_backend_path(be_ep["path"])):
                if methods_compatible(fe_ep["method"], be_ep["method"]):
                    match_count += 1
                    break
    
    p0_count = len([ep for ep in unmatched_frontend if classify_module(ep["normalized"]) == module])
    p1_count = len([ep for ep in unmatched_backend if not ep.get("_method_mismatch") and classify_module(ep["normalized"]) == module])
    
    status = "✅" if match_count > 0 and p0_count == 0 and p1_count <= 1 else "⚠️" if p0_count <= 2 else "❌"
    print(f"  {status} {module:25s} | BE:{be_count:3d} APIs | FE:{fe_count:3d} calls | Matched:{match_count:3d} | P0(Miss):{p0_count:2d} | P1(Orphan):{p1_count:2d}")

# ── 10. Key module deep-dives ───────────────────────────────────────────
KEY_MODULES = ["auth", "bom", "projects", "ecr", "eco", "purchases", "purchase-rfq", "purchase-supplier",
               "inventory", "cost-accounting", "certifications", "s2-cert", "pm", "product-plans",
               "quality", "outsource", "safety", "dfm", "gate-rules", "tests"]

print("\n" + "="*80)
print("PART 7: KEY MODULE DEEP-DIVE")
print("="*80)

for module in KEY_MODULES:
    be_eps = backend_modules.get(module, [])
    fe_eps = frontend_modules.get(module, [])
    
    if not be_eps and not fe_eps:
        continue
    
    print(f"\n  ── {module.upper()} ──")
    print(f"     Backend: {len(be_eps)} endpoints | Frontend: {len(fe_eps)} calls")
    
    # Mismatches in this module
    p0 = [ep for ep in unmatched_frontend if classify_module(ep["normalized"]) == module]
    p1 = [ep for ep in unmatched_backend if not ep.get("_method_mismatch") and classify_module(ep["normalized"]) == module]
    
    if p0:
        print(f"     🔴 P0 (Missing Backend):")
        for ep in p0[:5]:
            print(f"        FE: {ep['method']:6s} {ep['normalized']:50s} [{ep['file']}]")
        if len(p0) > 5:
            print(f"        ... and {len(p0)-5} more")
    
    if p1:
        print(f"     🟡 P1 (Orphan Backend APIs - no frontend uses):")
        for ep in p1[:5]:
            print(f"        BE: {ep['method']:6s} {ep['normalized']:50s} [{ep['file']}]")
        if len(p1) > 5:
            print(f"        ... and {len(p1)-5} more")

print("\n" + "="*80)
print("PART 8: FRONTEND ROUTES WITH NO BACKEND COVERAGE")
print("="*80)

# Map routes to modules
route_module_map = {}
for route in frontend_raw["frontend_routes"]:
    path = route.get("path", "")
    name = route.get("name", "")
    if path.startswith("/"):
        # Root route
        pass
    
    # Check children
    for child in route.get("children", []):
        child_path = child.get("path", "")
        child_name = child.get("name", "")
        
        # Classify what module this belongs to
        full_path = "/" + child_path if not child_path.startswith("/") else child_path
        module = classify_module(full_path)
        
        # Check if there are any backend APIs for this module
        be_count = len(backend_modules.get(module, []))
        fe_count = len(frontend_modules.get(module, []))
        
        p0 = [ep for ep in unmatched_frontend if classify_module(ep["normalized"]) == module and module != "other"]
        
        if be_count == 0 and fe_count > 0:
            print(f"  ❌ {child_name:30s} path=/{child_path:40s} module={module:20s} → NO backend APIs")
        elif p0:
            print(f"  ⚠️ {child_name:30s} path=/{child_path:40s} module={module:20s} → {len(p0)} missing APIs")

print("\n" + "="*80)
print("SUMMARY STATISTICS")
print("="*80)

total_p0 = len(unmatched_frontend)
total_p1 = orphan_count
total_p3 = method_mismatch_count

# Count P2 (path inconsistencies)
# Path match but different parameter style
p2_count = 0
for inc in unique_incs:
    if inc["type"] == "param_style":
        p2_count += 1

print(f"""
  Overall Statistics:
  ───────────────────
  Backend Endpoints:           {len(backend_raw):4d}
  Frontend API Calls:          {len(frontend_api_calls):4d}
  Frontend Routes:             {len(frontend_raw['frontend_routes']):4d}

  Issues Found:
  ─────────────
  P0 (Missing Backend API):    {total_p0:4d}  ← Frontend calls without backend
  P1 (Orphan Backend API):     {total_p1:4d}  ← Backend APIs not called by frontend
  P2 (Path Inconsistency):     {p2_count:4d}  ← Parameter style differences
  P3 (HTTP Method Mismatch):   {total_p3:4d}  ← FE/BE use different HTTP methods

  Key Risk Modules (by P0 count):
""")

for module in sorted(p0_by_module.keys(), key=lambda m: -len(p0_by_module[m])):
    be_count = len(backend_modules.get(module, []))
    print(f"    {module:25s}: P0={len(p0_by_module[module]):3d} (BE={be_count} endpoints)")
