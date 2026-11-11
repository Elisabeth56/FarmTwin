# v1 benchmark (archive)

The hackathon's model benchmark and grader. They import modules that v2 replaced (`app.llm.client`, `app.engines.context_assembler`), so run them from the v1 code:

```bash
git checkout fc251f9   # main before the v2 work
```

Results are in `bench_results/` and `docs/v1/benchmarks.md`. The v2 re-benchmark (#15) uses `evals/run.py` and the current code.
