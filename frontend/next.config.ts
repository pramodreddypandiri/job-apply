import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Proxy API calls to backend in development
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
