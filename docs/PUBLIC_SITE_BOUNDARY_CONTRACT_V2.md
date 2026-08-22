# Public site boundary contract v2

This contract is the deterministic public presentation boundary for the six
Project Shadow sites. It separates exact marker and artifact identity checks
from release roles, uniqueness, contradiction rejection, and identity binding.
It is not a natural-language judge and it does not authorize deployment.

## One non-hidden HTML-source release band

Each home route, and the American Repair Manual `/manual.html` route, must
contain exactly one non-hidden HTML-source element with class
`public-release-band` and all of these exact attributes:

| Attribute | Required value |
|---|---|
| `data-shadow-contract` | `public-boundary-v2` |
| `data-shadow-current-release` | `r1.0.1-2026-08-17` |
| `data-shadow-historical-release` | `r1-2026-08-14` |
| `data-shadow-historical-state` | `preserved-superseded` |
| `data-shadow-zero-myth` | `true` |
| `data-shadow-generic-myth-role` | `separate-optional-default-off-nonauthorizing` |
| `data-shadow-full-canon-myth-role` | `separate-optional-default-off-nonauthorizing` |

The same element must contain exactly one direct semantic child for each claim:

| Child attribute | Exact normalized text |
|---|---|
| `data-shadow-claim="release-role"` | Project Shadow R1.0.1 is the current R1 reference. The August 14 R1 release is a preserved historical predecessor superseded by R1.0.1. |
| `data-shadow-claim="sidecar-role"` | Project Shadow 1.0.1 contains no Myth package. Generic Myth v0.2.0 and Full-Canon Myth v0.3.5 are separate optional companions; both default off, neither is required by R1, and neither can authorize action or change an R1 result. |

These are the exact required statements:

> Project Shadow R1.0.1 is the current R1 reference. The August 14 R1 release is a preserved historical predecessor superseded by R1.0.1.

> Project Shadow 1.0.1 contains no Myth package. Generic Myth v0.2.0 and Full-Canon Myth v0.3.5 are separate optional companions; both default off, neither is required by R1, and neither can authorize action or change an R1 result.

Every required band must link to the canonical Project Shadow release and CAPA pages.
Satellite sites must not link directly to a Project Shadow GitHub release from
their home route.

## Bound artifact records

Project Shadow and ALMSIVI must expose each required artifact identity in one
non-hidden HTML-source record per `data-shadow-artifact-id`. The same record
must bind the exact filename, byte count or member count, and SHA-256 in
attributes. It must contain exactly one child whose
`data-shadow-artifact-identity-for` value equals the artifact ID and whose
normalized text exactly equals:

> filename · comma-formatted quantity · SHA-256 digest

| Artifact ID | Filename or member set | Bytes / members | SHA-256 |
|---|---|---:|---|
| `r1_0_1_outer` | `Project_Shadow_R1.0.1_Public_Reference_2026-08-17.zip` | 5,731,663 | `6f6f1e16d5e9a20e62403f14af7ce8629ce2d702528fb7f80aaf4a14deb7a1d1` |
| `r1_0_1_inner` | `Project_Shadow_R1.0.1_Runtime_Family_Myth_Decoupled_2026-08-17.zip` | 5,463,189 | `c8c32b12432c954b1a6f852c0c9f81bbbd40167e936be057d4c3de1a0aa3a623` |
| `generic_myth_v0_2_0` | `Project_Shadow_Generic_Myth_Sidecar_v0.2.0_OPTIONAL_PUBLIC_COMPANION_2026-08-17.zip` | 93,676 | `6e7a362d4135f9d626dcfef463bfb1f7166226b3cf8a4c02a953ab39af1538bf` |
| `full_canon_myth_v0_3_5` | `Project_Shadow_Full_Canon_Myth_Sidecar_v0.3.5_OPTIONAL_PUBLIC_COMPANION_2026-08-17.zip` | 1,428,812 | `2b55867fe7c502a0defd8d6f2e9b53fbd1caaf1b0f225a438bd45b04a3e7bae2` |
| `r1_0_1_operational_member_set` | `R1.0.1 operational member set` | 27 members | `7a557efad953cbafd9e3ea9eb29b2d3e3e1bc6ab99dcf6b9ae7a99c487b0754d` |
| `r1_2026_08_14_predecessor` | `Project_Shadow_R1_Public_Release_Candidate_2026-08-14.zip` | 7,679,812 | `2f8fe1530b6a83294d15011df95853aaecf08fa4dba756f0c2e91dd089e1b1ec` |

The first five records are required on Project Shadow and ALMSIVI. The
preserved predecessor record is additionally required on ALMSIVI.
The complete structured artifact inventory is closed: no additional or
duplicate `data-shadow-artifact-id` is allowed, and every identity child must
be a direct child of its same-ID parent. More generally, every visible
`data-shadow-*` attribute must match one of the exact band, claim, CAPA, or
artifact shapes in this contract; unknown or alternate structured markers fail.

## Current CAPA state

Project Shadow and The Record must publish a non-hidden HTML-source region whose exact
attributes are:

```html
data-shadow-capa-id="PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001"
data-shadow-capa-state="IMPLEMENTED_PENDING_EFFECTIVENESS"
```

The region must contain exactly one child with
`data-shadow-capa-declaration="current-state"` and this exact normalized text:

> CAPA PS-R1-PRIVATE-MYTH-PUBLIC-BOUNDARY-001 current state: IMPLEMENTED_PENDING_EFFECTIVENESS.

The August 18 `CLOSED_EFFECTIVE` event remains historical evidence. It is not
the current state and cannot be reused as the v2 reclosure receipt.

## Verification and replay

The repository verifier rejects explicit HTML hiding, closed `details`, inline
zero-opacity, duplicate attributes, malformed semantic-region nesting,
conflicting structured roles, the enumerated direct reversal and contradiction
fixtures inside or outside the band, contradictory structured CAPA states,
identity misbinding, unknown structured markers, digit-prefix identity tricks,
missing links, skipped checks, and unexpected checks. It does not claim to
recognize every possible natural-language paraphrase. A v2 effectiveness
receipt must retain the exact bounded response bodies, bind the clean verifier
to a reachable Git commit and exact blob hash, record the CAPA state actually
observed, and replay all semantic checks and negative controls offline.

This deterministic layer proves a non-hidden HTML-source contract; it does not
prove browser-computed visibility through external or embedded stylesheets, or
the meaning of every unstructured prose paraphrase.
Reclosure therefore separately requires a retained human review of all six
browser-rendered sites. That review must bind the exact v2 JSON receipt and
response-evidence ZIP and confirm the ordinary visible meaning, release roles,
sidecar roles, CAPA state, and artifact bindings. The causality rule is:

> historical closure < reopening < each route observation <= v2 verification <= human review <= reclosure

After any transition to `CLOSED_EFFECTIVE`, online verification checks the new
live closed-state declaration separately; it does not reinterpret the retained
pending-state receipt. See [`VERIFY_RELEASES.md`](VERIFY_RELEASES.md).
