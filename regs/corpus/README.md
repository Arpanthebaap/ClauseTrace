# Regulatory corpus — synthetic, illustrative only

**Important:** the files in this folder are **original, paraphrased, illustrative text**
written for this prototype. They are *not* verbatim excerpts of any RBI Master Direction,
the PMLA 2002 & Rules, Basel III text, or any other real regulatory publication, and they
must not be treated as authoritative or cited outside this demo.

In a real deployment, this folder is replaced by the institution's actual, licensed/public
regulatory text (RBI circulars are public domain; internal policy documents would be
ingested under the institution's own document-governance rules), parsed with CoCo's
document-processing capability (chunking, embedding, and clause-level ID assignment) so that
`Regulatory Mapping Skill` and `Evidence & Citation Skill` can cite a real, verifiable
section number.

Each file below uses a stable `clause_id` so the semantic view and skills can join a finding
to a specific, citable clause — that ID scheme is what actually matters for the demo, not the
illustrative wording.

| File | Illustrative topic | Clause ID prefix |
|---|---|---|
| `kyc_customer_due_diligence.md` | Customer due diligence / risk categorisation | `KYC-CDD-*` |
| `aml_structuring_reporting.md` | Structuring / suspicious transaction reporting | `AML-STR-*` |
| `basel_liquidity_disclosure.md` | Liquidity coverage ratio disclosure | `BASEL-LCR-*` |
