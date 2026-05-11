import Link from "next/link";
import { HBar, MetricCard, MetricGrid } from "@/components/Charts";
import { fmtUSD, fmtUSDCompact, readRecipients } from "@/lib/recipients";

export const metadata = {
  title: "Funding sources — Denver Homelessness Dollar Tracker",
};

export default function FundingPage() {
  const data = readRecipients();
  const by = data?.by_funding ?? [];
  const sorted = [...by].sort((a, b) => b.total - a.total);
  const total = sorted.reduce((acc, f) => acc + f.total, 0);

  return (
    <article className="prose-civic">
      <h1>Funding sources</h1>
      <p>
        Where the dollars originated, drawn from the{" "}
        <code>FundingSourceDescription</code> column of the city checkbook.
        Voter-approved measures (Homelessness Resolution Fund &mdash; Ballot
        2B, 2020; Affordable Housing Fund), federal grants (HUD CoC, ESG,
        CDBG, HOME, ARPA pass-throughs), state funds, and general-fund
        baselines all flow through this leg.
      </p>

      <MetricGrid>
        <MetricCard label="Distinct funding sources" value={`${sorted.length}`} />
        <MetricCard
          label="Total attributed"
          value={fmtUSDCompact(total)}
          hint={fmtUSD(total)}
        />
        <MetricCard
          label="Top source"
          value={sorted[0]?.name?.slice(0, 32) ?? "—"}
          hint={sorted[0] ? fmtUSDCompact(sorted[0].total) : undefined}
        />
      </MetricGrid>

      {sorted.length > 0 && (
        <>
          <h2>Spending by funding source</h2>
          <HBar
            items={sorted.map((f) => ({ label: f.name, value: f.total }))}
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
                <th>Funding source</th>
                <th>Total paid</th>
                <th>Payments</th>
                <th>Distinct recipients</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((f) => (
                <tr key={f.slug}>
                  <td>{f.name}</td>
                  <td style={{ whiteSpace: "nowrap" }}>{fmtUSD(f.total)}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    {f.n_payments.toLocaleString()}
                  </td>
                  <td style={{ whiteSpace: "nowrap" }}>{f.n_recipients}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <p style={{ color: "#78716c", fontSize: "0.85rem" }}>
        Source: the <code>FundingSourceDescription</code> column of the Denver
        Open Checkbook. Funding-source strings are stored verbatim; a curator
        pass to bucket them into the funding-source taxonomy from{" "}
        <Link href="/methodology/">methodology</Link> (federal / state /
        local-tax / bond / philanthropic / fee) is a backlog item.
      </p>
    </article>
  );
}
