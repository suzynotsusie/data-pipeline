# Official Data Sources and Presentation

The administrative-procedure datasets bundled with GovEase-AI were collected and normalized from the National Public Service Portal at [dichvucong.gov.vn](https://dichvucong.gov.vn). Source URLs are preserved on procedure records, logical retrieval chunks, form-schema fields and validation issues.

## Frontend rules

1. Display official source links next to generated guidance.
2. Open official sources in a new tab and clearly label the destination.
3. Never present generated explanations as a new regulation or administrative decision.
4. Show a notice that the result is guidance and must be checked before submission.
5. Keep the simulated portal visibly marked as a demo and do not reuse the official national emblem.

## Provenance flow

```text
dichvucong.gov.vn source page
  → structured JSON record
  → logical chunk with source_url
  → retrieval and backend response
  → citation rendered by the frontend
```

Before a production pilot, each source snapshot should also record retrieval time, issuing authority, legal effective dates and reviewer approval as described in `data-governance.md`.
