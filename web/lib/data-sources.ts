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
