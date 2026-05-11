import fs from "node:fs";
import path from "node:path";

const REPO_ROOT = path.join(process.cwd(), "..");

export type RecipientRow = {
  id: number;
  legal_name: string;
  n_payments: number;
  total_paid: number;
  first_payment_date: string | null;
  last_payment_date: string | null;
  by_year: Record<string, number>;
  top_departments: { name: string; amount: number }[];
  top_funding_sources: { name: string; amount: number }[];
};

export type SeedStatus = {
  canonical: string;
  distinctive: string;
  notes: string;
  matched: boolean;
  n_payments: number;
  total_paid: number;
};

export type RecipientsPayload = {
  meta: {
    generated_at: string;
    last_checkbook_fetch_at: string | null;
    n_recipients: number;
    n_payments: number;
    n_seeds?: number;
    n_seeds_matched?: number;
  };
  recipients: RecipientRow[];
  seeds?: SeedStatus[];
};

export function readRecipients(): RecipientsPayload | null {
  const p = path.join(REPO_ROOT, "data", "processed", "recipients.json");
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, "utf8")) as RecipientsPayload;
}

const USD = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

export function fmtUSD(n: number): string {
  return USD.format(n);
}
