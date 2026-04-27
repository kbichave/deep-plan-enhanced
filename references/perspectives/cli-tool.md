# CLI Tool Perspectives

domain: cli-tool

## Perspective 1: CLI UX Reviewer
Asks: Is this tool intuitive and predictable for users?
- Argument parsing consistency (flags, subcommands, positional args)
- Help text completeness and discoverability (--help at every level)
- Error message clarity (what went wrong, what to do next)
- Exit code conventions (0 success, 1 general error, 2 usage error)
- Shell completion support (bash, zsh, fish)
- Progress indicators for long-running operations
- Quiet and verbose modes (--quiet, --verbose, -v)
- Color output and TTY detection (disable color when piped)

## Perspective 2: Integration & Scripting Engineer
Asks: Can I use this tool in scripts and pipelines?
- stdin/stdout/stderr separation (data on stdout, logs on stderr)
- Pipe-friendliness and structured output options (--json, --csv)
- Machine-readable output formats for downstream parsing
- Signal handling (SIGINT for graceful cancel, SIGTERM for cleanup)
- Environment variable configuration alongside CLI flags
- Config file discovery (XDG, dotfiles, project-local)
- Idempotent operations (safe to re-run without side effects)
- Cross-platform compatibility (macOS, Linux, Windows)

## Perspective 3: Distribution & Packaging Reviewer
Asks: Can users install and maintain this tool easily?
- Installation methods (brew, pip, npm, cargo, binary releases)
- Dependency footprint and vendoring strategy
- Version reporting (--version with useful output)
- Update mechanism and changelog communication
- Binary size and startup time
- Offline operation support (no network calls for core functionality)
- Backward-compatible flag changes and deprecation warnings
- Package registry metadata (description, keywords, homepage)
