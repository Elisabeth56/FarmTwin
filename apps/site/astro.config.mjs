import starlight from "@astrojs/starlight";
import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://farmtwin.vercel.app",
  integrations: [
    starlight({
      title: "FarmTwin docs",
      logo: { src: "./src/assets/mark.svg", replacesTitle: false },
      favicon: "/favicon.svg",
      customCss: ["@fontsource/hanken-grotesk/400.css", "./src/styles/docs.css"],
      social: [{ icon: "github", label: "GitHub", href: "https://github.com/Elisabeth56/FarmTwin" }],
      sidebar: [
        { label: "Get started", items: ["docs", "docs/install", "docs/first-run"] },
        { label: "Using FarmTwin", items: ["docs/farms", "docs/logging", "docs/asking"] },
        { label: "Help", items: ["docs/updates", "docs/troubleshooting"] },
      ],
    }),
  ],
});
