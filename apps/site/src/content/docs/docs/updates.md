---
title: Updates and your data
description: How updates work and where your farm data lives.
---

When you're online, FarmTwin checks for updates and asks before installing one. Updates never touch your farm data or re-download the model.

Your farm data is one file. Copy it to back it up:

| System | File |
|---|---|
| Windows | `%LOCALAPPDATA%\FarmTwin\farmtwin.db` |
| Mac | `~/Library/Application Support/FarmTwin/farmtwin.db` |
| Linux | `~/.local/share/FarmTwin/farmtwin.db` |

The AI model sits in the `models` folder next to it.
