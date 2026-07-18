import { readFile, readdir } from "node:fs/promises";
import path from "node:path";

import type { CitizenGroupOption, CitizenSubdomainOption, CitizenWorkflowCatalog } from "./types";

type RawCatalog = {
  groups?: Array<{
    group_key: string;
    group_id: number;
    label: string;
    subdomains?: Array<{
      event_id: number;
      subdomain_key: string;
      label: string;
      subdomain_label?: string;
    }>;
  }>;
};

type WorkflowConfig = {
  subdomain_catalog?: Array<{
    subdomain_key: string;
    subdomain_label?: string;
    summary?: string;
  }>;
  entry_prompts?: string[];
};

const WORKSPACE_ROOT = path.resolve(process.cwd(), "..");
const CATALOG_PATH = path.join(WORKSPACE_ROOT, "data", "catalog", "citizen_group_domains.json");
const WORKFLOWS_ROOT = path.join(WORKSPACE_ROOT, "..", "data", "workflows");

function titleCaseVietnameseKey(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function buildGroupDescription(group: CitizenGroupOption): string {
  const subdomainLabels = group.subdomains.slice(0, 3).map((item) => item.label);
  if (!subdomainLabels.length) {
    return `Nhóm ${group.label.toLowerCase()} trong luồng thủ tục công dân.`;
  }
  const moreCount = group.subdomains.length - subdomainLabels.length;
  const suffix = moreCount > 0 ? ` và ${moreCount} nhánh khác` : "";
  return `${subdomainLabels.join(", ")}${suffix}.`;
}

async function loadWorkflowConfig(groupKey: string): Promise<WorkflowConfig | null> {
  const workflowPath = path.join(WORKFLOWS_ROOT, groupKey, "workflow_engine_config.json");
  try {
    const raw = await readFile(workflowPath, "utf-8");
    return JSON.parse(raw) as WorkflowConfig;
  } catch {
    return null;
  }
}

async function loadSubdomainWorkflowConfigs(groupKey: string): Promise<Map<string, WorkflowConfig>> {
  const groupDir = path.join(WORKFLOWS_ROOT, groupKey);
  try {
    const entries = await readdir(groupDir, { withFileTypes: true });
    const configs = new Map<string, WorkflowConfig>();
    await Promise.all(
      entries
        .filter((entry) => entry.isDirectory())
        .map(async (entry) => {
          const workflowPath = path.join(groupDir, entry.name, "workflow_engine_config.json");
          try {
            const raw = await readFile(workflowPath, "utf-8");
            configs.set(entry.name, JSON.parse(raw) as WorkflowConfig);
          } catch {
            // Ignore partial folders while the workflow dataset is being materialized.
          }
        }),
    );
    return configs;
  } catch {
    return new Map();
  }
}

export async function getCitizenWorkflowCatalog(): Promise<CitizenWorkflowCatalog> {
  const raw = await readFile(CATALOG_PATH, "utf-8");
  const catalog = JSON.parse(raw) as RawCatalog;

  const groups = await Promise.all(
    (catalog.groups || []).map(async (group): Promise<CitizenGroupOption> => {
      const workflow = await loadWorkflowConfig(group.group_key);
      const subdomainWorkflows = await loadSubdomainWorkflowConfigs(group.group_key);
      const labelMap = new Map(
        (workflow?.subdomain_catalog || [])
          .filter((item) => item.subdomain_key)
          .map((item) => [item.subdomain_key, item.subdomain_label || item.subdomain_key]),
      );
      const summaryMap = new Map(
        (workflow?.subdomain_catalog || []).map((item) => [item.subdomain_key, item.summary || null]),
      );

      const subdomains: CitizenSubdomainOption[] = (group.subdomains || []).map((subdomain) => ({
        event_id: subdomain.event_id,
        subdomain_key: subdomain.subdomain_key,
        label:
          labelMap.get(subdomain.subdomain_key) ||
          subdomain.subdomain_label ||
          subdomain.label ||
          titleCaseVietnameseKey(subdomain.subdomain_key),
        summary:
          summaryMap.get(subdomain.subdomain_key) ||
          subdomainWorkflows.get(subdomain.subdomain_key)?.subdomain_catalog?.[0]?.summary ||
          null,
      }));

      const nextGroup: CitizenGroupOption = {
        group_key: group.group_key,
        group_id: group.group_id,
        label: group.label,
        description: "",
        entry_prompts: workflow?.entry_prompts || [],
        subdomains,
      };

      nextGroup.description = buildGroupDescription(nextGroup);
      return nextGroup;
    }),
  );

  return {
    persona: "citizen",
    updated_at: new Date().toISOString().slice(0, 10),
    groups,
  };
}
