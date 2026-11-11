# ADR-011: STT model swap — Nigerian-accented English fine-tune, EN-only
Date: 2026-08-22
Status: Accepted

Context: Day 5.5 evaluation of whisper.cpp base (60MB, multilingual) on 15 recorded clips
(8 English, 7 Nigerian Pidgin recorded by native speaker) showed:
- English: 32.8% mean WER
- Pidgin: 56.1% mean WER — above 40% gate threshold

Investigated NCAIR1/NigerianAccentedEnglish (gated, requires manual access approval)
and Orinode (Q3 2026 product, unclear open-model availability). Evaluated
rishabbahal/whisper-small-nigerian-accent (967MB, public, Whisper-small fine-tune):
- English: 17.9% mean WER (45% relative improvement over base)
- Pidgin: 58.7% mean WER — still above gate

Decision: Ship rishabbahal/whisper-small-nigerian-accent as EN-only STT rebranded
"Nigerian English". Pidgin STT deferred to future work.

Consequences:
- Backend: whisper_client.py replaced with HF transformers (module-level singleton loader).
  Previous whisper.cpp subprocess client preserved as whisper_cli_client.py for reference.
- Frontend: language toggle removed, mic button labeled "Voice input (Nigerian English)".
- Memory: HF Whisper-small resident + PyTorch runtime + llama-server. Verified in
  Day 5.5 memory test — total stays under 7GB ceiling.
- REPORT.md: honest documentation of Pidgin gap in open ASR ecosystem, with pointers
  to Orinode and NCAIR1 as future integration paths.
