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

## Update 12 Sep (late) — read this first
- Docker Desktop is now RUNNING (engine 29.2.1). Images `eclipse-temurin:21-jdk` and `influxdb:2.9-alpine` are NOT pulled yet (Berk must say yes; ~540 MB total).
- The P02 and P06 agents were cut off mid-work. Their partial output is committed as WIP (see commit "WIP: partial P02 infra and P06 sim"). Status:
  - P02 PARTIAL: energy/infra/docker-compose.yml (189 lines, topology edge→relay:18081→backend-edge:8081→backend:8083, influx), rendered Felix .config files under energy/infra/config/{edge,backend,backend-edge}/, energy/infra/relay/entrypoint.sh, energy/infra/.gitignore. MISSING: scripts/lab_config.py (renderer, may not be needed since configs are rendered), scripts/lab_build (gradle buildEdge buildBackend buildBackendEdge inside temurin container → infra/build-record.json), scripts/lab_run.py (EXP-02 runner: phases prepare→baseline→stop relay→load changes with markers 5217/683 and 1811/4297 W→start relay→poll LastSuccessfulResend ≥66 min→Influx query→evidence/runs/<run_id>/ v2 format with 1 Hz state_trace + SHA256SUMS), experiments/EXP-02.json, tests/test_lab_*.py, infra/README.md. Nothing has been built or started in Docker yet. Check the .config files against io.openems.*/Config.java attribute ids and tools/docker/*/root/var/lib/openems-default-config in C:\Users\Berk\projects\openems-upstream before trusting them. Apikey/influx token must come from a git-ignored infra/.env, never hard-coded.
  - P06 PARTIAL: src/energy_assurance/sim/{__init__,limits,seeding,model}.py (model.py 593 lines: Profile, RunSpec, simulate(spec, limits) → dict; syntax OK, untested). MISSING: sim/scenario.py (outage/reconnect/resend-delay 300+U[0,3600) s, fleet mode), sim/runner.py (serial + ProcessPool parallel, per-run sub-seeds, checkpoint JSONL, deterministic merge, serial==parallel test), benchmarks/bench_scaling.py (strong/weak scaling p=1..16, median/IQR, speedup, efficiency, results JSON), tests/test_sim_*.py. No test has been run against model.py yet.
- Next model: first run the full test suite (expect 101 OK), then finish P06 (pure Python, no Docker needed) and P02 runner code; then, after Berk approves image pulls, build and run EXP-02.
