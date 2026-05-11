import Link from "next/link";
import { HBar, MetricCard, MetricGrid } from "@/components/Charts";
import { fmtIso, fmtUSD, fmtUSDCompact, readRecipients, slugify } from "@/lib/recipients";

export const metadata = {
  title: "Recipients — Denver Homelessness Dollar Tracker",
};

export default function RecipientsPage() {
  const data = readRecipients();
  if (!data) {
    return (
      <article className="prose-civic">
        <h1>Recipients</h1>
        <p>
          No <code>data/processed/recipients.json</code> on disk yet. The
          nightly GitHub Actions workflow writes this file after the
          Phase&nbsp;1 ingest runs against the Denver Open Checkbook.
        </p>
      </article>
    );
  }

  const sorted = [...data.recipients].sort((a, b) => b.total_paid - a.total_paid);
  const matched = sorted.filter((r) => r.n_payments > 0);
  const sumTotal = sorted.reduce((acc, r) => acc + r.total_paid, 0);
  const unmatchedSeeds = (data.seeds ?? []).filter((s) => !s.matched);

  return (
    <article className="prose-civic">
      <h1>Recipients</h1>
      <p>
        Every nonprofit on the curated seed list, with total receipts from
        the City and County of Denver. Click any name for the full payment
        history, year-by-year breakdown, and the city departments funding
        them.
      </p>

      <MetricGrid>
        <MetricCard
          label="Recipients"
          value={`${matched.length}`}
          hint={
            data.overview?.n_seeds_total
              ? `of ${data.overview.n_seeds_total} curated seeds`
              : undefined
          }
        />
        <MetricCard
          label="Total attributed"
          value={fmtUSDCompact(sumTotal)}
          hint={fmtUSD(sumTotal)}
        />
        <MetricCard
          label="Payments ingested"
          value={data.meta.n_payments.toLocaleString()}
        />
        <MetricCard
          label="Last checkbook fetch"
          value={fmtIso(data.meta.last_checkbook_fetch_at)}
        />
      </MetricGrid>

      {matched.length > 0 && (
        <>
          <h2>All recipients, ranked</h2>
          <HBar
            items={matched.map((r) => ({
              label: r.legal_name,
              value: r.total_paid,
              href: `/recipients/${r.slug || slugify(r.legal_name)}/`,
            }))}
            formatter={fmtUSDCompact}
          />
        </>
      )}

      {matched.length > 0 && (
        <>
          <h2>Detail table</h2>
          <table>
            <thead>
              <tr>
                <th>Recipient</th>
                <th>Payments</th>
                <th>Total</th>
                <th>First</th>
                <th>Last</th>
                <th>Top department</th>
              </tr>
            </thead>
            <tbody>
              {matched.map((r) => {
                const topDept =
                  (r.by_department ?? r.top_departments ?? [])[0];
                return (
                  <tr key={r.id}>
                    <td>
                      <Link href={`/recipients/${r.slug || slugify(r.legal_name)}/`}>{r.legal_name}</Link>
                    </td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      {r.n_payments.toLocaleString()}
                    </td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      {fmtUSD(r.total_paid)}
                    </td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      {r.first_payment_date ?? "—"}
                    </td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      {r.last_payment_date ?? "—"}
                    </td>
                    <td>
                      {topDept ? (
                        <>
                          {topDept.name}{" "}
                          <span style={{ color: "#78716c" }}>
                            ({fmtUSDCompact(topDept.amount)})
                          </span>
                        </>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}

      {unmatchedSeeds.length > 0 && (
        <>
          <h2>Seeds with no matched payments ({unmatchedSeeds.length})</h2>
          <p>
            These nonprofits are on our curated seed list but the most recent
            ingest found zero matching Denver Checkbook payments. Common
            reasons: the org is paid through a fiscal sponsor or larger
            nonprofit; it&rsquo;s regional/quasi-public; or our matching phrase
            needs widening. Surfaced for curator transparency.
          </p>
          <table>
            <thead>
              <tr>
                <th>Canonical name</th>
                <th>Curator note</th>
              </tr>
            </thead>
            <tbody>
              {unmatchedSeeds.map((s) => (
                <tr key={s.canonical}>
                  <td>{s.canonical}</td>
                  <td style={{ color: "#57534e" }}>{s.notes || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <p style={{ color: "#78716c", fontSize: "0.85rem" }}>
        Source: City and County of Denver Open Checkbook (Socrata dataset
        wnau-xrqi). Every payment row in our database links back to its
        Socrata <code>:id</code>. Aggregations exclude $0 voids and
        adjustments.
      </p>
    </article>
  );
}
