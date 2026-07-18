# Form Validation Sources

The birth-registration controls deliberately distinguish legal facts from demo heuristics.

- The province dropdown follows the 34 provincial-level administrative units effective from 1 July 2025 under Decision 19/2025/QĐ-TTg. The same official catalog contains 3,321 commune-level units, but the current UI does not yet implement a cascading commune selector. It must not be described as a complete address catalog. There is no district-level tier in this two-level catalog.
- A personal identification number is checked only for presence and the public 12-digit format. GovEase does not infer or validate the first digits. In the target integration, identity data comes from the authenticated VNeID/National Public Service Portal session; manual entry remains only as a standalone-demo fallback.
- The requester relationship list follows the explicit family/caregiver groups in Article 15 of the 2026 Civil Status Law.
- Possible Telex residue such as `Nguyeenx` is a warning heuristic. It asks the citizen to compare the value with the original document; it is not represented as a legal rule.

Official references:

- Government administrative-unit catalog: https://xaydungchinhsach.chinhphu.vn/bang-danh-muc-va-ma-so-cua-34-tinh-thanh-moi-cac-don-vi-hanh-chinh-cap-xa-moi-11925070418263625.htm
- Official catalog of 3,321 commune-level units: https://xaydungchinhsach.chinhphu.vn/danh-sach-3321-don-vi-hanh-chinh-cap-xa-tai-34-tinh-thanh-sau-sap-xep-sap-nhap-119250710102358656.htm
- Civil Status Law 03/2026/QH16: https://xaydungchinhsach.chinhphu.vn/toan-van-luat-ho-tich-so-03-2026-qh16-119260527163142286.htm

## Effective-date warning

Law 03/2026/QH16 was passed on 23 April 2026 but takes effect on 1 March 2027. Until then, it is a future-law integration target, not the legal basis for claiming the current pilot procedure is already governed by its provisions. Its principles on one-time data provision and proactive database lookup are used only to shape the integration architecture.
