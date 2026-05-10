import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Hide the floating "N" route-status badge that Next.js renders in the
  // bottom-left during dev. Next still surfaces real build/runtime errors;
  // we just don't want the badge over the chat UI for demo screenshots.
  devIndicators: false,
};

export default nextConfig;
