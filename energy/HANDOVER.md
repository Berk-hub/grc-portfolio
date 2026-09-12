# Energy Lab — handover (12 Sep 2026)

Read this, then STATUS.md, then only the active package in ENERGY_LAB_UYGULAMA_VE_DEVIR_PLANI.md (kept in C:\Users\Berk\projects\ENERGY_LAB_PLAN.md, outside the repo). Reply to Berk in Turkish, short. Docs in plain English.

## Where things are
- Local clone: C:\Users\Berk\projects\grc-portfolio, branch `energy-v2` (pushed). `main` untouched; merge only after Berk reviews.
- OpenEMS source: C:\Users\Berk\projects\openems-upstream, detached at 189ac916 (not built).
- Python: C:\Users\Berk\AppData\Local\Python\pythoncore-3.14-64\python.exe. Run from energy/: `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`; CLI: `python -m energy_assurance.cli validate|assess|verify-manifest`.
- Git identity for commits: `-c user.name="Berk Ozcan" -c user.email="235576595+Berk-hub@users.noreply.github.com"`; end messages with `Co-Authored-By: Claude ... <noreply@anthropic.com>` (plan rule 12: never hide AI use). Push works non-interactively (`git push origin energy-v2`). Never force-push, never edit evidence/backend-loss/.
- Working tree is LF (core.autocrlf false, core.eol lf). Keep LF.
- Machine: Windows 11, 16 CPU, 15.4 GB RAM, Docker Desktop (must be started by Berk), Java 8 only → build/run OpenEMS inside Docker (eclipse-temurin:21-jdk). Codespace is dead; do everything locally.

## Done (VERIFIED)
- P00 b1f2f12: Appendix A patch applied; 29 tests.
- P01 7c5bf69: evaluator v2 (SC-03 INCONCLUSIVE on snapshot evidence; `--evaluator v1` reproduces v1.0), dictionary-driven limits, schema checks, manifest hygiene, `assess --expect`; CI uses `--expect INCONCLUSIVE`; 101 tests.
- P04 4a14c52: data/service-model.json + docs/18-service-model.md.

## In flight (agents were writing into the working tree; check `git status`, verify, then commit)
- P02 (files: energy/infra/**, scripts/lab_*.py, experiments/EXP-02.json, tests/test_lab_*.py). Verify: tests pass; no secrets; compose has no hard-coded apikey/token.
- P06 (files: src/energy_assurance/sim/**, benchmarks/**, tests/test_sim_*.py). Verify: tests pass; serial==parallel; benchmark JSON present.
If either agent's output is missing or broken, re-run that package from the plan text.

## Remaining, in order (gates from the plan + 12 Sep panel)
1. P02 execute: Berk starts Docker Desktop and approves pulls of `eclipse-temurin:21-jdk` (~450MB) and `influxdb:2.9-alpine` (~90MB). Then `scripts/lab_build` (three gradle tasks in container; record sha256 → infra/build-record.json; compare to config/openems-upstream-lock.json and note that evidence/build/openems-edge-baseline.md holds a stale earlier hash 9cbbbb55), `docker compose up`, readiness checks. UNVERIFIED from source: Backend-Edge-App apikey acceptance timing → retry.
2. P03 EXP-02: run `scripts/lab_run.py --experiment experiments/EXP-02.json`. Requirements: 1 Hz state trace (v2 evidence), distinctive markers (5217/683, 1811/4297 W), observation ≥ 66 min after reconnection until LastSuccessfulResend non-null, structured Influx query → evidence/runs/<run_id>/14-influx-post-resend.json, RRD capture after a 300 s boundary, manifest. Then `assess` on the new run (v2). Update findings.json FND-REC-001 from the result (CANDIDATE → CONFIRMED/REJECTED only with evidence). Keep v1 evidence untouched.
3. P05: network faults via docker (silent drop with iptables/tc in a netns or `docker network disconnect`, latency/loss), stale meter (EXP-05), Edge restart, second site (two edge containers). Each scenario: expected vs observed vs evidence link; injection verified separately.
4. P07: on P06 outputs + P03/P05 runs: repeated reconnections (≥30) to estimate resend-delay distribution, CIs, sensitivity analysis, tail risk; unit of analysis = independent run. Report in docs/19-quantitative-analysis.md with reproducible script.
5. P08 only if Berk approves budget; otherwise IaC prepared, NOT TESTED.
6. P09: reconcile models: add docs/17 Findings 3–4 to findings.json; SC-03 wording everywhere = evaluator-versioned; RRD4J "intact" claim withdrawn until measured; audit-program evidence path `.github/workflows/assurance.yml` → `../.github/...`; pyproject name → grc-portfolio-energy; README key documents list docs 10–18; RELEASE_NOTES tag names → energy-v1.1.0 / next.
7. P10: regenerate the two Energy PDFs from docs/16 and docs/17 (HTML via python-markdown + Edge headless: see reports/ pipeline in chat history — `msedge --headless --print-to-pdf`), update root README status, clean rerun of tests + CI green, then Berk merges energy-v2 → main and tags energy-v1.2.0.

## Rules that must not slip
Results vocabulary only SUPPORTED/NOT SUPPORTED/INCONCLUSIVE/NOT TESTED; simulator output ≠ OpenEMS observation; single host ≠ physical independence; no secrets in repo; no "done" while a package is open; every number in a doc traceable to a file.
