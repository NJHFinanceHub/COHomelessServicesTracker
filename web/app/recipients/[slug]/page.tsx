import Link from "next/link";
import { notFound } from "next/navigation";
import { HBar, MetricCard, MetricGrid, VBar } from "@/components/Charts";
import {
  fmtIso,
  fmtUSD,
  fmtUSDCompact,
  normalizedByYear,
  readRecipients,
  slugify,
} from "@/lib/recipients";

export const dynamicParams = false; // static export — only known slugs

function slugFor(r: { slug?: string; legal_name: string }): string {
  return r.slug || slugify(r.legal_name);
}

export function generateStaticParams() {
  const data = readRecipients();
  if (!data) return [];
  return data.recipients
    .filter((r) => r.n_payments > 0)
    .map((r) => ({ slug: slugFor(r) }));
}

export default function RecipientDetail({ params }: { params: { slug: string } }) {
  const data = readRecipients();
  if (!data) return notFound();
  const r = data.recipients.find((x) => slugFor(x) === params.slug);
  if (!r || r.n_payments === 0) return notFound();

  const byYear = normalizedByYear(r);
  const byDept = r.by_department ?? r.top_departments ?? [];
  const byFund = r.by_funding_source ?? r.top_funding_sources ?? [];
  const byCat = r.by_expense_category ?? [];
  const recent = r.recent_payments ?? [];

  return (
    <article className="prose-civic">
      <p style={{ fontSize: "0.85rem", color: "#78716c", marginBottom: 0 }}>
        <Link href="/recipients/">← All recipients</Link>
      </p>
      <h1>{r.legal_name}</h1>

      <MetricGrid>
        <MetricCard
          label="Total received"
          value={fmtUSDCompact(r.total_paid)}
          hint={fmtUSD(r.total_paid)}
        />
        <MetricCard
          label="Payments"
          value={r.n_payments.toLocaleString()}
        />
        <MetricCard
          label="Date range"
          value={
            r.first_payment_date && r.last_payment_date
              ? `${r.first_payment_date.slice(0, 4)}–${r.last_payment_date.slice(0, 4)}`
              : "—"
          }
          hint={
            r.first_payment_date && r.last_payment_date
              ? `${r.first_payment_date} → ${r.last_payment_date}`
              : undefined
          }
        />
        <MetricCard label="City departments" value={`${byDept.length}`} />
        <MetricCard label="Funding sources" value={`${byFund.length}`} />
      </MetricGrid>

      {byYear.length > 0 && (
        <>
          <h2>By year</h2>
          <VBar
            items={byYear.map((y) => ({ label: y.year, value: y.amount }))}
            formatter={fmtUSDCompact}
          />
        </>
      )}

      {byDept.length > 0 && (
        <>
          <h2>By city department</h2>
          <HBar
            items={byDept.map((d) => ({ label: d.name, value: d.amount }))}
            formatter={fmtUSDCompact}
          />
        </>
      )}

      {byFund.length > 0 && (
        <>
          <h2>By funding source</h2>
          <HBar
            items={byFund.map((f) => ({ label: f.name, value: f.amount }))}
            formatter={fmtUSDCompact}
          />
        </>
      )}

      {byCat.length > 0 && (
        <>
          <h2>By expense category</h2>
          <HBar
            items={byCat.map((c) => ({ label: c.name, value: c.amount }))}
            formatter={fmtUSDCompact}
          />
        </>
      )}

      {recent.length > 0 && (
        <>
          <h2>Most recent payments</h2>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Amount</th>
                <th>Department</th>
                <th>Funding source</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((p, idx) => (
                <tr key={idx}>
                  <td style={{ whiteSpace: "nowrap" }}>{p.date ?? "—"}</td>
                  <td style={{ whiteSpace: "nowrap" }}>{fmtUSD(p.amount)}</td>
                  <td>{p.department ?? "—"}</td>
                  <td>{p.funding_source ?? "—"}</td>
                  <td>{p.description ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ color: "#78716c", fontSize: "0.85rem" }}>
            Showing the {recent.length} most recent payments. All payments are
            stored in our database keyed on the Socrata row id from the city
            checkbook.
          </p>
        </>
      )}

      <p style={{ color: "#78716c", fontSize: "0.85rem" }}>
        Source: City of Denver Open Checkbook (Socrata dataset wnau-xrqi). Last
        verified ingest: {fmtIso(data.meta.last_checkbook_fetch_at)}.
      </p>
    </article>
  );
}
