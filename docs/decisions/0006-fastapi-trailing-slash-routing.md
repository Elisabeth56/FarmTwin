# ADR-006: FastAPI trailing-slash routing
Date: 2026-08-17
Status: Accepted
Context: FastAPI's default trailing-slash redirect on `POST /api/farms/` 
returns 307 and curl drops the body on redirect.
Decision: Route paths inside prefixed routers use `""` not `"/"`, so 
`POST /api/farms` resolves directly without redirect.
Consequences: All future routers follow this convention.
