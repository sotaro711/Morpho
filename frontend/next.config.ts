import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 段付き周期構造の計算(81 波長 × 基底数 61)は 30 秒を超えることがあり、
  // 既定のプロキシタイムアウトだと socket hang up で切断されるため延長する。
  experimental: {
    proxyTimeout: 180_000,
  },
  // フロントの /api/* を FastAPI バックエンド (:8000) へプロキシする。
  // 同一オリジンになるため CORS 設定が不要になる。
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
