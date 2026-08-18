**PUBLISHED · PACKAGING-BOUNDARY CORRECTION · BETA-ACTIVE-TESTING · PRELIVE**

# Project Shadow 1.0.1 — R1 Reference Packaging Correction

**Tag:** `r1.0.1-2026-08-17`

**Asset:** `Project_Shadow_R1.0.1_Public_Reference_2026-08-17.zip`

**Bytes:** 5,731,663

**SHA-256:** `6f6f1e16d5e9a20e62403f14af7ce8629ce2d702528fb7f80aaf4a14deb7a1d1`

The values above identify the final deterministic outer archive. The maintainer
separately authorized this exact filename, byte count, SHA-256, and tag, and the
artifact is published on GitHub and Hugging Face. Publication is not anonymous
redownload identity evidence and does not close the CAPA.

## What this corrects

R1.0.1 removes the older Generic Myth v0.1.1 package from the public R1
runtime-family container. That member was physically present in the preserved
August 14 R1 archive even though its own metadata classified it as non-public,
excluded it from public manufacture, and marked it default off.

The August 14 release remains immutable historical evidence. It has not been
edited, replaced, renamed, or silently reissued. R1.0.1 is a separately
versioned successor that corrects the packaging boundary.

## What does not change

All 27 active operational descendants must remain byte-identical to the August
14 predecessor. Their canonical path-and-identity digest is:

`7a557efad953cbafd9e3ea9eb29b2d3e3e1bc6ab99dcf6b9ae7a99c487b0754d`

Primitive Commons beta.5 must also remain byte-exact. No operational artifact
byte, evidence rule, gate, profile contract, authority boundary, or PRELIVE
nonclaim may change.

The corrected inner runtime-family archive is:

- `Project_Shadow_R1.0.1_Runtime_Family_Myth_Decoupled_2026-08-17.zip`
- 5,463,189 bytes
- SHA-256 `c8c32b12432c954b1a6f852c0c9f81bbbd40167e936be057d4c3de1a0aa3a623`
- 27 active descendants; zero operational descendant bytes changed; no Myth
  payload embedded

The maintainer admitted this exact inner identity for R1.0.1 reference
packaging. That scoped admission expressly does not authorize production,
deployment, or publication.

## Myth is optional and external

R1.0.1 contains no Myth payload. Project Shadow remains inspectable,
verifiable, and evaluable within its stated PRELIVE scope without either
sidecar.

Two separately published companions are available only by explicit choice:

- Generic Myth Sidecar v0.2.0 — optional, default off, terminal-only, and
  nonauthorizing.
- Full-Canon Myth Sidecar v0.3.5 — optional, default off, terminal-only, and
  nonauthorizing.

Neither is part of, required by, embedded in, or enabled by default in R1.
Neither can supply evidence, authority, a gate result, score, routing input,
tool argument, approval, or action. No companion is authorized for production
or operational deployment.

## CAPA state

CAPA `PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001` is implemented pending
effectiveness. Closure requires anonymous public redownload identity checks on
GitHub and Hugging Face and corrected live wording across all six public
Project Shadow sites.

## Verify the exact asset

Verify the byte count and SHA-256 before extraction and run the
verification-only script included in the archive:

```bash
python3 -I -S -B tools/verify_outer_release.py \
  Project_Shadow_R1.0.1_Public_Reference_2026-08-17.zip
```

A verifier pass establishes only the implemented custody, integrity, schema,
regression, and bounded compatibility checks. It does not establish safety,
efficacy, certification, legal compliance, production suitability, or
authority for deployment or action.

Download only the explicitly named asset. GitHub's automatically generated
`Source code (zip)` and `Source code (tar.gz)` archives are repository
snapshots, not the Project Shadow R1.0.1 release.
