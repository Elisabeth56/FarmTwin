// Things only the desktop shell can do. In a browser these return null and the UI falls back.

export function inDesktopApp(): boolean {
  return "__TAURI_INTERNALS__" in window;
}

/** Opens the system file picker for a .gguf file and returns its path. */
export async function pickModelFile(kind: "model" | "voice" = "model"): Promise<string | null> {
  if (!inDesktopApp()) return null;
  const { open } = await import("@tauri-apps/plugin-dialog");
  const picked = await open({ multiple: false, filters: kind === "voice" ? [{ name: "Voice model", extensions: ["bin"] }] : [{ name: "AI model", extensions: ["gguf"] }] });
  return typeof picked === "string" ? picked : null;
}
