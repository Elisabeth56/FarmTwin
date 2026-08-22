# Day 5.5 STT Evaluation Results

Date: 2026-08-22
Whisper model: ggml-base-q5_1.bin (60MB, multilingual base)
Decoder language: `en` for all clips (Amendment #1: Whisper has no native Pidgin)

## Aggregate

| Language | Clips | Mean WER | Mean Latency |
|----------|-------|----------|-------------|
| English  | 8     | 0.328 (32.8%) | 2.8s |
| Pidgin   | 7     | 0.561 (56.1%) | 2.5s |

Script peak RSS (whisper only, not counting llama-server): 7 MB

## Gate criteria (Amendment #1)

- Pidgin WER ≤ 40% AND combined RSS (whisper+LLM) < 6.5 GB → **Ship bilingual**
- Else → **Ship EN-only**

**Pidgin WER gate**: 56.1% FAIL (threshold 40%)

(Combined RSS with llama-server measured separately.)

## Per-clip results

### en_01.m4a (en)
- WER: 0.000
- Latency: 3.2s
- Reference: `What should I do this week?`
- Hypothesis: `What should I do this week?`

### en_02.m4a (en)
- WER: 0.375
- Latency: 4.2s
- Reference: `Is my maize at risk from the rain?`
- Hypothesis: `is my mise at wrist from the ring`

### en_03.m4a (en)
- WER: 0.000
- Latency: 2.9s
- Reference: `How can I tell if my crop has fungal disease?`
- Hypothesis: `How can I tell if my crop has fungal disease?`

### en_04.m4a (en)
- WER: 0.800
- Latency: 2.5s
- Reference: `The humidity has been high for three days. What now?`
- Hypothesis: `If you meet C has been high for 3 days, what do I do?`

### en_05.m4a (en)
- WER: 0.500
- Latency: 2.4s
- Reference: `My plants are yellowing in the lower leaves. What could cause that?`
- Hypothesis: `My plants are yellow and yellow at least. What can cause that?`

### en_06.m4a (en)
- WER: 0.500
- Latency: 2.5s
- Reference: `When should I apply fertilizer to my maize?`
- Hypothesis: `When shall I apply face visor to my knees?`

### en_07.m4a (en)
- WER: 0.364
- Latency: 2.2s
- Reference: `There were pests in the whorls yesterday. Should I be worried?`
- Hypothesis: `very past in the world yesterday should i be worried?`

### en_08.m4a (en)
- WER: 0.083
- Latency: 2.6s
- Reference: `How much rain is too much rain for maize at this stage?`
- Hypothesis: `How much rain is too much rain for me at this stage?`

### pidgin_01.m4a (pidgin)
- WER: 0.667
- Latency: 2.6s
- Reference: `Wetin I go do dis week?`
- Hypothesis: `Wait until I go to this week.`

### pidgin_02.m4a (pidgin)
- WER: 0.571
- Latency: 2.4s
- Reference: `My maize dey risk from the rain?`
- Hypothesis: `My midday is from the ring.`

### pidgin_03.m4a (pidgin)
- WER: 0.556
- Latency: 2.3s
- Reference: `How I go know say my crop get fungus?`
- Hypothesis: `How are you gonna see my clock get fungus?`

### pidgin_04.m4a (pidgin)
- WER: 0.400
- Latency: 2.7s
- Reference: `Humidity don high for three days. Wetin i go do?`
- Hypothesis: `Humidity don't high for 3 days. Listen I go to.`

### pidgin_05.m4a (pidgin)
- WER: 0.667
- Latency: 2.4s
- Reference: `My plants dey yellow for the down leaves. Wetin fit cause am?`
- Hypothesis: `My plans stay yellow for the town these, which in Fiko-san.`

### pidgin_06.m4a (pidgin)
- WER: 0.400
- Latency: 2.8s
- Reference: `Wetin be the time to put fertilizer for my maize?`
- Hypothesis: `waiting be the time to perfectilize our for my miss`

### pidgin_07.m4a (pidgin)
- WER: 0.667
- Latency: 2.3s
- Reference: `Pest dey inside the whorl yesterday. Make I worry?`
- Hypothesis: `Passed inside the wall yesterday, Mikai Roy.`

