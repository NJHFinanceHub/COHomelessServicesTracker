import { MetricCard, MetricGrid, VBar } from "@/components/Charts";
import { fmtUSD, fmtUSDCompact, readRecipients } from "@/lib/recipients";

export const metadata = {
  title: "Annual spend — Denver Homelessness Dollar Tracker",
};

export default function YearsPage() {
  const data = readRecipients();
  const by = data?.by_year ?? [];
  const sorted = [...by].sort((a, b) => a.year.localeCompare(b.year));
  const total = sorted.reduce((acc, y) => acc + y.total, 0);
  const peak = sorted.reduce<{ year: string; total: number } | null>(
    (acc, y) => (acc === null || y.total > acc.total ? y : acc),
    null,
  );
  const last = sorted[sorted.length - 1];

  return (
    <article className="prose-civic">
      <h1>Annual spend</h1>
      {sorted.length === 1 && (
        <p
          style={{
            borderLeft: "3px solid #b45309",
            paddingLeft: 12,
            color: "#57534e",
          }}
        >
          <strong>Single-year coverage.</strong> The Denver Open Checkbook
          dataset (Socrata id <code>wnau-xrqi</code>) is current-calendar-year
          only &mdash; it rolls over every January and retains the present
          year&rsquo;s payments. Hence one bar. We&rsquo;ve confirmed this by
          aggregate-querying the dataset; see{" "}
          <a href="/data/">data status</a> for the evidence and a list of
          candidate historical sources.
        </p>
      )}
      <p>
        Total dollars Denver paid to the seeded homelessness-related
        nonprofits each calendar year. When multi-year data is available the
        shape of this curve will be the most important contextual chart on
        the site &mdash; ARPA pass-throughs, voter-approved measures, and
        one-time bond proceeds all reshape it.
      </p>

      <MetricGrid>
        <MetricCard
          label="Years covered"
          value={
            sorted.length > 0
              ? `${sorted[0].year}–${sorted[sorted.length - 1].year}`
              : "—"
          }
        />
        <MetricCard
          label="Total"
          value={fmtUSDCompact(total)}
          hint={fmtUSD(total)}
        />
        <MetricCard
          label="Peak year"
          value={peak ? peak.year : "—"}
          hint={peak ? fmtUSDCompact(peak.total) : undefined}
        />
        <MetricCard
          label="Most recent year"
          value={last ? last.year : "—"}
          hint={last ? fmtUSDCompact(last.total) : undefined}
        />
      </MetricGrid>

      {sorted.length > 0 && (
        <>
          <h2>Spend per year</h2>
          <VBar
            items={sorted.map((y) => ({ label: y.year, value: y.total }))}
            formatter={fmtUSDCompact}
          />
        </>
      )}

      {sorted.length > 0 && (
        <>
          <h2>Detail</h2>
          <table>
            <thead>
              <tr>
                <th>Year</th>
                <th>Total paid</th>
                <th>Payments</th>
                <th>Distinct recipients</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((y) => (
                <tr key={y.year}>
                  <td>{y.year}</td>
                  <td style={{ whiteSpace: "nowrap" }}>{fmtUSD(y.total)}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    {y.n_payments.toLocaleString()}
                  </td>
                  <td style={{ whiteSpace: "nowrap" }}>{y.n_recipients}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <p style={{ color: "#78716c", fontSize: "0.85rem" }}>
        Year is parsed from the first 4 characters of <code>PaymentDate</code>
        in the Denver Open Checkbook. Fiscal-year vs. calendar-year nuance is
        not yet modelled.
      </p>
    </article>
  );
}
