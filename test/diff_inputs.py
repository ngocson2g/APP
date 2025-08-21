# tools/diff_inputs.py
import html, re, sys, json
from collections import defaultdict
from security_app.parsers.csv_parser import parse_csv
from security_app.parsers.json_parser import parse_json
from security_app.core.command_extractor import extract_all_commands

def clean(s: str) -> str:
    if s is None: return ""
    s = html.unescape(str(s))
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.translate(str.maketrans({"“":'"', "”":'"', "’":"'", "‘":"'", "‐":"-"}))
    return s.strip()

def norm_cmds(text: str):
    text = clean(text)
    return [c.strip() for c in extract_all_commands(text)]

def to_map(rules):
    m = {}
    for r in rules:
        m[r.id] = {
            "severity": r.severity,
            "title": clean(r.title),
            "check": clean(r.check),
            "cmds": norm_cmds(r.check),
        }
    return m

csv_rules = parse_csv(sys.argv[1])
json_rules = parse_json(sys.argv[2])

A = to_map(csv_rules)
B = to_map(json_rules)

only_in_A = sorted(set(A) - set(B))
only_in_B = sorted(set(B) - set(A))
print(f"Only in CSV: {len(only_in_A)} -> {only_in_A[:10]}")
print(f"Only in JSON: {len(only_in_B)} -> {only_in_B[:10]}")

diff_ids = []
for rid in sorted(set(A) & set(B)):
    if A[rid]["cmds"] != B[rid]["cmds"]:
        diff_ids.append(rid)

print(f"Rules with different command lists: {len(diff_ids)}")
for rid in diff_ids[:30]:
    print("="*80)
    print(rid)
    print("CSV cmds:")
    for c in A[rid]["cmds"]:
        print("  $", c)
    print("JSON cmds:")
    for c in B[rid]["cmds"]:
        print("  $", c)
