# Project Shadow

> **Mixed-rights repository.** This repository is not one blanket
> Apache-2.0 work. Apache-2.0 applies only to eligible original software;
> CC BY 4.0 applies only to eligible original documentation and
> machine-readable controls. Preserved governance evidence and release
> archives retain their own attached or path-scoped terms. Read
> [`RIGHTS.md`](RIGHTS.md) before reuse.

**PROJECT SHADOW 1.0.1 / R1 REFERENCE / BETA-ACTIVE-TESTING / PRELIVE**

Project Shadow 1.0.1 is the corrected current R1 reference. It removes Myth
from the R1 runtime-family package while preserving all 27 active operational
descendants byte-for-byte. Generic Myth v0.2.0 is published separately as an
optional companion, the exact Myth-free inner family is admitted, and the final
R1.0.1 outer identity has its own exact-hash publication authorization.

Generic Myth v0.2.0 and R1.0.1 now exist as public GitHub and Hugging Face
releases. Anonymous redownload identity verification and six-site effectiveness
checks remain pending. The machine-readable phase is
[`POSTPUBLICATION`](PUBLIC_RELEASE_STATUS_2026-08-17.json), and CAPA
`PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001` remains open.

## Current contact

All new Project Shadow correspondence should use
**`projectshadowqa@protonmail.com`**.

Use `[CORRECTION]`, `[CAPA]`, `[SECURITY]`, `[RESEARCH]`, `[PRESS]`,
`[COLLABORATION]`, or `[CONDUCT]` in the subject line. See
[`CONTACT_AND_CORRECTIONS.md`](CONTACT_AND_CORRECTIONS.md).

Historical addresses and certificate identities may remain inside exact-hash,
signed, frozen, or quoted evidence. They are custody evidence, not current
contact routes.

## Release state

| Artifact | State | Boundary |
|---|---|---|
| R1, 2026-08-14 | Preserved historical release; superseded as the current reference | Contains a historically nested Generic Myth v0.1.1 member whose own metadata was non-public; the released bytes remain immutable evidence |
| Full-Canon Myth v0.3.4 | Preserved historical optional sidecar | External, default off, nonauthorizing |
| Full-Canon Myth v0.3.5 | Published optional companion | External, default off, terminal-only, nonauthorizing |
| Generic Myth v0.2.0 (`generic-myth-v0.2.0`) | Published optional companion | Separate, default-off, terminal-only, nonauthorizing; never embedded in R1 |
| R1.0.1 (`r1.0.1-2026-08-17`) | Published corrected current reference | Publication contract requires zero Myth payload |

The exact historical, published, authorized, and frozen identities are in
[`PUBLICATION_MANIFEST.json`](PUBLICATION_MANIFEST.json). A concrete identity
does not by itself authorize publication; consult its authority record and
publication state.

## Myth is optional

Project Shadow does not require Myth. Both Myth companions are separate,
explicitly enabled, default-off presentation layers. Neither can provide
evidence, authority, a gate result, score, routing input, tool argument,
approval, or action. No companion is authorized for production or operational
deployment.

- **Generic Myth Sidecar v0.2.0** is a generic mnemonic presentation with no
  named third-party expressive material. Its frozen exact-hash build has passed
  final tests and is published separately on GitHub and Hugging Face.
- **Full-Canon Myth Sidecar v0.3.5** is an optional mixed-rights interpretive
  companion published separately from R1.

R1.0.1 contains neither sidecar. The August 14 bytes are preserved rather
than silently edited; the correction is a separately versioned successor.

## Verify before use

Run the repository evidence verifier for the current lifecycle phase:

```bash
python3 -I -S -B tools/verify_repository_evidence.py --phase postpublication
```

This validates the published identities, scoped authorities, optional-sidecar
boundaries, and current open CAPA state. Online mode additionally redownloads
the exact GitHub assets and checks live release metadata; it does not create the
missing Hugging Face redownload receipt, establish six-site effectiveness, or
close the CAPA:

```bash
python3 -I -S -B tools/verify_repository_evidence.py --phase postpublication \
  --online --download-dir /tmp/project-shadow-release-assets
```

Exact Windows, macOS, and Linux instructions are in
[`docs/VERIFY_RELEASES.md`](docs/VERIFY_RELEASES.md). The historical
[`tools/verify_public_release.py`](tools/verify_public_release.py) remains
pinned to the August 14 artifact; it is not silently retargeted to R1.0.1.

## CAPA state

CAPA `PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001` is
**IMPLEMENTED_PENDING_EFFECTIVENESS**. Closure requires exact public GitHub and
Hugging Face redownload identity checks for the corrected artifacts plus live
verification of the six Project Shadow public sites. See the
[`CAPA record`](governance/CAPA_PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001_2026-08-17.json).
Only after those criteria are evidenced may this state become
`CLOSED_EFFECTIVE`.

## Scope boundary

This work remains `BETA-ACTIVE-TESTING / PRELIVE`. It does not authorize
production or operational deployment and does not claim efficacy, safety,
certification, or legal compliance. See
[`docs/SCOPE_AND_NONCLAIMS.md`](docs/SCOPE_AND_NONCLAIMS.md).

Current sole-maintainer authority, the absence of a designated successor, the
non-authority of AI and automation, and the fail-closed stale-after date are
recorded in
[`governance/MAINTAINER_CONTINUITY.md`](governance/MAINTAINER_CONTINUITY.md).

## Participate and challenge

Technical criticism, correction evidence, false positives, false negatives,
and adverse results are welcome. Start with
[`CONTRIBUTING.md`](CONTRIBUTING.md), use the matching issue form, or email the
current contact with the appropriate subject prefix. Report vulnerabilities
privately under [`SECURITY.md`](SECURITY.md).
