# Director’s Cut — Quick Start

Create assets and reference-driven video with your own ComfyUI.

## Downloads

| Platform | Download | Setup |
| --- | --- | --- |
| Windows x64 | [Windows EXE](https://github.com/leonardofrito/Directors-Cut/releases/download/v0.1.0-rc.5/DirectorsCut-0.1.0-rc.5-windows-x64.exe) | Open the file; Python is included. |
| macOS | [Source package](https://github.com/leonardofrito/Directors-Cut/releases/download/v0.1.0-rc.5/DirectorsCut-0.1.0-rc.5-source.zip) | Extract, then follow the source instructions below. |
| Linux | [Source package](https://github.com/leonardofrito/Directors-Cut/releases/download/v0.1.0-rc.5/DirectorsCut-0.1.0-rc.5-source.zip) | Extract, then follow the source instructions below. |

[All release files and notes](https://github.com/leonardofrito/Directors-Cut/releases/tag/v0.1.0-rc.5)

Native macOS and Linux packages are not published yet. Their links above download source code, not an EXE or a ready-made app. The Windows build is currently unsigned.

Windows may show an unknown-publisher or SmartScreen warning because this release is not digitally signed yet.

## Before you start

Install and start a compatible ComfyUI. Its required workflow nodes and model files are separate from Director’s Cut. Model downloads are available in the app; missing supported custom nodes can be installed from Connection → Workflow nodes. Restart ComfyUI after installation.

## Windows EXE

1. Download the EXE above and open it.
2. Connect Director’s Cut to your ComfyUI address and select its data/models folder.
3. Choose compatible models and download any missing catalog files.

The app opens in your browser. No Python installation or source checkout is needed for this EXE.

## macOS, Linux or source development

Install Python 3.12 or [uv](https://docs.astral.sh/uv/), then extract the source package.

On macOS and Linux:

```sh
sh setup.sh
sh start.sh
```

On Windows, run `setup.bat`, then `Start Director's Cut.bat`.

Open `http://127.0.0.1:7860` and configure the ComfyUI connection. See the [connection guide](https://github.com/leonardofrito/Directors-Cut/blob/main/docs/comfy-connection.md) for custom paths, ports and remote engines.

## Your projects

The packaged app keeps its data outside the executable:

| System | Default data folder |
| --- | --- |
| Windows | `%LOCALAPPDATA%/DirectorsCut` |
| macOS | `~/Library/Application Support/DirectorsCut` |
| Linux | `~/.local/share/directors-cut`, or `$XDG_DATA_HOME/directors-cut` |

Moving or replacing the executable does not move your projects. Back up the data folder before replacing a build. Source launches use their project directory unless a data path is supplied.

Use **Quit app** to stop Director’s Cut. Closing its browser tab leaves the local server running.

## Optional features

- Uploaded motion/audio references and soundtrack replacement require FFmpeg, found through PATH, `OPENFRAME_FFMPEG` or a detected ComfyUI environment.
- [MCP setup](https://github.com/leonardofrito/Directors-Cut/blob/main/docs/mcp.md) is separate from the EXE and needs the source package plus `requirements-mcp.txt`. End-to-end host testing is still pending.
- GGUF files require compatible ComfyUI loaders. Omni REF variants are labelled unofficial.

[Model downloads](https://github.com/leonardofrito/Directors-Cut/blob/main/docs/model-downloads.md) · [License](https://github.com/leonardofrito/Directors-Cut/blob/main/LICENSE)
