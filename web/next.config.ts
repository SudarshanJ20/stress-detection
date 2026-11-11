import type { NextConfig } from "next";
const config: NextConfig = {
  poweredByHeader: false,
  experimental: { proxyClientMaxBodySize: "100mb" },
  async rewrites() {
    return [
      {
        source: "/api/local/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Referrer-Policy", value: "no-referrer" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Permissions-Policy", value: "camera=(self), microphone=()" },
        ],
      },
    ];
  },
};
export default config;
