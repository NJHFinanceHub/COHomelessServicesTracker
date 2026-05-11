import Link from "next/link";
import {
  readCatalogHits,
  readCheckbookColumnProbe,
  readCheckbookDateRange,
} from "@/lib/data-sources";
import { fmtUSDCompact } from "@/lib/recipients";

export const metadata = {
  title: "Data status — Denver Homelessness Dollar Tracker",
};

function fmtEpoch(epoch: number | null): string {
  if (!epoch) return "—";
  return new Date(epoch * 1000).toISOString().replace("T", " ").replace(/\..+/, " UTC");
}

function fmtIso(iso: string | null): string {
  if (!iso) return "—";
  return iso.replace("T", " ").replace(/\..+/, " UTC");
}

export default function DataStatusPage() {
  const probe = readCheckbookColumnProbe();
  const dateRange = readCheckbookDateRange();
  const catalog = readCatalogHits();

  return (
    <article className="prose-civic">
      <h1>Data status</h1>
      <p>
        Each upstream source has a status of <em>not yet ingested</em>,{" "}
        <em>scaffolded</em>, <em>piloted</em>, <em>live</em>, <em>stale</em>, or{" "}
        <em>broken</em> &mdash; see the{" "}
        <Link href="/sources/">source inventory</Link> for the full list. This
        page shows the most recent verified probes of the Denver Open Checkbook
        dataset, the load-bearing source for Phase&nbsp;1.
      </p>

      {dateRange && (
        <>
          <h2>Dataset coverage &mdash; current-year only</h2>
          <p>
            <strong>The dataset only contains 2025.</strong> Denver&rsquo;s
            Socrata-hosted &ldquo;Open Checkbook&rdquo; (id <code>wnau-xrqi</code>)
            rolls over every January and retains current-year payments only.
            Direct evidence from the dataset, returned by aggregate query:
          </p>
          <table>
            <tbody>
              <tr>
                <th>Earliest paymentdate</th>
                <td>{dateRange.min_date ?? "—"}</td>
              </tr>
              <tr>
                <th>Latest paymentdate</th>
                <td>{dateRange.max_date ?? "—"}</td>
              </tr>
              <tr>
                <th>Total rows in dataset</th>
                <td>{dateRange.n_total_rows.toLocaleString()}</td>
              </tr>
              <tr>
                <th>Total amount (all Denver, not just homelessness)</th>
                <td>
                  {dateRange.sum_total !== null
                    ? fmtUSDCompact(dateRange.sum_total)
                    : "—"}
                </td>
              </tr>
              <tr>
                <th>Probe last fetched</th>
                <td>{fmtIso(dateRange.fetched_at)}</td>
              </tr>
            </tbody>
          </table>
          {dateRange.per_year.length > 0 && (
            <>
              <h3>Per-year row counts</h3>
              <table>
                <thead>
                  <tr>
                    <th>Year</th>
                    <th>Rows</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {dateRange.per_year.map((y) => (
                    <tr key={y.year}>
                      <td>{y.year}</td>
                      <td>{y.n_payments.toLocaleString()}</td>
                      <td>
                        {y.total !== null ? fmtUSDCompact(y.total) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
          <p>
            Implication for the rest of this site: every number you see comes
            from 2025 payments. The &ldquo;by year&rdquo; chart on the home
            page is one bar by necessity until we add an alternate historical
            source.
          </p>
          <h3>Where multi-year data may live</h3>
          <ul>
            <li>
              <strong>Denver Open Data Portal</strong> (denvergov.org/opendata):
              the city operates its own portal and may publish historical
              checkbook exports there as static CSVs.
            </li>
            <li>
              <strong>HOST Annual Action Plans</strong> (2020-onward):
              budget-level multi-year figures, PDF — extraction is in the
              source-inventory backlog.
            </li>
            <li>
              <strong>Denver Auditor reports</strong>: routinely audit
              department spending and publish multi-year tables.
            </li>
            <li>
              <strong>Web Archive snapshots</strong> of the Socrata dataset
              from prior Januaries: theoretically captures pre-rollover state.
            </li>
          </ul>
          {catalog && catalog.hits.length > 0 && (
            <>
              <p>
                The nightly Socrata Discovery API probe found{" "}
                <strong>{catalog.n_hits_filtered}</strong> potentially-related
                datasets across data.colorado.gov (and other Socrata domains):
              </p>
              <table>
                <thead>
                  <tr>
                    <th>Domain</th>
                    <th>Dataset</th>
                    <th>Updated</th>
                    <th>Link</th>
                  </tr>
                </thead>
                <tbody>
                  {catalog.hits.slice(0, 30).map((h) => (
                    <tr key={h.id}>
                      <td>{h.domain ?? "—"}</td>
                      <td>{h.name ?? h.id}</td>
                      <td>{h.updatedAt?.slice(0, 10) ?? "—"}</td>
                      <td>
                        {h.permalink ? (
                          <a href={h.permalink} target="_blank" rel="noreferrer">
                            open
                          </a>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </>
      )}

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
        </>
      )}
    </article>
  );
}
