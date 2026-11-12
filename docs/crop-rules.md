# Crop rule files

Each crop FarmTwin covers has one file in `knowledge/crops/<crop>.yaml`. The engine in `apps/api/app/engines/rules.py` reads them at startup; nothing about a crop's calendar or risks is hardcoded in Python (ADR-019). `_common.yaml` holds rules that apply to every crop and run after the crop's own.

## Shape

```yaml
crop: maize                 # key used by plantings.crop_type
name: Maize
sources: [iita_maize_lifecycle_overview]   # corpus source_ids the file draws on

stages:                     # contiguous day ranges after planting, [from_day, to_day)
  - {id: vegetative, from_day: 21, to_day: 60, description: "Rapid leaf and stalk growth."}

risks:
  - id: heavy_rainfall_fungal_risk
    severity: high          # low | medium | high
    urgency: this_week      # immediate | this_week | monitor
    stages: [vegetative]    # omit to apply at every stage
    when: <condition>
    reason: Plain sentence shown to the user and given to the model.
    fact: Optional sentence added to the evidence, with {today} available.
    source: cimmyt_maize_disease_overview   # must be a source_id in knowledge/corpus
    threshold_source: fao_weather_agriculture   # optional, see below
```

Stage outside every range: `pre_planting` before day 0, `past_maturity` after the last stage. The harvest window is the last 10% of the cycle.

## Conditions

| Condition | Holds when |
|---|---|
| `{observation: {type, min?, max?, within_days?}}` | at least one logged observation of that type is in range and no older than `within_days` |
| `{weather: {field, min?, max?, within_days?}}` | the latest weather snapshot's `rainfall_mm`, `humidity_pct`, `temp_max_c` or `temp_min_c` is in range (and recent enough, if `within_days` is set) |
| `{rule: <id>}` | an earlier risk in the same file fired |
| `{rain_recorded: {within_days}}` | any rain log or weather reading in the window, even 0 mm. Dry-spell rules start with it, so a farm with no rain data is never read as a dry farm |
| `{any: [...]}`, `{all: [...]}`, `{not: ...}` | combine the above |

Each reading that makes a condition hold becomes a supporting fact on the risk, so the app and the prompt can show exactly why it fired. A `not` condition has no reading to point at, so give that rule a `fact`.

## Rules for adding a crop

1. Every number comes from a document in `knowledge/corpus`, and every risk names that document's `source_id`. The test suite fails on an unknown source.
2. Keep conditions to comparisons over recent readings. Anything that needs real computation goes in Python with its own test.
3. Extension guides say what weather drives a risk ("damp conditions", "the dry season") but rarely give a number. Use the shared weather definitions already in the corpus (heavy rain is 50 mm or more; high humidity is 80% or more; a dry spell is no 10 mm rain in 10 days, from `fao_weather_agriculture`) and name that document in `threshold_source`. Don't invent a crop-specific number.
4. Stage boundaries come from day counts the document gives (weeding weeks, spray windows, days to maturity). Say in the file's header comment which variety the calendar follows and how the boundaries were derived. If the document gives no day count, keep the stage coarse rather than guess.
5. Add tests for each new rule in `apps/api/tests/test_rules.py`.
