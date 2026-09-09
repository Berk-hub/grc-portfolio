#!/usr/bin/env python3
"""Consistency checks for the Fineract assessment files.

Run from the fineract/ directory: python check.py
Exits non-zero if anything is inconsistent, so it can run in CI later.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# what the report summary claims (section 1)
EXPECTED_COUNTS = {"High": 2, "Medium": 4, "Low": 2}
VALID_RATINGS = set(EXPECTED_COUNTS)
VALID_CONDITIONS = {"C1", "C2", "C3", "none"}

errors = []


def load_finding(path):
    """The finding files use a flat key: value format, lists inline in brackets."""
    d = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#") or ": " not in line and not line.endswith(":"):
                continue
            key, _, val = line.partition(":")
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                d[key.strip()] = [x.strip() for x in inner.split(",")] if inner else []
            else:
                d[key.strip()] = val
    return d


# --- load everything
findings_dir = os.path.join(HERE, "findings")
files = sorted(f for f in os.listdir(findings_dir) if f.endswith(".yml"))
findings = {}
for name in files:
    f = load_finding(os.path.join(findings_dir, name))
    if f.get("id") != name[:-4]:
        errors.append(f"{name}: id field '{f.get('id')}' does not match filename")
    findings[f.get("id")] = f

register = {}
with open(os.path.join(HERE, "evidence", "evidence-register.csv"), encoding="utf-8") as f:
    for row in csv.DictReader(f):
        register[row["id"]] = row

risks = []
with open(os.path.join(HERE, "risk-register.csv"), encoding="utf-8") as f:
    risks = list(csv.DictReader(f))

# --- 1. finding count and rating totals match the report summary
if len(findings) != sum(EXPECTED_COUNTS.values()):
    errors.append(f"expected {sum(EXPECTED_COUNTS.values())} findings, found {len(findings)}")
counts = {}
for fid, f in findings.items():
    r = f.get("rating")
    if r not in VALID_RATINGS:
        errors.append(f"{fid}: invalid rating '{r}'")
    counts[r] = counts.get(r, 0) + 1
for rating, want in EXPECTED_COUNTS.items():
    got = counts.get(rating, 0)
    if got != want:
        errors.append(f"rating count mismatch: {rating} is {got}, report says {want}")

# --- 2. every referenced evidence id exists, every register file exists on disk
for fid, f in findings.items():
    for ev in f.get("evidence", []):
        if ev not in register:
            errors.append(f"{fid}: evidence id {ev} not in evidence-register.csv")
    if not f.get("evidence") and not f.get("evidence_note"):
        errors.append(f"{fid}: no evidence files and no evidence_note")
for ev, row in register.items():
    if not os.path.exists(os.path.join(HERE, row["file"])):
        errors.append(f"{ev}: file {row['file']} missing from repo")

# --- 3. every High finding is closed by a go-live condition
for fid, f in findings.items():
    cond = f.get("condition")
    if cond not in VALID_CONDITIONS:
        errors.append(f"{fid}: invalid condition '{cond}'")
    if f.get("rating") == "High" and cond == "none":
        errors.append(f"{fid}: rated High but tied to no condition")

# --- 4. risk register rows reference real findings, inherent/target arithmetic holds
for r in risks:
    if r["finding"] not in findings:
        errors.append(f"{r['id']}: references unknown finding {r['finding']}")
    if int(r["L_inherent"]) * int(r["I_inherent"]) != int(r["inherent"]):
        errors.append(f"{r['id']}: inherent score arithmetic wrong")
    if int(r["L_target"]) * int(r["I_target"]) != int(r["target_residual"]):
        errors.append(f"{r['id']}: target residual arithmetic wrong")

# --- 5. every finding appears in the risk register at least once
covered = {r["finding"] for r in risks}
for fid in findings:
    if fid not in covered:
        errors.append(f"{fid}: not mapped to any risk register entry")

if errors:
    for e in errors:
        print("FAIL:", e)
    sys.exit(1)
print(f"OK: {len(findings)} findings, {len(register)} evidence items, {len(risks)} risks, all checks passed")
