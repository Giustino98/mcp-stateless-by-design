# Coding Rules

- Write minimal, readable, fully typed Python. Apply DRY, KISS, and YAGNI.
- Parse boundaries into total types. If absence violates the contract, fail
  immediately instead of propagating `None`.
- Use dependency injection only for a real boundary. Prefer `typing.Protocol`
  over abstract base classes when a port is justified.
- Avoid `Any`, casts, type ignores, speculative abstractions, and global mutable
  state.
- Comments explain essential reasons or protocol constraints only.
- Verify installed MCP SDK APIs before using them.
- Use the latest stable Python through `uv`; expose commands through `Makefile`.
- Every change must pass Ruff, strict Pyright, and Pytest via `make check`.
