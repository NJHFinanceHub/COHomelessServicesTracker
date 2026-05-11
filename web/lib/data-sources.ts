import fs from "node:fs";
import path from "node:path";

const REPO_ROOT = path.join(process.cwd(), "..");

export type CheckbookColumn = {
  fieldName: string;
  name: string;
  dataTypeName: string;
};

export type CheckbookColumnProbe = {
  endpoint: string;
  dataset_id: string;
  fetched_at: string;
  rows_updated_at: number | null;
  columns: CheckbookColumn[];
  resolved: {
    vendor_field: string | null;
    amount_field: string | null;
    date_field: string | null;
  };
};

export function readCheckbookColumnProbe(): CheckbookColumnProbe | null {
  const p = path.join(REPO_ROOT, "data", "raw", "checkbook_columns.json");
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, "utf8")) as CheckbookColumnProbe;
}

export type CheckbookDateRange = {
  endpoint: string;
  dataset_id: string;
  fetched_at: string;
  min_date: string | null;
  max_date: string | null;
  n_total_rows: number;
  sum_total: number | null;
  per_year: { year: string; n_payments: number; total: number | null }[];
};

export function readCheckbookDateRange(): CheckbookDateRange | null {
  const p = path.join(REPO_ROOT, "data", "raw", "checkbook_date_range.json");
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, "utf8")) as CheckbookDateRange;
}

export type CatalogHit = {
  id: string;
  name: string | null;
  description: string;
  domain: string | null;
  type: string | null;
  updatedAt: string | null;
  createdAt: string | null;
  columns_field_name?: string[];
  row_count?: number | null;
  permalink: string | null;
};

export type CatalogPayload = {
  fetched_at: string;
  queries: { q: string; extra: string }[];
  n_hits_total: number;
  n_hits_filtered: number;
  hits: CatalogHit[];
};

export function readCatalogHits(): CatalogPayload | null {
  const p = path.join(REPO_ROOT, "data", "raw", "socrata_catalog_denver_checkbook.json");
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, "utf8")) as CatalogPayload;
}
