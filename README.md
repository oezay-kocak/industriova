# Production Zero

Production Zero is an early Python/PySide6 game project mixing idle, tycoon,
factory-management, and deckbuilding systems.

The current foundation intentionally keeps gameplay small and focuses on:

- separating static card definitions from owned card instances
- keeping UI, simulation, state, services, and persistence separate
- routing important state changes through commands
- keeping deterministic seeds explicit
- using local service implementations first, with interfaces ready for later
  server or platform-backed versions

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python -m production_zero.app
```

