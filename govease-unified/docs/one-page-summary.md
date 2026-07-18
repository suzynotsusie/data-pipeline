# GovEase-AI — One-page Summary

## Problem

Citizens often do not know which administrative procedure applies, what documents to prepare or whether a form is internally consistent. Errors are discovered only after review, creating repeat visits and avoidable support load.

## Solution

GovEase-AI combines an integration-ready FastAPI service with a Next.js portal simulation and embeddable widget. It converts a plain-language need into a sourced checklist, exposes a machine-readable form schema, and checks completed information with deterministic rules plus an optional semantic LLM review. Public procedure data is retrieved through Chroma and every pilot answer retains links to its official source.

## Target users

- Citizens completing procedures without specialist knowledge.
- Portal teams that need an API rather than another standalone application.
- Public-service staff seeking fewer repetitive questions and incomplete submissions.

## Pilot

The pilot covers birth registration and temporary residence registration end to end: need description, clarification, checklist, generated form and field-level validation. The frontend consumes `/api/v1`, includes a public-service portal simulation, and exposes an iframe widget for integration demonstrations.

## Deployment roadmap

1. Deploy the API on Render with a persistent Chroma disk and restricted CORS.
2. Integrate the independent demo frontend using the published OpenAPI contract.
3. Pilot the two procedures with one receiving authority and review anonymized outcome metrics.
4. Establish a source-review and version-promotion workflow.
5. Add procedures by sector only after each one passes the same accuracy and validation evaluation.

## Success measures

Procedure-routing accuracy, required-document recall, planted-error detection, false-positive rate, citation coverage and reduction in repeat submissions.
