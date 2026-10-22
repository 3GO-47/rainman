"""v37 — Markets v2 deleted; METAPROP paired with META (META | METAPROP switch on F2 Matchups). Applied in place on 2026-10-21;
kept as a record. Rerunnable guard only."""
import io, sys
s = io.open('scripts/dashboard_template.html', encoding='utf-8').read()
print('already applied' if "meta:['metaprop','META','METAPROP','META']" in s else 'NOT applied — see session_log n91')
