# Evaluation Report

Run the reproducible checks from the repository root:

```powershell
python -m unittest discover -v
python query_test.py
```

## Current pilot baseline

| Capability | Dataset | Expected baseline |
| --- | ---: | ---: |
| Procedure routing | 10 phrasing variants | 10/10 |
| Pre-submission planted errors | 5 submissions | 5/5 cases detect all expected rules |
| Detailed procedure coverage | Pilot catalog | 2 procedures |
| Citation metadata | Logical chunks | Every returned pilot source has `source_url` |

The two pilot procedures are birth registration (`1.001193`) and temporary residence registration (`1.004194`). The suite covers formatting errors, missing documents, date conflicts, address conflicts, missing signatures and guardian consent.

## Next evaluation expansion

- Five ambiguous requests that must trigger clarification.
- Five out-of-scope requests that must not route confidently.
- Five fully valid submissions per procedure to measure false positives.
- Human comparison of every checklist item against the latest official source snapshot.
- Retrieval hit rate and citation coverage reported per procedure version.
