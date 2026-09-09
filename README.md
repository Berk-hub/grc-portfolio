# grc-portfolio

Third-party risk and control assessments of open-source systems, written the way a
regulated firm would commission them: a hypothetical but realistic client, a stated
regulatory perimeter, evidence collected with standard tooling, and an opinion the
evidence can actually carry.

I'm a computer science student at Leeds working toward technology risk / GRC roles.
These assessments are how I practise the discipline end to end: scoping, evidence,
rating criteria fixed before findings, compliance mapping against named framework
versions, and honest limitations sections.

| Assessment | Sector | Frameworks | Opinion | Status |
|---|---|---|---|---|
| [Apache Fineract](fineract/) — core banking platform | Finance | PRA SS2/21, FCA SYSC 15A, DORA, ISO 27001:2022, NIST CSF 2.0 | Suitable with conditions | Done |
| BBC micro:bit radio protocol | IoT / education | — | — | In progress |
| [OpenEMS energy resilience lab](energy/) — energy management system | Energy | NCSC CAF v4.0, UK NIS, NIS2 | Reasonable assurance on design, limited on operating effectiveness | Done |

The OpenEMS entry works the other way round from the others: I built the laboratory
first, then reviewed my own build with the same discipline — separate opinions on
design and effectiveness, a residual-risk register, a CAF self-assessment, and a
self-review caveat applied throughout. The full laboratory (code, evidence, models,
CI) lives in this repository under
[energy/](energy/).

## Ground rules

- Every claim traces to evidence in the repo (tool output, screenshots, or a named
  file and line in the assessed source). Each assessment ships an evidence register
  and a `check.py` that verifies internal consistency.
- Clients are hypothetical and clearly labelled as such. No real institution's data
  is used; everything comes from public sources.
- Ratings can disagree with scanner severity, but the report has to say why.
- Regulatory mappings name the version and effective date of the text they map
  against, and say when applicability is an assumption rather than a determination.
