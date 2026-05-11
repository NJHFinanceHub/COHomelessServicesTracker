import Link from "next/link";
import { MetricCard, MetricGrid, VBar } from "@/components/Charts";
import { fmtUSD, fmtUSDCompact, readRecipients } from "@/lib/recipients";

export const metadata = {
  title: "Timeline — Denver Homelessness Dollar Tracker",
};

const MONTH_NAMES = [
  "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function shortMonth(ym: string): string {
  // "2025-04" → "Apr"
  const [, m] = ym.split("-");
  const idx = parseInt(m, 10);
  if (!idx || idx < 1 || idx > 12) return ym;
  return MONTH_NAMES[idx];
}

export default function TimelinePage() {
  const data = readRecipients();
  const byYear = data?.by_year ?? [];
  const byMonth = data?.by_month ?? [];

  const monthTotal = byMonth.reduce((acc, m) => acc + m.total, 0);
  const peakMonth = byMonth.reduce<{ year_month: string; total: number } | null>(
    (acc, m) => (acc === null || m.total > acc.total ? m : acc),
    null,
  );
  const lastMonth = byMonth[byMonth.length - 1];

  const yearTotal = byYear.reduce((acc, y) => acc + y.total, 0);
  const peakYear = byYear.reduce<{ year: string; total: number } | null>(
    (acc, y) => (acc === null || y.total > acc.total ? y : acc),
    null,
  );

  return (
    <article className="prose-civic">
      <h1>Timeline</h1>

      {byYear.length === 1 && (
        <p
          style={{
            borderLeft: "3px solid #b45309",
            paddingLeft: 12,
            color: "#57534e",
            background: "#fef3c7",
            padding: "0.75rem 1rem",
            borderRadius: 4,
          }}
        >
          <strong>Single-year coverage confirmed.</strong> The Denver Open
          Checkbook dataset (Socrata <code>wnau-xrqi</code>) is
          current-calendar-year only. We probed every realistic alternative
          source (sibling Socrata datasets, the Internet Archive Wayback
          Machine, the Denver Open Data Portal) and none returns transactional
          data for 2020–2024. See <Link href="/data/">data status</Link> for
          the full evidence trail. Monthly granularity below is what we&rsquo;ve
          got &mdash; it still surfaces real seasonal patterns and one-time
          payout months.
        </p>
      )}

      {byMonth.length > 0 && (
        <>
          <h2>Monthly spend, {byMonth[0].year_month.slice(0, 4)}</h2>
          <MetricGrid>
            <MetricCard
              label="Months covered"
              value={`${byMonth.length}`}
              hint={
                byMonth.length > 0
                  ? `${byMonth[0].year_month} → ${byMonth[byMonth.length - 1].year_month}`
                  : undefined
              }
            />
            <MetricCard
              label="Total"
              value={fmtUSDCompact(monthTotal)}
              hint={fmtUSD(monthTotal)}
            />
            <MetricCard
              label="Peak month"
              value={peakMonth ? peakMonth.year_month : "—"}
              hint={peakMonth ? fmtUSDCompact(peakMonth.total) : undefined}
            />
            <MetricCard
              label="Most recent month"
              value={lastMonth ? lastMonth.year_month : "—"}
              hint={lastMonth ? fmtUSDCompact(lastMonth.total) : undefined}
            />
          </MetricGrid>
          <VBar
            items={byMonth.map((m) => ({
              label: shortMonth(m.year_month),
              value: m.total,
            }))}
            formatter={fmtUSDCompact}
          />
          <h3>Detail</h3>
          <table>
            <thead>
              <tr>
                <th>Month</th>
                <th>Total</th>
                <th>Payments</th>
                <th>Distinct recipients</th>
              </tr>
            </thead>
            <tbody>
              {byMonth.map((m) => (
                <tr key={m.year_month}>
                  <td>{m.year_month}</td>
                  <td style={{ whiteSpace: "nowrap" }}>{fmtUSD(m.total)}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    {m.n_payments.toLocaleString()}
                  </td>
                  <td style={{ whiteSpace: "nowrap" }}>{m.n_recipients}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {byYear.length > 1 && (
        <>
          <h2>Annual spend</h2>
          <MetricGrid>
            <MetricCard
              label="Years covered"
              value={
                byYear.length > 0
                  ? `${byYear[0].year}–${byYear[byYear.length - 1].year}`
                  : "—"
              }
            />
            <MetricCard
              label="Total"
              value={fmtUSDCompact(yearTotal)}
              hint={fmtUSD(yearTotal)}
            />
            <MetricCard
              label="Peak year"
              value={peakYear ? peakYear.year : "—"}
              hint={peakYear ? fmtUSDCompact(peakYear.total) : undefined}
            />
          </MetricGrid>
          <VBar
            items={byYear.map((y) => ({ label: y.year, value: y.total }))}
            formatter={fmtUSDCompact}
          />
        </>
      )}

      <p style={{ color: "#78716c", fontSize: "0.85rem" }}>
        Source: Denver Open Checkbook (<code>wnau-xrqi</code>). Year and month
        are parsed from the first 4 and 7 characters of{" "}
        <code>PaymentDate</code> respectively. Fiscal-year vs. calendar-year
        nuance is not modelled.
      </p>
    </article>
  );
}
