/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // Browser -> API routing (slice 1): the API service is internal-only
  // in compose (no published port), so the browser never talks to it
  // directly. Next.js proxies same-origin /api/* to the internal API.
  // API_INTERNAL_URL is set at build/deploy time: http://api:8000 in
  // compose, http://127.0.0.1:8000 for local dev.
  async rewrites() {
    const apiBase = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${apiBase}/api/:path*` }];
  },
};

module.exports = nextConfig;
