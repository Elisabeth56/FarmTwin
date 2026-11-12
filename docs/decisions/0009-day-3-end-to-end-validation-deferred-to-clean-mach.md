# ADR-009: Day 3 end-to-end validation deferred to clean-machine test
Date: 2026-08-19
Status: Accepted
Context: Dev machine is Intel Mac 2014 with 8GB RAM. During Day 3 dev session,
Claude desktop app + VirtualStudio process consumed ~1GB and CPU cycles, degrading
llama.cpp inference from baseline 15-18 tok/s prompt eval to 1.4 tok/s.
After killing those, prompt eval recovered to 19.6 tok/s and generation to 6.8 tok/s.

Decision: Defer full /api/ask end-to-end validation to clean-boot session or Day 5
integration testing. Verified components independently: retrieval, deterministic
engines, prompt assembly, 503 handling, all endpoints still work.

Consequences:
- Day 4 frontend built against mocked /api/ask responses (standard practice)
- Real end-to-end test happens once during Day 5 integration
- Day 6 benchmark measurements taken during clean-boot state, not mid-dev-session
- REPORT.md notes hardware development context (dev machine same class as target)
