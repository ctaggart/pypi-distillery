# distillery-bin

[Distillery](https://github.com/ekristen/distillery) CLI repackaged as Python wheels for easy installation via tools like `uv` and `pip`.

Distillery is a tool for installing binaries from GitHub Releases.

## Install

```sh
pip install distillery-bin
dist --version
```

Or with `uv`:

```sh
uv tool install distillery-bin
dist --version
```

## Supported Platforms

| Platform | Wheel tag |
|----------|-----------|
| Linux x64 | `manylinux_2_17_x86_64` |
| Linux ARM64 | `manylinux_2_17_aarch64` |
| Linux x64 (musl) | `musllinux_1_1_x86_64` |
| Linux ARM64 (musl) | `musllinux_1_1_aarch64` |
| macOS x64 | `macosx_10_9_x86_64` |
| macOS ARM64 | `macosx_11_0_arm64` |
| Windows x64 | `win_amd64` |
| Windows ARM64 | `win_arm64` |

## How It Works

This package downloads the official distillery release archives from
[ekristen/distillery](https://github.com/ekristen/distillery/releases)
and repackages each `.tar.gz` / `.zip` as a platform-specific Python wheel.

A thin Python entry point (`console_scripts`) delegates to the native binary,
so `dist` is available on `PATH` after install.

Both `pip install distillery-bin` and `uv tool install distillery-bin` are
supported — the console_scripts entry point works with both package managers.

## Development

Python, uv, & just are needed.

```bash
uv tool install rust-just
```

## License

This package redistributes distillery under its
[MIT](https://github.com/ekristen/distillery/blob/main/LICENSE) license.
