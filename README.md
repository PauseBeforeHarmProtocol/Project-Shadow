# Project Shadow

**PROJECT SHADOW 1.0 / R1 REFERENCE / BETA-ACTIVE-TESTING / PRELIVE**

This clean-history repository is the public landing surface for two exact,
separately distributed Project Shadow artifacts. It contains release metadata,
governance evidence, integrity instructions, and nonclaim boundaries. It does
not contain the release ZIPs in Git history; those are attached to their
respective GitHub Releases.

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

## Download order and separation

The optional sidecar is published first under tag `myth-v0.3.4`. The canonical
R1 release is published last under tag `r1-2026-08-14` so that R1 is the latest
release. The sidecar is not embedded in R1, is not an admitted R1 descendant,
does not claim R1 conformance, and is distributed under its own mixed-rights
terms.

## Verify before use

Verify the downloaded ZIP's byte count and SHA-256 before extracting it. Then
run the verifier embedded in the extracted package. Exact Windows, macOS, and
Linux commands are in [`docs/VERIFY_RELEASES.md`](docs/VERIFY_RELEASES.md).

## Scope boundary

Public release is authorized only within `PROJECT SHADOW 1.0 / R1 REFERENCE /
BETA-ACTIVE-TESTING / PRELIVE`. This release does not authorize production or
operational deployment, efficacy, safety, certification, or legal-compliance
claims. See [`docs/SCOPE_AND_NONCLAIMS.md`](docs/SCOPE_AND_NONCLAIMS.md).

## Rights

The R1 archive and the external sidecar each contain controlling notices,
licenses, manifests, and provenance records. The repository does not apply an
outer blanket license to either archive and does not grant third-party rights,
affiliation, endorsement, or legal clearance. Read [`RIGHTS.md`](RIGHTS.md)
before redistribution or adaptation.

