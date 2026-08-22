# Day 5.5 STT Evaluation — rishabbahal/whisper-small-nigerian-accent

Date: 2026-08-22
Model: rishabbahal/whisper-small-nigerian-accent (Whisper-small fine-tuned on Nigerian-accented English)

## Aggregate

| Language | Clips | Mean WER | Mean Latency |
|----------|-------|----------|-------------|
| English  | 8 | 17.9% | 5.8s |
| Pidgin   | 7 | 58.7% | 5.5s |

## Comparison to Whisper base

- English: base 32.8% → this 17.9%
- Pidgin: base 56.1% → this 58.7%

**Gate (Pidgin ≤ 40%): FAIL**

## Per-clip

### en_01.m4a
- WER: 0.000 | Latency: 12.7s
- REF: `What should I do this week?`
- HYP: `What should I do this week?`

### en_02.m4a
- WER: 0.250 | Latency: 4.3s
- REF: `Is my maize at risk from the rain?`
- HYP: `It's my maze at risk from the rain.`

### en_03.m4a
- WER: 0.000 | Latency: 4.8s
- REF: `How can I tell if my crop has fungal disease?`
- HYP: `How can I tell if my crop has fungal disease?`

### en_04.m4a
- WER: 0.300 | Latency: 4.9s
- REF: `The humidity has been high for three days. What now?`
- HYP: `The humidity has been high for three days. What do I do?`

### en_05.m4a
- WER: 0.250 | Latency: 5.1s
- REF: `My plants are yellowing in the lower leaves. What could cause that?`
- HYP: `My plants are yellowing in Idoa leaves. What can cause that?`

### en_06.m4a
- WER: 0.375 | Latency: 4.8s
- REF: `When should I apply fertilizer to my maize?`
- HYP: `When should I apply face visor to my face?`

### en_07.m4a
- WER: 0.091 | Latency: 4.9s
- REF: `There were pests in the whorls yesterday. Should I be worried?`
- HYP: `There were pests in the walls yesterday, should I be worried?`

### en_08.m4a
- WER: 0.167 | Latency: 5.2s
- REF: `How much rain is too much rain for maize at this stage?`
- HYP: `How much rain is too much rain for me is at this stage.`

### pidgin_01.m4a
- WER: 0.500 | Latency: 4.6s
- REF: `Wetin I go do dis week?`
- HYP: `Wait till I go do this week.`

### pidgin_02.m4a
- WER: 0.571 | Latency: 4.8s
- REF: `My maize dey risk from the rain?`
- HYP: `My maze day is from the ring`

### pidgin_03.m4a
- WER: 1.000 | Latency: 5.0s
- REF: `How I go know say my crop get fungus?`
- HYP: `Haraigunosse Mykoggia Fongos`

### pidgin_04.m4a
- WER: 0.700 | Latency: 5.3s
- REF: `Humidity don high for three days. Wetin i go do?`
- HYP: `Humiditi don't hide for three days.  We sleep alone.`

### pidgin_05.m4a
- WER: 0.583 | Latency: 5.7s
- REF: `My plants dey yellow for the down leaves. Wetin fit cause am?`
- HYP: `My plants stay yellow for the downlifts waiting for Kossan.`

### pidgin_06.m4a
- WER: 0.200 | Latency: 6.2s
- REF: `Wetin be the time to put fertilizer for my maize?`
- HYP: `Waiting be the time to put fertilizer for my mis.`

### pidgin_07.m4a
- WER: 0.556 | Latency: 7.0s
- REF: `Pest dey inside the whorl yesterday. Make I worry?`
- HYP: `Pass the inside of the wall yesterday, make eye worry.`

