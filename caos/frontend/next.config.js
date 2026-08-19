const { PHASE_DEVELOPMENT_SERVER } = require("next/constants");

const base = {
  reactStrictMode: true,
  output: "export",
  trailingSlash: true,
  skipTrailingSlashRedirect: true,
  images: { unoptimized: true },
  experimental: {
    turbopackFileSystemCacheForDev: false,
  },
};

module.exports = (phase) => phase === PHASE_DEVELOPMENT_SERVER
  ? {
      ...base,
      async rewrites() {
        return [{ source: "/api/:path*", destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*` }];
      },
    }
  : base;
