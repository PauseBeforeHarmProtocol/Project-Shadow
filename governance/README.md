# Governance evidence

This directory separates two kinds of evidence:

1. The exact admission record, its Sigstore bundle, and the independent
   signature-verification receipt establish the signature and external-time
   gates for the admitted record.
2. `RELEASE_AUTHORIZATION_2026-08-14.json` records the later, separate
   maintainer authorization for the exact R1 and v0.3.4 sidecar hashes.

The signed admission record did not self-authorize public release. The later
authorization does not modify the signed record or the exact R1 archive; it
satisfies the external publication gate for the named artifacts only.

## Exact evidence identities

| Evidence | Bytes | SHA-256 |
|---|---:|---|
| Admission record | 217,626 | `659d15bf371a1c2b8410d39c040733da43779fbe54730c43140e1d06dc70b424` |
| Sigstore bundle | 6,770 | `a579f1b855ad22eb58be4ece5a580edbff60a171b35517b15ee172e417faaba0` |
| Independent verification receipt | 1,625 | `62e3965891b0f0a11aa46b50854f467acef84645faa569419fc79cf1051c1629` |
| Public-release authorization receipt | 1,995 | `af9e049c73b57224aaa49683908ff8cdd33d744aa538c89f883ee6c75ab2f547` |

The public-release authorization receipt is a session record and makes no
claim of having its own cryptographic signature.
