import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Denver Homelessness Dollar Tracker",
  description:
    "Tracing every taxpayer dollar Denver spends on homelessness — from source to recipient to reported outcomes, with primary-source citations on every number.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        <header className="border-b border-stone-200 bg-white">
          <div className="max-w-5xl mx-auto px-4 py-4 flex flex-wrap items-baseline gap-4">
            <Link href="/" className="font-semibold text-lg">
              Denver Homelessness Dollar Tracker
            </Link>
            <nav className="flex gap-4 text-sm text-stone-600 ml-auto">
              <Link href="/methodology" className="hover:text-stone-900">
                Methodology
              </Link>
              <Link href="/sources" className="hover:text-stone-900">
                Sources
              </Link>
              <Link href="/data" className="hover:text-stone-900">
                Data status
              </Link>
              <a
                href="https://github.com/njhfinancehub/cohomelessservicestracker"
                className="hover:text-stone-900"
                target="_blank"
                rel="noreferrer"
              >
                GitHub
              </a>
            </nav>
          </div>
        </header>
        <main className="flex-1 max-w-5xl mx-auto px-4 py-8 w-full">{children}</main>
        <footer className="border-t border-stone-200 mt-8">
          <div className="max-w-5xl mx-auto px-4 py-6 text-sm text-stone-500">
            Phase 0 — scaffold. Numbers are not yet published. See the{" "}
            <Link href="/methodology" className="underline">
              methodology
            </Link>{" "}
            for the framing.
          </div>
        </footer>
      </body>
    </html>
  );
}
