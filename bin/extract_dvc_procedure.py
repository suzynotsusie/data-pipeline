#!/usr/bin/env python3
"""Extract procedure information from dichvucong.gov.vn procedure URLs.

Usage:
    python extract_dvc_procedure.py <url>
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import ssl
from dataclasses import dataclass, asdict
from html import unescape
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass
class ProcedureData:
    url: str
    procedure_id: str | None = None
    ma_so: str | None = None
    title: str | None = None
    issuing_agency: str | None = None
    implementing_agency: str | None = None
    sector: str | None = None
    summary: str | None = None
    raw_source: str | None = None


def _http_get(url: str, timeout: int = 30) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": "https://www.google.com/",
    }
    req = Request(url, headers=headers)

    # Some environments need a permissive SSL context to avoid TLS handshake issues.
    context = ssl.create_default_context()
    with urlopen(req, timeout=timeout, context=context) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def _http_post_json(url: str, payload: dict, timeout: int = 30) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json; charset=UTF-8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    data = json.dumps(payload).encode('utf-8')
    req = Request(url, data=data, headers=headers, method="POST")
    context = ssl.create_default_context()
    with urlopen(req, timeout=timeout, context=context) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def _extract_json_ld(html: str) -> list[dict[str, Any]]:
    pattern = re.compile(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    results: list[dict[str, Any]] = []
    for m in pattern.finditer(html):
        payload = m.group(1).strip()
        if not payload:
            continue
        try:
            obj = json.loads(payload)
            if isinstance(obj, dict):
                results.append(obj)
            elif isinstance(obj, list):
                results.extend([x for x in obj if isinstance(x, dict)])
        except json.JSONDecodeError:
            continue
    return results


def _extract_next_data(html: str) -> dict[str, Any] | None:
    m = re.search(
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return None
    payload = m.group(1).strip()
    if not payload:
        return None
    try:
        obj = json.loads(payload)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _extract_meta(html: str, key: str) -> str | None:
    for pattern in (
        rf'<meta[^>]+property=["\']{re.escape(key)}["\'][^>]+content=["\'](.*?)["\']',
        rf'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']{re.escape(key)}["\']',
        rf'<meta[^>]+name=["\']{re.escape(key)}["\'][^>]+content=["\'](.*?)["\']',
        rf'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']{re.escape(key)}["\']',
    ):
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if m:
            return unescape(m.group(1).strip())
    return None


def _find_first_string(obj: Any, candidate_keys: set[str]) -> str | None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in candidate_keys and isinstance(v, str) and v.strip():
                return v.strip()
        for v in obj.values():
            found = _find_first_string(v, candidate_keys)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_first_string(item, candidate_keys)
            if found:
                return found
    return None


def _extract_from_visible_labels(html: str) -> dict[str, str]:
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = unescape(text)
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]

    out: dict[str, str] = {}

    labels = {
        "issuing_agency": ["Cơ quan ban hành", "Cơ quan ban hành:", "Bộ, ngành ban hành"],
        "implementing_agency": ["Cơ quan thực hiện", "Cơ quan thực hiện:"],
        "sector": ["Lĩnh vực", "Lĩnh vực:"],
        "title": ["Tên thủ tục", "Tên thủ tục:", "Thủ tục hành chính"],
    }

    for key, words in labels.items():
        for i, line in enumerate(lines):
            if any(w.lower() == line.lower() for w in words):
                if i + 1 < len(lines):
                    out[key] = lines[i + 1]
                    break
            for w in words:
                if line.lower().startswith(w.lower()):
                    rhs = line[len(w) :].strip(" :")
                    if rhs:
                        out[key] = rhs
                        break
            if key in out:
                break

    return out


def extract_procedure(url: str) -> ProcedureData:
    parsed = urlparse(url)
    procedure_id = parsed.path.rstrip("/").split("/")[-1] if parsed.path else None

    data = ProcedureData(url=url, procedure_id=procedure_id)

    if procedure_id:
        try:
            api_url = "https://dichvucong.gov.vn/api/v1/configuring/formality/get-formality-by-citizen"
            api_resp = _http_post_json(api_url, {"id": procedure_id})
            api_data = json.loads(api_resp).get("data", {})
            if api_data:
                data.ma_so = api_data.get("code") or api_data.get("codeNotation")
                data.title = api_data.get("name")
                data.issuing_agency = api_data.get("departmentPromulgateName")
                data.sector = api_data.get("category", {}).get("name") if api_data.get("category") else None
                
                # Extract implementing agencies
                agencies = []
                unit_groups = api_data.get("unitGroupsExecuting")
                if isinstance(unit_groups, str) and unit_groups.strip():
                    agencies.append(unit_groups.strip())
                elif isinstance(unit_groups, list):
                    for u in unit_groups:
                        if isinstance(u, dict) and u.get("name"):
                            agencies.append(u.get("name").strip())
                        elif isinstance(u, str) and u.strip():
                            agencies.append(u.strip())
                            
                depts = api_data.get("departmentsExecuting")
                if isinstance(depts, str) and depts.strip():
                    agencies.append(depts.strip())
                elif isinstance(depts, list):
                    for d in depts:
                        if isinstance(d, dict) and d.get("name"):
                            agencies.append(d.get("name").strip())
                        elif isinstance(d, str) and d.strip():
                            agencies.append(d.strip())
                            
                exec_agencies = api_data.get("executingAgencies")
                if isinstance(exec_agencies, str) and exec_agencies.strip():
                    agencies.append(exec_agencies.strip())
                elif isinstance(exec_agencies, list):
                    for a in exec_agencies:
                        if isinstance(a, dict) and a.get("name"):
                            agencies.append(a.get("name").strip())
                        elif isinstance(a, str) and a.strip():
                            agencies.append(a.strip())
                            
                seen = set()
                unique_agencies = []
                for agency in agencies:
                    if agency not in seen:
                        seen.add(agency)
                        unique_agencies.append(agency)
                data.implementing_agency = "; ".join(unique_agencies) if unique_agencies else None
                
                data.summary = api_data.get("description") or (api_data.get("executionSteps", [{}])[0].get("description") if api_data.get("executionSteps") else None)
                data.raw_source = "api-v1"
                return data
        except Exception:
            # Fallback to HTML parsing if API fails
            pass

    html = _http_get(url)
    json_ld_objects = _extract_json_ld(html)
    next_data = _extract_next_data(html)

    if json_ld_objects:
        data.raw_source = "json-ld"
        primary = json_ld_objects[0]
        data.title = data.title or primary.get("name") if isinstance(primary.get("name"), str) else data.title
        data.summary = data.summary or primary.get("description") if isinstance(primary.get("description"), str) else data.summary

    if next_data:
        data.raw_source = data.raw_source or "next-data"
        data.title = data.title or _find_first_string(next_data, {"title", "name", "ten", "tenthutuc"})
        data.summary = data.summary or _find_first_string(next_data, {"description", "summary", "mota", "moTa", "noiDung"})
        data.issuing_agency = data.issuing_agency or _find_first_string(
            next_data,
            {"coquanbanhanh", "coQuanBanHanh", "issuingagency", "issuing_agency"},
        )
        data.implementing_agency = data.implementing_agency or _find_first_string(
            next_data,
            {"coquanthuchien", "coQuanThucHien", "implementingagency", "implementing_agency"},
        )
        data.sector = data.sector or _find_first_string(next_data, {"linhvuc", "linhVuc", "sector"})

    data.title = data.title or _extract_meta(html, "og:title")
    data.summary = data.summary or _extract_meta(html, "description")

    by_label = _extract_from_visible_labels(html)
    data.title = data.title or by_label.get("title")
    data.issuing_agency = data.issuing_agency or by_label.get("issuing_agency")
    data.implementing_agency = data.implementing_agency or by_label.get("implementing_agency")
    data.sector = data.sector or by_label.get("sector")

    return data


def write_csv(row: ProcedureData, output_file: Path) -> None:
    fieldnames = list(asdict(row).keys())
    mode = "a"

    if output_file.exists():
        try:
            with output_file.open("r", encoding="utf-8-sig", newline="") as rf:
                first_line = rf.readline().strip()
                existing_header = [h.strip() for h in first_line.split(",")] if first_line else []
            if existing_header != fieldnames:
                mode = "w"
        except Exception:
            mode = "w"
    else:
        mode = "w"

    with output_file.open(mode, encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if mode == "w":
            writer.writeheader()
        writer.writerow(asdict(row))


def enrich_from_local_csv(row: ProcedureData, lookup_csv: Path) -> ProcedureData:
    if not lookup_csv.exists():
        return row

    try:
        with lookup_csv.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for rec in reader:
                if (rec.get("URL") or "").strip() == row.url.strip():
                    row.ma_so = row.ma_so or (rec.get("Mã số") or None)
                    row.title = row.title if row.title and row.title != "Cổng Dịch vụ công Quốc gia" else (rec.get("Tên") or row.title)
                    row.issuing_agency = row.issuing_agency or (rec.get("Cơ quan ban hành") or None)
                    row.implementing_agency = row.implementing_agency or (rec.get("Cơ quan thực hiện") or None)
                    row.sector = row.sector or (rec.get("Lĩnh vực") or None)
                    row.raw_source = f"{row.raw_source}+csv-lookup" if row.raw_source else "csv-lookup"
                    break
    except Exception:
        # Keep extraction robust even when local CSV has encoding/format issues.
        return row

    return row


def main() -> int:
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')

    parser = argparse.ArgumentParser(description="Extract procedure data from dichvucong.gov.vn")
    parser.add_argument("url", help="Procedure URL")
    parser.add_argument(
        "--out",
        default="extracted_procedures.csv",
        help="Output CSV path (default: extracted_procedures.csv)",
    )
    parser.add_argument(
        "--lookup-csv",
        default="Ho_tich_merged_dedup_by_ma_so.csv",
        help="Optional local CSV used to enrich by exact URL match",
    )
    args = parser.parse_args()

    try:
        row = extract_procedure(args.url)
    except HTTPError as e:
        print(f"HTTP error: {e.code} - {e.reason}")
        return 2
    except URLError as e:
        print(f"URL error: {e.reason}")
        return 3
    except Exception as e:  # pylint: disable=broad-except
        print(f"Unexpected error: {e}")
        return 4

    row = enrich_from_local_csv(row, Path(args.lookup_csv))
    write_csv(row, Path(args.out))

    print("Extraction result")
    for k, v in asdict(row).items():
        print(f"- {k}: {v}")
    print(f"Saved to: {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
