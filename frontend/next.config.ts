/** Export to out/ for FastAPI; Node is used only during development/build. */
import type { NextConfig } from "next";

const config: NextConfig = { output: "export", trailingSlash: true, poweredByHeader: false };
export default config;
