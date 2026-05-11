import Link from "next/link";
import { readCheckbookColumnProbe } from "@/lib/data-sources";

export const metadata = {
  title: "Data status — Denver Homelessness Dollar Tracker",
};

function fmtEpoch(epoch: number | null): string {
  if (!epoch) return "—";
  return new Date(epoch * 1000).toISOString().replace("T", " ").replace(/\..+/, " UTC");
}

function fmtIso(iso: string): string {
  return iso.replace("T", " ").replace(/\..+/, " UTC");
}

export default function DataStatusPage() {
  const probe = readCheckbookColumnProbe();

  return (
    <article className="prose-civic">
      <h1>Data status</h1>
      <p>
        Each upstream source has a status of <em>not yet ingested</em>,{" "}
        <em>scaffolded</em>, <em>piloted</em>, <em>live</em>, <em>stale</em>, or{" "}
        <em>broken</em> &mdash; see the{" "}
        <Link href="/sources">source inventory</Link> for the full list. This page
        shows the most recent verified probe of the Denver Open Checkbook API,
        the load-bearing dataset for Phase&nbsp;1 ingest.
      </p>

      <h2>Denver Open Checkbook &mdash; column probe</h2>
      {!probe ? (
        <p>
          No <code>data/raw/checkbook_columns.json</code> on disk yet. The
          nightly GitHub Actions workflow writes this file on first run.
        </p>
      ) : (
        <>
          <table>
            <tbody>
              <tr>
                <th>Endpoint</th>
                <td>
                  <a href={probe.endpoint} target="_blank" rel="noreferrer">
                    {probe.endpoint}
                  </a>
                </td>
              </tr>
              <tr>
                <th>Dataset id</th>
                <td>
                  <code>{probe.dataset_id}</code>
                </td>
              </tr>
              <tr>
                <th>Probe fetched at</th>
                <td>{fmtIso(probe.fetched_at)}</td>
              </tr>
              <tr>
                <th>Dataset rows updated at</th>
                <td>{fmtEpoch(probe.rows_updated_at)}</td>
              </tr>
              <tr>
                <th>Resolved vendor field</th>
                <td>
                  <code>{probe.resolved.vendor_field ?? "—"}</code>
                </td>
              </tr>
              <tr>
                <th>Resolved amount field</th>
                <td>
                  <code>{probe.resolved.amount_field ?? "—"}</code>
                </td>
              </tr>
              <tr>
                <th>Resolved date field</th>
                <td>
                  <code>{probe.resolved.date_field ?? "—"}</code>
                </td>
              </tr>
            </tbody>
          </table>

          <h3>All columns</h3>
          <table>
            <thead>
              <tr>
                <th>API field</th>
                <th>Display name</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {probe.columns.map((c) => (
                <tr key={c.fieldName}>
                  <td>
                    <code>{c.fieldName}</code>
                  </td>
                  <td>{c.name}</td>
                  <td>
                    <code>{c.dataTypeName}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>What this unlocks</h3>
          <p>
            With <code>payee</code> (vendor), <code>amount</code>, and{" "}
            <code>paymentdate</code> resolved, the Phase&nbsp;1 ingest can bind
            to real columns instead of guessed ones. The additional fields{" "}
            <code>department</code>, <code>programarea</code>,{" "}
            <code>fundingsourcedescription</code>, <code>project</code>, and{" "}
            <code>expensecategory</code> let us populate the{" "}
            <code>agency</code> and <code>funding_source</code> tables straight
            from checkbook rows without parsing HOST PDFs first.
          </p>
        </>
      )}
    </article>
  );
}
