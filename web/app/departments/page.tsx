import Link from "next/link";
import { HBar, MetricCard, MetricGrid } from "@/components/Charts";
import { fmtUSD, fmtUSDCompact, readRecipients } from "@/lib/recipients";

export const metadata = {
  title: "City departments — Denver Homelessness Dollar Tracker",
};

export default function DepartmentsPage() {
  const data = readRecipients();
  const by = data?.by_department ?? [];
  const sorted = [...by].sort((a, b) => b.total - a.total);
  const total = sorted.reduce((acc, d) => acc + d.total, 0);

  return (
    <article className="prose-civic">
      <h1>City departments</h1>
      <p>
        Denver department of origin for every payment in our database. The
        Department of Housing Stability (HOST) is the headline agency, but
        Denver Public Health &amp; Environment, Human Rights &amp; Community
        Partnerships, and others contribute meaningful slices. This view is the
        first cut at the <em>agency &rarr; recipient</em> middle leg of the
        funding flow.
      </p>

      <MetricGrid>
        <MetricCard
          label="Departments"
          value={`${sorted.length}`}
        />
        <MetricCard
          label="Total attributed"
          value={fmtUSDCompact(total)}
          hint={fmtUSD(total)}
        />
        <MetricCard
          label="Top department"
          value={sorted[0]?.name?.slice(0, 32) ?? "—"}
          hint={sorted[0] ? fmtUSDCompact(sorted[0].total) : undefined}
        />
      </MetricGrid>

      {sorted.length > 0 && (
        <>
          <h2>Spending by department</h2>
          <HBar
            items={sorted.map((d) => ({ label: d.name, value: d.total }))}
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
                <th>Department</th>
                <th>Total paid</th>
                <th>Payments</th>
                <th>Distinct recipients</th>
                <th>Top recipients</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((d) => (
                <tr key={d.slug}>
                  <td>{d.name}</td>
                  <td style={{ whiteSpace: "nowrap" }}>{fmtUSD(d.total)}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    {d.n_payments.toLocaleString()}
                  </td>
                  <td style={{ whiteSpace: "nowrap" }}>{d.n_recipients}</td>
                  <td>
                    {d.top_recipients.length === 0
                      ? "—"
                      : d.top_recipients
                          .map(
                            (r) =>
                              `${r.name} (${fmtUSDCompact(r.amount)})`,
                          )
                          .join("; ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <p style={{ color: "#78716c", fontSize: "0.85rem" }}>
        Source: the <code>Department</code> column of the Denver Open Checkbook.
        We do not currently merge variant spellings of the same department
        (e.g. <em>HOST</em> vs. <em>Department of Housing Stability (HOST)</em>
        vs. <em>Department of Housing Stability Special</em>) &mdash; that
        normalization is a backlog item.{" "}
        <Link href="/sources/">Source inventory</Link>.
      </p>
    </article>
  );
}
