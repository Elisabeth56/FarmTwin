"""
Day 5.5 STT evaluation: computes WER for English and Pidgin clips
against the reference transcripts. Also measures Whisper peak RSS.

Runs the existing whisper_client.transcribe() function on each clip,
uses English decoder for all (per Amendment #1: Whisper has no Pidgin,
English decoder handles Pidgin-adjacent speech reasonably).

Output: written to evaluation/stt_results/day5_5_wer.md
"""

import os
import sys
import time
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CLIPS_DIR = REPO_ROOT / "evaluation" / "stt_clips"
RESULTS_DIR = REPO_ROOT / "evaluation" / "stt_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
REFERENCE_FILE = CLIPS_DIR / "reference.txt"

# Add backend to path so we can import whisper_client
sys.path.insert(0, str(REPO_ROOT / "backend"))
os.chdir(REPO_ROOT / "backend")

from app.stt.whisper_client import transcribe


def normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace. Standard WER prep."""
    text = text.lower()
    text = re.sub(r"[^\w\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def wer(reference: str, hypothesis: str) -> float:
    """Word Error Rate via Levenshtein on token lists."""
    ref = normalize(reference).split()
    hyp = normalize(hypothesis).split()
    if not ref:
        return 1.0 if hyp else 0.0

    # DP table
    d = [[0] * (len(hyp) + 1) for _ in range(len(ref) + 1)]
    for i in range(len(ref) + 1):
        d[i][0] = i
    for j in range(len(hyp) + 1):
        d[0][j] = j
    for i in range(1, len(ref) + 1):
        for j in range(1, len(hyp) + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,       # deletion
                d[i][j - 1] + 1,       # insertion
                d[i - 1][j - 1] + cost # substitution
            )
    return d[len(ref)][len(hyp)] / len(ref)


def convert_to_wav(m4a_path: Path) -> Path:
    """Whisper needs WAV. ffmpeg is already available."""
    wav_path = m4a_path.with_suffix(".converted.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(m4a_path),
         "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
         str(wav_path)],
        check=True, capture_output=True, timeout=30
    )
    return wav_path


def parse_reference(ref_file: Path) -> dict[str, str]:
    refs = {}
    for line in ref_file.read_text().splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        filename, text = line.split("|", 1)
        refs[filename.strip()] = text.strip()
    return refs


def measure_peak_rss(pid: int) -> int:
    """Read peak RSS in KB from macOS ps."""
    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "rss="],
        capture_output=True, text=True
    )
    return int(result.stdout.strip()) if result.stdout.strip() else 0


def main():
    print(f"Loading references from {REFERENCE_FILE}")
    refs = parse_reference(REFERENCE_FILE)
    print(f"Loaded {len(refs)} reference transcripts")

    results = []
    en_wers, pidgin_wers = [], []
    en_latencies, pidgin_latencies = [], []
    max_rss_kb = 0

    for filename in sorted(refs.keys()):
        clip_path = CLIPS_DIR / filename
        if not clip_path.exists():
            print(f"MISSING: {filename}")
            continue

        # Convert to WAV
        try:
            wav_path = convert_to_wav(clip_path)
        except Exception as e:
            print(f"FFMPEG FAIL {filename}: {e}")
            continue

        reference = refs[filename]
        is_pidgin = filename.startswith("pidgin")

        # Transcribe (English decoder for both, per Amendment #1)
        try:
            t0 = time.time()
            result = transcribe(str(wav_path), language="en")
            elapsed = time.time() - t0
            hypothesis = result["text"]
        except Exception as e:
            print(f"WHISPER FAIL {filename}: {e}")
            wav_path.unlink(missing_ok=True)
            continue

        # WER
        clip_wer = wer(reference, hypothesis)

        # Track memory
        rss = measure_peak_rss(os.getpid())
        max_rss_kb = max(max_rss_kb, rss)

        # Store
        results.append({
            "filename": filename,
            "language": "pidgin" if is_pidgin else "en",
            "reference": reference,
            "hypothesis": hypothesis,
            "wer": clip_wer,
            "latency_s": elapsed,
        })

        if is_pidgin:
            pidgin_wers.append(clip_wer)
            pidgin_latencies.append(elapsed)
        else:
            en_wers.append(clip_wer)
            en_latencies.append(elapsed)

        print(f"[{filename}] lang={('pidgin' if is_pidgin else 'en'):6s} "
              f"WER={clip_wer:.3f} lat={elapsed:.1f}s")
        print(f"  REF: {reference}")
        print(f"  HYP: {hypothesis}")
        print()

        # Cleanup
        wav_path.unlink(missing_ok=True)

    # Aggregate
    en_mean_wer = sum(en_wers) / len(en_wers) if en_wers else float("nan")
    pidgin_mean_wer = sum(pidgin_wers) / len(pidgin_wers) if pidgin_wers else float("nan")
    en_mean_lat = sum(en_latencies) / len(en_latencies) if en_latencies else float("nan")
    pidgin_mean_lat = sum(pidgin_latencies) / len(pidgin_latencies) if pidgin_latencies else float("nan")

    print("=" * 60)
    print("AGGREGATE RESULTS")
    print("=" * 60)
    print(f"English clips: n={len(en_wers)}, mean WER={en_mean_wer:.3f} ({en_mean_wer*100:.1f}%), mean latency={en_mean_lat:.1f}s")
    print(f"Pidgin clips:  n={len(pidgin_wers)}, mean WER={pidgin_mean_wer:.3f} ({pidgin_mean_wer*100:.1f}%), mean latency={pidgin_mean_lat:.1f}s")
    print(f"Script peak RSS: {max_rss_kb/1024:.0f} MB")

    # Write markdown report
    report_path = RESULTS_DIR / "day5_5_wer.md"
    with report_path.open("w") as f:
        f.write("# Day 5.5 STT Evaluation Results\n\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d')}\n")
        f.write(f"Whisper model: ggml-base-q5_1.bin (60MB, multilingual base)\n")
        f.write("Decoder language: `en` for all clips (Amendment #1: Whisper has no native Pidgin)\n\n")

        f.write("## Aggregate\n\n")
        f.write(f"| Language | Clips | Mean WER | Mean Latency |\n")
        f.write(f"|----------|-------|----------|-------------|\n")
        f.write(f"| English  | {len(en_wers)}     | {en_mean_wer:.3f} ({en_mean_wer*100:.1f}%) | {en_mean_lat:.1f}s |\n")
        f.write(f"| Pidgin   | {len(pidgin_wers)}     | {pidgin_mean_wer:.3f} ({pidgin_mean_wer*100:.1f}%) | {pidgin_mean_lat:.1f}s |\n\n")
        f.write(f"Script peak RSS (whisper only, not counting llama-server): {max_rss_kb/1024:.0f} MB\n\n")

        f.write("## Gate criteria (Amendment #1)\n\n")
        f.write("- Pidgin WER ≤ 40% AND combined RSS (whisper+LLM) < 6.5 GB → **Ship bilingual**\n")
        f.write("- Else → **Ship EN-only**\n\n")

        pidgin_pass = pidgin_mean_wer <= 0.40
        f.write(f"**Pidgin WER gate**: {pidgin_mean_wer*100:.1f}% {'PASS' if pidgin_pass else 'FAIL'} (threshold 40%)\n\n")
        f.write("(Combined RSS with llama-server measured separately.)\n\n")

        f.write("## Per-clip results\n\n")
        for r in results:
            f.write(f"### {r['filename']} ({r['language']})\n")
            f.write(f"- WER: {r['wer']:.3f}\n")
            f.write(f"- Latency: {r['latency_s']:.1f}s\n")
            f.write(f"- Reference: `{r['reference']}`\n")
            f.write(f"- Hypothesis: `{r['hypothesis']}`\n\n")

    print(f"\nReport written to {report_path}")


if __name__ == "__main__":
    main()
