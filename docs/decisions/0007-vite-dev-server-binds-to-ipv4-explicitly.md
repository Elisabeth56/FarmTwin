# ADR-007: Vite dev server binds to IPv4 explicitly
Date: 2026-08-17
Status: Accepted
Context: Vite 9 defaults to IPv6-only loopback, causing 127.0.0.1 to refuse.
Decision: Set `server.host: '127.0.0.1'` in vite.config.ts.
Consequences: setup.sh instructions and README can use either 127.0.0.1 
or localhost consistently.
