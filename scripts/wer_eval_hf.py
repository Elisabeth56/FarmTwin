"""
Day 5.5 STT re-evaluation: HF Whisper fine-tuned on Nigerian accented English.
Same 15 clips + same reference file as wer_eval.py.
"""
import os
import sys
import time
import re
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CLIPS_DIR = REPO_ROOT / "evaluation" / "stt_clips"
RESULTS_DIR = REPO_ROOT / "evaluation" / "stt_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
REFERENCE_FILE = CLIPS_DIR / "reference.txt"

MODEL_ID = "rishabbahal/whisper-small-nigerian-accent"

sys.path.insert(0, str(REPO_ROOT / "backend"))

import soundfile as sf
import numpy as np
from transformers import WhisperForConditionalGeneration, WhisperProcessor


def normalize(text):
    text = text.lower()
    text = re.sub(r"[^\w\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def wer(reference, hypothesis):
    ref = normalize(reference).split()
    hyp = normalize(hypothesis).split()
    if not ref:
        return 1.0 if hyp else 0.0
    d = [[0] * (len(hyp) + 1) for _ in range(len(ref) + 1)]
    for i in range(len(ref) + 1): d[i][0] = i
    for j in range(len(hyp) + 1): d[0][j] = j
    for i in range(1, len(ref) + 1):
        for j in range(1, len(hyp) + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            d[i][j] = min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+cost)
    return d[len(ref)][len(hyp)] / len(ref)


def convert_to_wav(m4a_path):
    wav_path = m4a_path.with_suffix(".converted.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(m4a_path),
         "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
         str(wav_path)],
        check=True, capture_output=True, timeout=30
    )
    return wav_path


def parse_reference(ref_file):
    refs = {}
    for line in ref_file.read_text().splitlines():
        line = line.strip()
        if not line or "|" not in line: continue
        filename, text = line.split("|", 1)
        refs[filename.strip()] = text.strip()
    return refs


def main():
    print(f"Loading model {MODEL_ID}... (already cached, ~5s)")
    t0 = time.time()
    processor = WhisperProcessor.from_pretrained(MODEL_ID)
    model = WhisperForConditionalGeneration.from_pretrained(MODEL_ID)
    model.eval()
    print(f"Loaded in {time.time()-t0:.1f}s")

    print(f"Loading references from {REFERENCE_FILE}")
    refs = parse_reference(REFERENCE_FILE)
    print(f"{len(refs)} clips to evaluate\n")

    results = []
    en_wers, pidgin_wers = [], []
    en_lat, pidgin_lat = [], []

    for filename in sorted(refs.keys()):
        clip_path = CLIPS_DIR / filename
        if not clip_path.exists():
            print(f"MISSING: {filename}")
            continue

        try:
            wav_path = convert_to_wav(clip_path)
        except Exception as e:
            print(f"FFMPEG FAIL {filename}: {e}")
            continue

        # Load audio via soundfile
        audio, sr = sf.read(str(wav_path))
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        audio = audio.astype(np.float32)

        reference = refs[filename]
        is_pidgin = filename.startswith("pidgin")

        try:
            t0 = time.time()
            inputs = processor(audio, sampling_rate=16000, return_tensors="pt")
            import torch
            with torch.no_grad():
                predicted_ids = model.generate(
                    inputs.input_features,
                    max_new_tokens=200,
                    language="en",
                    task="transcribe"
                )
            hypothesis = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0].strip()
            elapsed = time.time() - t0
        except Exception as e:
            print(f"WHISPER FAIL {filename}: {e}")
            wav_path.unlink(missing_ok=True)
            continue

        clip_wer = wer(reference, hypothesis)

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
            pidgin_lat.append(elapsed)
        else:
            en_wers.append(clip_wer)
            en_lat.append(elapsed)

        print(f"[{filename}] {('pidgin' if is_pidgin else 'en'):6s} WER={clip_wer:.3f} lat={elapsed:.1f}s")
        print(f"  REF: {reference}")
        print(f"  HYP: {hypothesis}")
        print()

        wav_path.unlink(missing_ok=True)

    en_mean = sum(en_wers)/len(en_wers) if en_wers else float("nan")
    pidgin_mean = sum(pidgin_wers)/len(pidgin_wers) if pidgin_wers else float("nan")

    print("=" * 60)
    print("AGGREGATE — rishabbahal/whisper-small-nigerian-accent")
    print("=" * 60)
    print(f"English: n={len(en_wers)}, mean WER={en_mean:.3f} ({en_mean*100:.1f}%), mean latency={sum(en_lat)/len(en_lat):.1f}s")
    print(f"Pidgin:  n={len(pidgin_wers)}, mean WER={pidgin_mean:.3f} ({pidgin_mean*100:.1f}%), mean latency={sum(pidgin_lat)/len(pidgin_lat):.1f}s")
    print()

    # Compare to Whisper base
    print("COMPARISON to Whisper base (Day 5.5 first run):")
    print(f"  English: base=32.8% → this={en_mean*100:.1f}% ({'BETTER' if en_mean<0.328 else 'WORSE'})")
    print(f"  Pidgin:  base=56.1% → this={pidgin_mean*100:.1f}% ({'BETTER' if pidgin_mean<0.561 else 'WORSE'})")
    print()
    print(f"GATE (Pidgin ≤ 40%): {'PASS ✓' if pidgin_mean <= 0.40 else 'FAIL ✗'}")

    # Write report
    report_path = RESULTS_DIR / "day5_5_wer_hf.md"
    with report_path.open("w") as f:
        f.write(f"# Day 5.5 STT Evaluation — {MODEL_ID}\n\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d')}\n")
        f.write(f"Model: {MODEL_ID} (Whisper-small fine-tuned on Nigerian-accented English)\n\n")
        f.write("## Aggregate\n\n")
        f.write("| Language | Clips | Mean WER | Mean Latency |\n")
        f.write("|----------|-------|----------|-------------|\n")
        f.write(f"| English  | {len(en_wers)} | {en_mean*100:.1f}% | {sum(en_lat)/len(en_lat):.1f}s |\n")
        f.write(f"| Pidgin   | {len(pidgin_wers)} | {pidgin_mean*100:.1f}% | {sum(pidgin_lat)/len(pidgin_lat):.1f}s |\n\n")
        f.write("## Comparison to Whisper base\n\n")
        f.write(f"- English: base 32.8% → this {en_mean*100:.1f}%\n")
        f.write(f"- Pidgin: base 56.1% → this {pidgin_mean*100:.1f}%\n\n")
        f.write(f"**Gate (Pidgin ≤ 40%): {'PASS' if pidgin_mean <= 0.40 else 'FAIL'}**\n\n")
        f.write("## Per-clip\n\n")
        for r in results:
            f.write(f"### {r['filename']}\n")
            f.write(f"- WER: {r['wer']:.3f} | Latency: {r['latency_s']:.1f}s\n")
            f.write(f"- REF: `{r['reference']}`\n")
            f.write(f"- HYP: `{r['hypothesis']}`\n\n")
    print(f"\nReport → {report_path}")


if __name__ == "__main__":
    main()
