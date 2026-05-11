import Link from "next/link";
import { HBar, MetricCard, MetricGrid, VBar } from "@/components/Charts";
import {
  fmtUSD,
  fmtUSDCompact,
  readRecipients,
  slugify,
} from "@/lib/recipients";

export default function Home() {
  const data = readRecipients();
  if (!data) {
    return (
      <article className="prose-civic">
        <h1>Where does Denver&rsquo;s homelessness money go?</h1>
        <p>Data not loaded yet. The nightly ETL writes data/processed/recipients.json.</p>
      </article>
    );
  }

  const recipients = [...data.recipients].sort((a, b) => b.total_paid - a.total_paid);
  const matched = recipients.filter((r) => r.n_payments > 0);
  const totalPaid =
    data.overview?.total_paid ?? matched.reduce((acc, r) => acc + r.total_paid, 0);
  const byYear = data.by_year ?? [];
  const byDept = data.by_department ?? [];
  const byFunding = data.by_funding ?? [];

  const top10Recipients = matched.slice(0, 10).map((r) => ({
    label: r.legal_name,
    value: r.total_paid,
    href: `/recipients/${r.slug || slugify(r.legal_name)}/`,
  }));

  const top10Departments = byDept.slice(0, 10).map((d) => ({
    label: d.name,
    value: d.total,
    href: `/departments/`,
  }));

  const top10Funding = byFunding.slice(0, 10).map((f) => ({
    label: f.name,
    value: f.total,
    href: `/funding/`,
  }));

  const dateRange =
    data.overview?.first_payment_date && data.overview?.last_payment_date
      ? `${data.overview.first_payment_date.slice(0, 4)}–${data.overview.last_payment_date.slice(0, 4)}`
      : "—";

  return (
    <article className="prose-civic">
      <h1>Where does Denver&rsquo;s homelessness money go?</h1>
      <p>
        This site traces every taxpayer dollar Denver pays to homelessness-related
        nonprofits, drawn directly from the city&rsquo;s{" "}
        <a
          href="https://data.colorado.gov/Business/City-of-Denver-Checkbook/wnau-xrqi"
          target="_blank"
          rel="noreferrer"
        >
          Open Checkbook
        </a>
        . Every number on the site links back to a specific Socrata row. We
        deliberately do <strong>not</strong> publish a single &ldquo;cost per
        homeless person&rdquo; number &mdash; see{" "}
        <Link href="/methodology/">methodology</Link> for why.
      </p>

      <MetricGrid>
        <MetricCard
          label="Total attributed"
          value={fmtUSDCompact(totalPaid)}
          hint={`across ${data.meta.n_payments.toLocaleString()} payments`}
        />
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
          label="Years covered"
          value={dateRange}
          hint={`${data.overview?.n_years ?? byYear.length} years of data`}
        />
        <MetricCard
          label="City departments"
          value={`${data.overview?.n_departments ?? byDept.length}`}
          hint="paying these nonprofits"
        />
        <MetricCard
          label="Funding sources"
          value={`${data.overview?.n_funding_sources ?? byFunding.length}`}
          hint="distinct funds & grants"
        />
      </MetricGrid>

      {byYear.length > 0 && (
        <>
          <h2>Annual spend, year over year</h2>
          <p>
            Total dollars attributed to homelessness-related nonprofits each
            calendar year. ARPA-funded years (2021–2024) and one-time
            voter-approved measure spending typically drive the spikes;
            general-fund baselines drive the steady portion.
          </p>
          <VBar
            items={byYear.map((y) => ({ label: y.year, value: y.total }))}
            formatter={fmtUSDCompact}
          />
        </>
      )}

      {top10Recipients.length > 0 && (
        <>
          <h2>Top 10 recipients</h2>
          <p>
            Click any name for the full payment history, year-over-year
            breakdown, and the city departments funding them.
          </p>
          <HBar items={top10Recipients} formatter={fmtUSDCompact} />
          <p>
            <Link href="/recipients/">See all {matched.length} recipients →</Link>
          </p>
        </>
      )}

      {top10Departments.length > 0 && (
        <>
          <h2>Top 10 city departments paying nonprofits</h2>
          <HBar items={top10Departments} formatter={fmtUSDCompact} />
          <p>
            <Link href="/departments/">All {byDept.length} departments →</Link>
          </p>
        </>
      )}

      {top10Funding.length > 0 && (
        <>
          <h2>Top 10 funding sources</h2>
          <p>
            From the &ldquo;Funding Source Description&rdquo; field in the city
            checkbook. Voter-approved measures like the Homelessness Resolution
            Fund (Ballot 2B, 2020) show up here alongside federal pass-throughs.
          </p>
          <HBar items={top10Funding} formatter={fmtUSDCompact} />
          <p>
            <Link href="/funding/">All {byFunding.length} funding sources →</Link>
          </p>
        </>
      )}

      <h2>Read first</h2>
      <ul>
        <li>
          <Link href="/methodology/">Methodology</Link> &mdash; the tiered
          comparability framework and what we deliberately don&rsquo;t do
        </li>
        <li>
          <Link href="/sources/">Sources</Link> &mdash; every primary dataset
          we&rsquo;ve ingested or plan to ingest, with current status
        </li>
        <li>
          <Link href="/data/">Data status</Link> &mdash; live Socrata column
          probe + the curator-loop &ldquo;new candidates&rdquo; output
        </li>
      </ul>
    </article>
  );
}
