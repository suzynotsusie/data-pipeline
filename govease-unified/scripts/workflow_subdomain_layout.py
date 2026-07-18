from __future__ import annotations

import copy
import csv
import json
from pathlib import Path
from typing import Any


def materialize_subdomain_outputs(
    workflow_dir: Path,
    summary_path: Path,
    normalized_path: Path,
    config_path: Path,
) -> list[Path]:
    if not summary_path.exists() or not normalized_path.exists() or not config_path.exists():
        return []

    with summary_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    normalized_payload = json.loads(normalized_path.read_text(encoding="utf-8"))
    config_payload = json.loads(config_path.read_text(encoding="utf-8"))

    rows_by_subdomain: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        subdomain_key = str(row.get("subdomain_key") or "").strip()
        if not subdomain_key:
            continue
        rows_by_subdomain.setdefault(subdomain_key, []).append(row)

    normalized_subdomains = {
        str(item.get("subdomain_key")): item
        for item in normalized_payload.get("subdomains", [])
        if isinstance(item, dict) and item.get("subdomain_key")
    }
    catalog_by_subdomain = {
        str(item.get("subdomain_key")): item
        for item in config_payload.get("subdomain_catalog", [])
        if isinstance(item, dict) and item.get("subdomain_key")
    }

    generated_paths: list[Path] = []
    for subdomain_key, subdomain_rows in rows_by_subdomain.items():
        subdomain_dir = workflow_dir / subdomain_key
        subdomain_dir.mkdir(parents=True, exist_ok=True)

        subdomain_summary_path = subdomain_dir / "summary.csv"
        with subdomain_summary_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(subdomain_rows)
        generated_paths.append(subdomain_summary_path)

        normalized_item = copy.deepcopy(normalized_subdomains.get(subdomain_key, {}))
        subdomain_normalized = {
            **normalized_payload,
            "subdomain_key": subdomain_key,
            "subdomain_label": normalized_item.get("subdomain_label"),
            "subdomains": [normalized_item] if normalized_item else [],
        }
        subdomain_normalized_path = subdomain_dir / "normalized.json"
        subdomain_normalized_path.write_text(
            json.dumps(subdomain_normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        generated_paths.append(subdomain_normalized_path)

        procedure_codes = {
            str(row.get("procedure_code") or "").strip()
            for row in subdomain_rows
            if str(row.get("procedure_code") or "").strip()
        }
        subdomain_config = _build_subdomain_config(
            config_payload=config_payload,
            subdomain_key=subdomain_key,
            subdomain_catalog_item=copy.deepcopy(catalog_by_subdomain.get(subdomain_key)),
            procedure_codes=procedure_codes,
        )
        subdomain_config_path = subdomain_dir / "workflow_engine_config.json"
        subdomain_config_path.write_text(
            json.dumps(subdomain_config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        generated_paths.append(subdomain_config_path)

    return generated_paths


def _build_subdomain_config(
    *,
    config_payload: dict[str, Any],
    subdomain_key: str,
    subdomain_catalog_item: dict[str, Any] | None,
    procedure_codes: set[str],
) -> dict[str, Any]:
    payload = copy.deepcopy(config_payload)
    payload["subdomain_key"] = subdomain_key
    payload["subdomain_catalog"] = [subdomain_catalog_item] if subdomain_catalog_item else []

    coverage = payload.get("coverage")
    if isinstance(coverage, dict):
        for key in ("expected_codes", "covered_codes", "missing_codes"):
            values = coverage.get(key)
            if isinstance(values, list):
                coverage[key] = [value for value in values if value in procedure_codes]

    decision_tree = payload.get("decision_tree")
    if isinstance(decision_tree, dict):
        routes = decision_tree.get("routes")
        if isinstance(routes, list):
            decision_tree["routes"] = [
                route
                for route in routes
                if _route_matches_subdomain(route, subdomain_key)
                and str(route.get("procedure_code") or "").strip() in procedure_codes
            ]

        nodes = decision_tree.get("nodes")
        if isinstance(nodes, list):
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                if node.get("slot") == "subdomain_key":
                    node["options"] = [subdomain_key]
                    node["prefilled_value"] = subdomain_key
                if "options_by_subdomain" in node and isinstance(node["options_by_subdomain"], dict):
                    selected = node["options_by_subdomain"].get(subdomain_key, [])
                    node["options_by_subdomain"] = {subdomain_key: selected}
                    node["options"] = [
                        item.get("operation_key", "")
                        for item in selected
                        if isinstance(item, dict) and item.get("operation_key")
                    ]

    return payload


def _route_matches_subdomain(route: Any, subdomain_key: str) -> bool:
    if not isinstance(route, dict):
        return False
    conditions = route.get("conditions")
    if not isinstance(conditions, dict):
        return True
    route_subdomain = conditions.get("subdomain_key")
    return route_subdomain in (None, "", subdomain_key)
