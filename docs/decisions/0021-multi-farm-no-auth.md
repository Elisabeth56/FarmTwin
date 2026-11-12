# ADR-021: Many farms per install, no authentication

- Status: Accepted
- Date: 2026-11-11

## Context
The primary user is an extension officer who supports many farmers. v1 assumed one farm. The app is offline and installed on the officer's own laptop.

## Options
- **Single farm.** Matches v1; does not match the officer's work.
- **Many farms, no auth.** The OS user account is the boundary.
- **Many farms with a local PIN.** Adds friction and false security; the database file is readable by anyone with the laptop anyway.

## Decision
Many farms with a farm list as the home screen. No accounts and no PIN.

## Consequences
- Every query is scoped by `farm_id`.
- If shared devices become a requirement, revisit with OS-level or encrypted-database options rather than an app PIN.
