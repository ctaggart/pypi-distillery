# Show the current version
version:
    uvx --with hatch-vcs hatchling version

# Build wheels for a specific distillery version (e.g., just build 1.8.11)
build version:
    uv run scripts/build_wheels.py {{version}}

# Run all checks
check: pyright test

# Type check
pyright:
    uvx pyright

# Check for new upstream release
check-release:
    uv run scripts/check_release.py

# Run tests
test:
    uv run --with pytest pytest tests/ -v

# Clean build artifacts
clean:
    rm -rf dist/
