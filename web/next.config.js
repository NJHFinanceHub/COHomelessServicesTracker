/** @type {import('next').NextConfig} */
// When building inside GitHub Actions for GitHub Pages, the site lives at
// /COHomelessServicesTracker/ on njhfinancehub.github.io. Local dev runs at
// the root so we keep basePath empty unless GITHUB_ACTIONS is set.
const isCI = !!process.env.GITHUB_ACTIONS;
const basePath = isCI ? "/COHomelessServicesTracker" : "";

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Pre-generate every page as static HTML for GitHub Pages.
  output: "export",
  // GitHub Pages serves /foo/ → /foo/index.html, so emit clean trailing-slash URLs.
  trailingSlash: true,
  basePath,
  assetPrefix: basePath,
  // No image optimizer in static export.
  images: { unoptimized: true },
};

module.exports = nextConfig;
