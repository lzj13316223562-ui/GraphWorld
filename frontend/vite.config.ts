import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const allowedHosts = [".cpolar.io", ".cpolar.cn", ".cpolar.top"];
const proxy = {
  "/api": "http://127.0.0.1:8010",
};

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts,
    proxy,
  },
  preview: {
    allowedHosts,
    proxy,
  },
});
