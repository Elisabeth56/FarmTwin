# ADR-025: Pidgin voice input, English answers; Nigerian languages and mobile deferred

- Status: Accepted
- Date: 2026-11-11

## Context
ADR-011 scoped voice to English after Whisper base and a Nigerian-English fine-tune failed the 40% WER gate on Pidgin. Since then, several open Pidgin-capable models have been released.

## Decision
- **Pidgin in, English out.** Shortlist for the ADR-011 WER gate (same clips, same threshold), each run as a whisper.cpp conversion per ADR-017:
  - NaijaVox-2.0 (Whisper-based; also covers Yoruba, Hausa, Igbo)
  - Africanvoice `african_voices_naija_small` (Whisper-small Pidgin fine-tune)
  - SBPN Base is noted but excluded for now (NeMo, no whisper.cpp path)
  The first model that passes and fits the memory budget ships. Licenses are checked before shipping.
- Answers stay in English. Qwen's understanding of Pidgin questions is measured in the eval (ADR-024) before voice Pidgin is advertised.
- **Deferred: Nigerian languages.** Speech models exist; the 3B LLM is weak in Yoruba, Hausa and Igbo. This needs a separate LLM benchmark.
- **Deferred: mobile.** Tauri v2 can target Android and iOS, but the Python backend cannot run there. A port needs the ADR-019 engine rewritten in TypeScript or Rust, on-device llama.cpp, and a smaller model for typical phone RAM.

## Consequences
- If no candidate passes the gate, voice stays English-only, and that result is published, as ADR-011 was.
