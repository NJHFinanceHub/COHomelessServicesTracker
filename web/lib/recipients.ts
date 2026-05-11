import fs from "node:fs";
import path from "node:path";

const REPO_ROOT = path.join(process.cwd(), "..");

export type AmountPair = { name: string; amount: number };

export type YearRow = {
  year: string;
  amount: number;
  n_payments: number;
};

export type PaymentSample = {
  date: string | null;
  amount: number;
  department: string | null;
  funding_source: string | null;
  expense_category: string | null;
  description: string | null;
};

export type RecipientRow = {
  id: number;
  legal_name: string;
  slug: string;
  n_payments: number;
  total_paid: number;
  first_payment_date: string | null;
  last_payment_date: string | null;
  years_active?: string[];
  by_year: YearRow[] | Record<string, number>; // tolerates both shapes during rollover
  by_department?: AmountPair[];
  by_funding_source?: AmountPair[];
  by_expense_category?: AmountPair[];
  recent_payments?: PaymentSample[];
  // Legacy fields kept for backwards-compat with the previous JSON shape:
  top_departments?: AmountPair[];
  top_funding_sources?: AmountPair[];
};

export type SeedStatus = {
  canonical: string;
  distinctive: string;
  notes: string;
  matched: boolean;
  n_payments: number;
  total_paid: number;
};

export type YearAgg = {
  year: string;
  n_payments: number;
  total: number;
  n_recipients: number;
};

export type MonthAgg = {
  year_month: string; // "YYYY-MM"
  n_payments: number;
  total: number;
  n_recipients: number;
};

export type DepartmentAgg = {
  name: string;
  slug: string;
  n_payments: number;
  total: number;
  n_recipients: number;
  top_recipients: AmountPair[];
};

export type FundingAgg = {
  name: string;
  slug: string;
  n_payments: number;
  total: number;
  n_recipients: number;
};

export type Overview = {
  total_paid: number;
  n_payments: number;
  n_recipients_matched: number;
  n_seeds_total: number | null;
  n_seeds_matched: number | null;
  n_departments: number;
  n_funding_sources: number;
  first_payment_date: string | null;
  last_payment_date: string | null;
  n_years: number;
  years_active: string[];
  top_recipient: { name: string; amount: number } | null;
  top_department: { name: string; amount: number } | null;
  top_funding_source: { name: string; amount: number } | null;
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
  overview?: Overview;
  by_year?: YearAgg[];
  by_month?: MonthAgg[];
  by_department?: DepartmentAgg[];
  by_funding?: FundingAgg[];
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

const USD_LARGE = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 1,
});

export function fmtUSD(n: number): string {
  return USD.format(n);
}

export function fmtUSDCompact(n: number): string {
  return USD_LARGE.format(n);
}

export function fmtIso(iso: string | null | undefined): string {
  if (!iso) return "—";
  return iso.replace("T", " ").replace(/\..+/, " UTC");
}

// Normalize the by_year field on a RecipientRow into a sorted array.
export function normalizedByYear(r: RecipientRow): YearRow[] {
  if (Array.isArray(r.by_year)) return r.by_year;
  if (r.by_year && typeof r.by_year === "object") {
    return Object.entries(r.by_year)
      .map(([year, amount]) => ({
        year,
        amount: Number(amount) || 0,
        n_payments: 0,
      }))
      .sort((a, b) => a.year.localeCompare(b.year));
  }
  return [];
}

export function recipientBySlug(
  data: RecipientsPayload,
  slug: string,
): RecipientRow | undefined {
  return data.recipients.find(
    (r) => r.slug === slug || slugify(r.legal_name) === slug,
  );
}

export function slugify(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "unknown";
}
