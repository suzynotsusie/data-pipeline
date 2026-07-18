import type { NextConfig } from "next";

const backendOrigin = (process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010").replace(/\/$/, "");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
