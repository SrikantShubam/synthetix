# SDLC Governor

Local SDLC gatekeeper for Codex and Claude Code.

Gryph records agent actions. This tool consumes that evidence, generates context,
stores plan versions, and runs Promptfoo gates.

Common commands:

```powershell
python tools/sdlc/sdlc.py init
python tools/sdlc/sdlc.py status
python tools/sdlc/sdlc.py ingest-gryph --since 1d
python tools/sdlc/sdlc.py context
python tools/sdlc/sdlc.py eval plan
python tools/sdlc/sdlc.py eval readiness
python tools/sdlc/sdlc.py advance implementation
```

