import Link from "next/link";

export default function Home() {
  return (
    <div className="prose-civic">
      <h1>Where does Denver&rsquo;s homelessness money go?</h1>
      <p>
        This site traces every taxpayer dollar Denver spends on homelessness from its
        source &mdash; federal, state, and local taxes; bond proceeds; voter-approved
        sales-tax measures &mdash; through the city department that received it,
        the nonprofit it was paid to, and the program that was supposed to use it,
        all the way to the outcomes those programs reported.
      </p>
      <p>
        It is <strong>not</strong> a leaderboard. It does not publish a single
        &ldquo;cost per homeless person&rdquo; number, because that number is almost
        always wrong (see <Link href="/methodology">methodology</Link>). It computes
        per-unit costs only within comparable service categories, with explicit
        confidence tiers and a primary source linked from every number.
      </p>
      <h2>Status</h2>
      <p>
        <strong>Phase 0 &mdash; foundation.</strong> The repo is scaffolded, the data
        model and methodology are published, and the Denver Open Checkbook
        ingester is wired up but not yet running in production. No dollar figures
        appear on this site yet.
      </p>
      <h2>Read first</h2>
      <ul>
        <li>
          <Link href="/methodology">Methodology</Link> &mdash; how we compute
          per-unit costs and what we deliberately do not do
        </li>
        <li>
          <Link href="/sources">Sources</Link> &mdash; every primary dataset
          we plan to ingest, with current status
        </li>
        <li>
          <a
            href="https://github.com/njhfinancehub/cohomelessservicestracker/blob/main/PROJECT_PLAN.md"
            target="_blank"
            rel="noreferrer"
          >
            Project plan
          </a>{" "}
          &mdash; the full brief, including phased build plan and risk register
        </li>
      </ul>
    </div>
  );
}
