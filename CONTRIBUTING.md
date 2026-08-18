# Contributing to Project Shadow

Project Shadow welcomes rigorous technical review, documentation corrections,
false-positive and false-negative reports, and adverse results. Outside
criticism is evidence to evaluate, not hostility to suppress.

## Pick one thing to break

You do not need to review the whole system. [Break or reproduce one technical
claim](https://github.com/PauseBeforeHarmProtocol/Project-Shadow/issues/new?template=technical-review.yml),
[correct one exact passage](https://github.com/PauseBeforeHarmProtocol/Project-Shadow/issues/new?template=documentation-correction.yml),
or [report one false positive, false negative, or adverse
result](https://github.com/PauseBeforeHarmProtocol/Project-Shadow/issues/new?template=adverse-result.yml).
Keep the evidence, uncertainty, consequence, and proposed effectiveness check
attached. Report exploitable security findings through the
[private advisory route](https://github.com/PauseBeforeHarmProtocol/Project-Shadow/security/advisories/new).

## Current contact

For corrections, CAPA proposals, research, press, collaboration, conduct, or a
private security fallback, use `projectshadowqa@protonmail.com` with the
subject prefix defined in
[`CONTACT_AND_CORRECTIONS.md`](CONTACT_AND_CORRECTIONS.md).

## Before opening a contribution

1. Read `README.md`, `RIGHTS.md`, `SECURITY.md`,
   `CONTACT_AND_CORRECTIONS.md`, and `docs/SCOPE_AND_NONCLAIMS.md`.
2. Select the matching issue form before proposing a pull request.
3. Use synthetic, non-sensitive evidence wherever possible.
4. Report vulnerabilities privately under `SECURITY.md`; never publish exploit
   details, secrets, personal data, or private evidence in an issue or pull
   request.

## Useful contributions

- reproducible technical-review findings;
- corrections tied to a precise path, statement, and source;
- verifier mutation cases that fail closed;
- false-positive, false-negative, or adverse-result reports;
- correction and CAPA proposals with an effectiveness-check method;
- accessibility, portability, and documentation improvements; and
- narrowly scoped proposals that preserve Project Shadow's governance and
  nonclaim boundaries.

## Custody boundaries

- Do not rewrite, replace, or relabel the existing R1 tag, commit, release
  asset, signed admission record, independent receipt, or preserved candidate
  gate.
- The candidate's internal publication gate remains open by design. The later
  human authorization and derived public status resolve publication above it.
- The Myth sidecar must remain separate, optional, default off, mixed-rights,
  nonauthorizing, and outside R1 conformance.
- A test pass, review approval, merge, tag, or automated workflow never
  self-authorizes publication, production, or operational deployment.
- Do not add efficacy, safety, certification, production-readiness, or
  legal-compliance claims.
- Historical email addresses and certificate identities in preserved evidence
  must not be rewritten merely to match the current contact mailbox.

## Pull requests

Use a focused branch and keep each pull request reviewable. Future changes
should use signed commits, pass all required checks, identify the issue being
closed, and explain the evidence and expected result. Add or update tests when
behavior changes. Maintainer review remains a human governance step.

## Rights of contributions

Eligible original software contributions are accepted under Apache-2.0 unless
clearly stated otherwise. Eligible original documentation and machine-readable
controls are accepted under CC BY 4.0 unless clearly stated otherwise. Do not
submit material you cannot license, private records, or third-party material
without a documented lawful basis and explicit path-scoped treatment. Read
`RIGHTS.md` and `REUSE.toml`; repository packaging never expands rights.

## Conduct

Participation is governed by `CODE_OF_CONDUCT.md`. Challenge claims and
methods directly; do not attack, threaten, expose, or harass people.
