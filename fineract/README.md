# Apache Fineract: third-party risk and control assessment

Assessment of Apache Fineract (open-source core banking) as if a UK retail bank were
onboarding it for a micro-loan product line. The client is hypothetical; the evidence
is real and was collected from public sources on 8 September 2026.

**Opinion: suitable with conditions.** Two High findings (unpatched Tomcat in the
official image, no release-tagged images), four Medium, two Low. Full reasoning is in
[report/Fineract.pdf](report/Fineract.pdf) (v1.2).

## Layout

```
report/       the assessment report (PDF)
findings/     one record per finding (F-01 to F-08): rating, evidence, criteria, owner
evidence/     raw tool output plus evidence-register.csv indexing it
screenshots/  Docker Hub tag search and OpenSSF Scorecard captures
risk-register.csv   R1-R10, inherent and target residual scores
check.py      consistency checks across all of the above
```

## Reproducing the evidence

Tool versions: Trivy 0.74.0, Syft 1.51.1, Scorecard v5.5.0. Run in any Linux
environment (I used GitHub Codespaces):

```
git clone https://github.com/apache/fineract && cd fineract
git checkout 1.15.0
trivy fs --scanners vuln,secret,misconfig .
syft dir:. -o cyclonedx-json
trivy image apache/fineract:latest
docker image inspect apache/fineract:latest
```

Scores and CVE lists will drift as the image is rebuilt daily from develop; the
register records what was true at the collection date.

## Consistency checks

```
python check.py
```

Verifies that finding counts match the report summary, every evidence reference
resolves to a file in the repo, every High finding is tied to a go-live condition,
and the risk register arithmetic holds. Written after I found a counting error in
v1.0 of my own report; the summary said "five Medium and one Low" while the table
said four and two. Fixed in v1.1, and now a script catches that class of mistake.

## Findings

| ID | Finding | Rating |
|----|---------|--------|
| F-01 | Official image ships Tomcat 10.1.55 with 3 critical CVEs, 8 high in deps | High |
| F-02 | No release-tagged container images; latest tracks develop | High |
| F-03 | DB bootstrap grants root full rights from any host | Medium |
| F-04 | Sample manifests run with default security context | Medium |
| F-05 | Manifests have no stated purpose (demo vs production) | Low |
| F-06 | CI tokens over-permissioned, partial branch protection | Medium |
| F-07 | No SAST or fuzzing in the project pipeline | Medium |
| F-08 | DB password on the command line in health probes | Low |

Requests to the project (section 8.3 of the report) will go to the Fineract dev
mailing list. Nothing here needed private disclosure; no previously unknown
vulnerability was found.
