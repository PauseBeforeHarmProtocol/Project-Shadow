**PUBLIC R1 REFERENCE · PACKAGING-BOUNDARY CORRECTION · BETA-ACTIVE-TESTING · PRELIVE**

# Project Shadow 1.0.1 — R1 Reference Packaging Correction

**Tag:** `r1.0.1-2026-08-17`
**Asset:** `Project_Shadow_R1.0.1_Public_Reference_2026-08-17.zip`
**Bytes:** `5,731,663`
**SHA-256:** `6f6f1e16d5e9a20e62403f14af7ce8629ce2d702528fb7f80aaf4a14deb7a1d1`

## What this corrects

R1.0.1 removes the older generic Myth v0.1.1 package from the public R1 runtime-family container. That component was physically present in the preserved August 14 R1 archive even though its own admission metadata classified it as private/internal-only, excluded it from public manufacture, and marked it default-off.

The August 14 release remains immutable historical evidence. It has not been edited, replaced, renamed, or silently reissued. R1.0.1 is a separately versioned successor that corrects the packaging boundary.

## What did not change

All 27 active operational descendants are byte-identical to the August 14 predecessor. Their canonical path-and-identity digest remains:

`7a557efad953cbafd9e3ea9eb29b2d3e3e1bc6ab99dcf6b9ae7a99c487b0754d`

Primitive Commons beta.5 is also preserved byte-exact. No operational artifact byte, evidence rule, gate, profile contract, authority boundary, or PRELIVE nonclaim was changed.

The corrected inner runtime-family archive is:

- `Project_Shadow_R1.0.1_Runtime_Family_Myth_Decoupled_2026-08-17.zip`
- `5,463,189` bytes
- SHA-256 `c8c32b12432c954b1a6f852c0c9f81bbbd40167e936be057d4c3de1a0aa3a623`
- 27 active descendants; zero operational descendant bytes changed; no Myth payload embedded

## Myth is optional and external

R1.0.1 contains no Myth payload. Project Shadow remains fully inspectable, verifiable, evaluable, and usable within its stated PRELIVE scope without either sidecar.

Two separately published companions are available only by explicit choice:

- [**Generic Myth Sidecar v0.2.0**](https://github.com/PauseBeforeHarmProtocol/Project-Shadow/releases/tag/generic-myth-v0.2.0) — licensed public successor to eligible generic material; optional, default off, terminal-only, nonauthorizing. Exact asset: `93,676` bytes; SHA-256 `6e7a362d4135f9d626dcfef463bfb1f7166226b3cf8a4c02a953ab39af1538bf`.
- [**Full-Canon Myth Sidecar v0.3.5**](https://github.com/PauseBeforeHarmProtocol/Project-Shadow/releases/tag/myth-v0.3.5) — mixed-rights interpretive companion; optional, default off, terminal-only, nonauthorizing. Exact asset: `1,428,812` bytes; SHA-256 `2b55867fe7c502a0defd8d6f2e9b53fbd1caaf1b0f225a438bd45b04a3e7bae2`.

Neither is part of, required by, embedded in, or enabled by default in R1. Neither can supply evidence, authority, a gate result, score, routing input, tool argument, approval, or action, and neither is authorized for production or operational deployment.

## CAPA state

CAPA `PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001` is implemented by this successor but remains **pending effectiveness** until independent public redownload checks confirm the exact GitHub and Hugging Face bytes and the corrected state is verified across the public Project Shadow surfaces. Closure evidence will be added without rewriting this release.

## Verify the exact asset

Download both explicitly named R1.0.1 assets:

- `Project_Shadow_R1.0.1_Public_Reference_2026-08-17.zip`
- `Project_Shadow_R1.0.1_Public_Reference_2026-08-17.zip.sha256.txt`

Verify the byte count and SHA-256 before extraction:

```bash
sha256sum -c Project_Shadow_R1.0.1_Public_Reference_2026-08-17.zip.sha256.txt
```

Then extract only to obtain the included read-only verifier and run it against the original ZIP:

```bash
unzip -q Project_Shadow_R1.0.1_Public_Reference_2026-08-17.zip -d project-shadow-r1.0.1-verifier
python3 -I -S -B \
  project-shadow-r1.0.1-verifier/Project_Shadow_R1.0.1_Public_Reference_2026-08-17/tools/verify_outer_release.py \
  Project_Shadow_R1.0.1_Public_Reference_2026-08-17.zip
```

The release was built twice with byte-identical output. Its corrected inner component was independently built twice and subjected to runtime replay, checksum, admission-carry-forward, recursive payload, archive-safety, and adversarial mutation checks.

A verifier PASS establishes only the implemented custody, integrity, schema, regression, and bounded compatibility checks. It does not establish safety, efficacy, certification, legal compliance, R1 production readiness, or authority for deployment or action.

Download the explicitly named asset. GitHub's automatically generated source ZIP and TAR archives are repository snapshots, not the Project Shadow R1.0.1 release.
