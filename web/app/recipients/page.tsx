import Link from "next/link";
import { fmtUSD, readRecipients } from "@/lib/recipients";

export const metadata = {
  title: "Recipients — Denver Homelessness Dollar Tracker",
};

function fmtIso(iso: string | null): string {
  if (!iso) return "—";
  return iso.replace("T", " ").replace(/\..+/, " UTC");
}

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

  const { meta, recipients, seeds } = data;
  const sorted = [...recipients].sort((a, b) => b.total_paid - a.total_paid);
  const sumTotal = sorted.reduce((acc, r) => acc + r.total_paid, 0);
  const unmatchedSeeds = (seeds ?? []).filter((s) => !s.matched);

  return (
    <article className="prose-civic">
      <h1>Recipients</h1>
      <p>
        Every nonprofit on the curated seed list, with their total receipts
        from the City and County of Denver (Open Checkbook). Numbers reflect
        only payments that we&rsquo;ve been able to deterministically attribute
        to the named organization &mdash; see{" "}
        <Link href="/methodology">methodology</Link> for the matching rules.
      </p>

      <table>
        <tbody>
          <tr>
            <th>Recipients with at least one payment</th>
            <td>
              {sorted.filter((r) => r.n_payments > 0).length} of{" "}
              {sorted.length}
            </td>
          </tr>
          <tr>
            <th>Total payments ingested</th>
            <td>{meta.n_payments.toLocaleString()}</td>
          </tr>
          <tr>
            <th>Total dollars attributed</th>
            <td>{fmtUSD(sumTotal)}</td>
          </tr>
          <tr>
            <th>Last checkbook fetch</th>
            <td>{fmtIso(meta.last_checkbook_fetch_at)}</td>
          </tr>
          <tr>
            <th>JSON generated at</th>
            <td>{fmtIso(meta.generated_at)}</td>
          </tr>
        </tbody>
      </table>

      {meta.n_payments === 0 && (
        <p>
          <strong>No payment rows yet.</strong> The data model and ingest are
          wired; the next nightly run (or manual <code>workflow_dispatch</code>)
          will populate these tables. Page will update on the following deploy.
        </p>
      )}

      {sorted.some((r) => r.n_payments > 0) && (
        <>
          <h2>By total received</h2>
          <table>
            <thead>
              <tr>
                <th>Recipient</th>
                <th>Payments</th>
                <th>Total</th>
                <th>First</th>
                <th>Last</th>
                <th>Top department</th>
                <th>Top funding source</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((r) => (
                <tr key={r.id}>
                  <td>{r.legal_name}</td>
                  <td>{r.n_payments.toLocaleString()}</td>
                  <td>{fmtUSD(r.total_paid)}</td>
                  <td>{r.first_payment_date ?? "—"}</td>
                  <td>{r.last_payment_date ?? "—"}</td>
                  <td>
                    {r.top_departments[0]?.name ?? "—"}
                    {r.top_departments[0] && (
                      <span style={{ color: "#78716c" }}>
                        {" "}
                        ({fmtUSD(r.top_departments[0].amount)})
                      </span>
                    )}
                  </td>
                  <td>
                    {r.top_funding_sources[0]?.name ?? "—"}
                    {r.top_funding_sources[0] && (
                      <span style={{ color: "#78716c" }}>
                        {" "}
                        ({fmtUSD(r.top_funding_sources[0].amount)})
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {unmatchedSeeds.length > 0 && (
        <>
          <h2>Curated seeds with no matched payments</h2>
          <p>
            These nonprofits are on our curated seed list but the most recent
            ingest found zero matching Denver Checkbook payments. Common
            reasons: the org is a sub-grantee paid through a larger nonprofit,
            it&rsquo;s a regional/quasi-public entity not contracted directly
            by the city, or our matching phrase needs widening. Listed for
            curator transparency.
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

      <p style={{ color: "#78716c", fontSize: "0.9rem" }}>
        Source: City and County of Denver Open Checkbook (Socrata dataset
        wnau-xrqi). Every payment row in our database links back to its
        Socrata <code>:id</code>. Aggregations exclude $0 voids and
        adjustments.
      </p>
    </article>
  );
}
