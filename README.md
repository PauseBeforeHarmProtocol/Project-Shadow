# Project Shadow

> **Mixed-rights repository.** This repository is not one blanket
> Apache-2.0 work. Apache-2.0 applies only to eligible original software;
> CC BY 4.0 applies only to eligible original documentation and
> machine-readable controls. Preserved governance evidence and both release
> archives retain their own attached or path-scoped terms. Read
> [`RIGHTS.md`](RIGHTS.md) before reuse.

**PROJECT SHADOW 1.0 / R1 REFERENCE / BETA-ACTIVE-TESTING / PRELIVE**

This clean-history repository is the public landing surface for two exact,
separately distributed Project Shadow artifacts. It contains release metadata,
governance evidence, integrity instructions, and nonclaim boundaries. It does
not contain the release ZIPs in Git history; those are attached to their
respective GitHub Releases.

## Current contact

All new Project Shadow correspondence should use
**`projectshadowqa@protonmail.com`**.

Use `[CORRECTION]`, `[CAPA]`, `[SECURITY]`, `[RESEARCH]`, `[PRESS]`,
`[COLLABORATION]`, or `[CONDUCT]` in the subject line. The full intake and
privacy rules are in
[`CONTACT_AND_CORRECTIONS.md`](CONTACT_AND_CORRECTIONS.md), with a
machine-readable status in
[`PUBLIC_CONTACT_STATUS_2026-08-17.json`](PUBLIC_CONTACT_STATUS_2026-08-17.json).

Historical addresses and certificate identities may remain inside exact-hash,
signed, frozen, or quoted evidence. They are preserved for custody and
verification and are not current contact routes.

## Exact releases

| Artifact | Role | Bytes | SHA-256 |
|---|---|---:|---|
| `Project_Shadow_R1_Public_Release_Candidate_2026-08-14.zip` | Canonical R1 reference release | 7,679,812 | `2f8fe1530b6a83294d15011df95853aaecf08fa4dba756f0c2e91dd089e1b1ec` |
| `Project_Shadow_Full_Canon_Myth_Sidecar_v0.3.4_OPTIONAL_EXTERNAL_RESEARCH_2026-08-14.zip` | Optional external research sidecar; separate from R1 and default off | 1,418,194 | `3c8c8c0d3d9582c76b685c1b685260cc8179478ab310037c858b46257aa314c7` |

The R1 filename retains the word `Candidate` because publication preserves the
authorized bytes exactly. The archive's internal status was written before the
separate exact-hash authorization. That external authorization is recorded in
[`governance/RELEASE_AUTHORIZATION_2026-08-14.json`](governance/RELEASE_AUTHORIZATION_2026-08-14.json).
The archive itself must not be rewritten to change its internal status.
The resolved, machine-readable state above that preserved gate is recorded in
[`PUBLIC_RELEASE_STATUS_2026-08-14.json`](PUBLIC_RELEASE_STATUS_2026-08-14.json).
The historical unsigned commit/tag facts and the later commit-bound attestation
are recorded in
[`governance/POST_PUBLICATION_ATTESTATION_2026-08-15.json`](governance/POST_PUBLICATION_ATTESTATION_2026-08-15.json).

## Download order and separation

The optional sidecar is published first under tag `myth-v0.3.4`. The canonical
R1 release is published last under tag `r1-2026-08-14` so that R1 is the latest
release. The sidecar is not embedded in R1, is not an admitted R1 descendant,
does not claim R1 conformance, and is distributed under its own mixed-rights
terms.

## Verify before use

Verify the downloaded ZIP's byte count and SHA-256 before extracting it. Then
run the current repository verifier against the outer ZIP so its prospective
archive-preflight limits apply, followed by the frozen verifier embedded in the
extracted package. Exact Windows, macOS, and Linux instructions are in
[`docs/VERIFY_RELEASES.md`](docs/VERIFY_RELEASES.md).

## Scope boundary

Public release is authorized only within `PROJECT SHADOW 1.0 / R1 REFERENCE /
BETA-ACTIVE-TESTING / PRELIVE`. This release does not authorize production or
operational deployment, efficacy, safety, certification, or legal-compliance
claims. See [`docs/SCOPE_AND_NONCLAIMS.md`](docs/SCOPE_AND_NONCLAIMS.md).

Current sole-maintainer authority, the absence of a designated successor, the
non-authority of AI and automation, and the fail-closed stale-after date are
recorded in
[`governance/MAINTAINER_CONTINUITY.md`](governance/MAINTAINER_CONTINUITY.md).

## Rights

The R1 archive and the external sidecar each contain controlling notices,
licenses, manifests, and provenance records. The repository does not apply an
outer blanket license to either archive and does not grant third-party rights,
affiliation, endorsement, or legal clearance. Read [`RIGHTS.md`](RIGHTS.md)
before redistribution or adaptation.

## Participate and challenge

Technical criticism, correction evidence, false positives, false negatives,
and adverse results are welcome. Outside criticism is evidence to evaluate,
not hostility to suppress. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md), use
the matching issue form, or email `projectshadowqa@protonmail.com` with the
appropriate subject prefix. Report vulnerabilities privately under
[`SECURITY.md`](SECURITY.md); never place exploit details or private evidence
in a public issue.
