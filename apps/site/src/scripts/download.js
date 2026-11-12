// Download links: point each card at its file in the latest GitHub release, and mark the
// visitor's system. Without a release yet, the cards link to the releases page and say so.
const RELEASES = "https://github.com/Elisabeth56/FarmTwin/releases";
const MATCH = {
  msi: (n) => n.endsWith(".msi"),
  "mac-arm": (n) => n.endsWith(".dmg") && /aarch64|arm64/i.test(n),
  "mac-intel": (n) => n.endsWith(".dmg") && /x64|x86_64|intel/i.test(n),
  linux: (n) => n.endsWith(".AppImage"),
};

const platform = (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || "";
const os = /win/i.test(platform) ? "Windows" : /mac/i.test(platform) ? "MacArm" : /linux|x11/i.test(platform) ? "Linux" : "";
document.querySelector(`.os[data-os="${os}"]`)?.classList.add("mine");
const heroDl = document.getElementById("heroDl");
const label = { Windows: "Download for Windows", MacArm: "Download for Mac", Linux: "Download for Linux" }[os];
if (heroDl && label) heroDl.textContent = label;

const line = document.getElementById("releaseLine");
fetch("https://api.github.com/repos/Elisabeth56/FarmTwin/releases/latest", { headers: { Accept: "application/vnd.github+json" } })
  .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
  .then((release) => {
    document.querySelectorAll("a[data-asset]").forEach((a) => {
      const asset = release.assets.find((x) => MATCH[a.dataset.asset](x.name));
      if (asset) a.href = asset.browser_download_url;
    });
    if (line) line.textContent = `Version ${release.tag_name.replace(/^v/, "")}, released ${new Date(release.published_at).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })}.`;
  })
  .catch(() => {
    document.querySelectorAll("a[data-asset]").forEach((a) => {
      a.textContent = "See releases";
      a.href = RELEASES;
    });
    if (line) line.textContent = "The first desktop release is on its way. The releases page lists every build.";
  });
