# Data and Privacy Governance

## Administrative sources

Procedure records are derived from public administrative-procedure sources and retain `source_url` metadata. Each production update should record retrieval time, effective dates, issuing authority and a data version before replacing the active Chroma collection.

Every detailed pilot record must include:

- `source.source_url` and `source.extracted_at`;
- `governance.review_status`, `reviewed_at`, `reviewer`, and `freshness_days`;
- explicit scope exclusions so the assistant does not silently apply one procedure to another case.

`pending_human_review` is intentionally visible and must not be described as approved or current. A production promotion requires `review_status=approved`, a named reviewer role, and `reviewed_at` after the source extraction time.

## Update workflow

1. Download and archive the source snapshot.
2. Normalize it into a structured procedure record.
3. Review required documents, steps, form fields and validation rules.
4. Run the evaluation suite.
5. Build a new versioned Chroma collection.
6. Promote the collection only after review; never reset the active production collection in place.

## Personal data

- Do not log submission bodies, identity numbers, addresses or document content.
- Do not persist `/validate` requests by default.
- Use TLS and a scoped integration API key in production.
- Set short log retention and restrict operator access.
- Send only the minimum necessary fields to the optional semantic LLM layer.

The service provides administrative guidance, not a legal decision. The frontend must show the official source and a notice to verify information before submission.
