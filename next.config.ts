import type { NextConfig } from "next";

// GitHub Pages project sites live under /<repo>. The workflow passes the
// base path from actions/configure-pages; locally it is empty.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

const nextConfig: NextConfig = {
  output: "export",
  basePath,
  trailingSlash: true,
  images: { unoptimized: true },
  reactStrictMode: true,
};

export default nextConfig;
