# Historical research boundary

The root-level V2 behavioural, biometric, Streamlit, MCP, and migration sources are retained for
history and comparison. They are excluded from the V3 `src/` package and wheel.

They are not a production security path. In particular, V3 does not use 14-dimensional scoring,
password habits, family lore, self-entered “OAuth” answers, YuNet/SFace, face histograms, family
secrets wrapping the master key, or a local-machine 730-day clock. V3 never asks for a password to
learn its “style.”

Use tag `prototype-v3-behavioral` for the audited prototype snapshot and tag `v2.0.0` for the final
V2 source. There is no automatic V2→V3 migration.
