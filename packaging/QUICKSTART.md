# Director's Cut — 0.1.0 release candidate

A local studio for characters, props, locations and reference-driven video.
Uses Qwen-Image 2.1, MiniMax H3 REF2VA and the official Comfy SDK.

## Windows portable EXE

1. Start your existing ComfyUI. Current compatible ComfyUI and workflow nodes are required.
2. Double-click the Windows EXE. Python is included; no Python setup is needed.
3. Your browser opens **Engine settings → Connection** on first use.
4. Detect/select ComfyUI, check the address and **models folder**, then save.
5. In Images/Video settings, select compatible models, including optional GGUF and prompt enhancers. Missing verified catalog
   files have a highlighted **Download** button. Download the selected files; the
   app places them in ComfyUI's matching model folders, verifies them and resumes
   interrupted transfers. Existing models are reused.
6. Create a project and asset, then use @references in a video shot.

The EXE contains no model weights, ComfyUI install, GPU driver or personal project.
It does not modify your ComfyUI environment. Missing custom nodes must be installed
in ComfyUI; Settings reports them. Quantized kernels depend on your GPU/backend.
Omni REF variants are explicitly unofficial. Model licenses are separate.

**Quit:** Engine settings → Quit app. Finish/cancel generations and pause downloads
first. Closing the browser tab alone leaves the studio running. Double-clicking
the EXE again opens the existing studio instead of starting a duplicate server.

**Data:** Windows `%LOCALAPPDATA%\DirectorsCut`; macOS
`~/Library/Application Support/DirectorsCut`; Linux
`~/.local/share/directors-cut` (or `$XDG_DATA_HOME/directors-cut`). Projects remain
there when the EXE is moved or replaced. Open the folder from Settings. Logs are
in its `.runtime` subfolder. Back up the whole data folder before replacing builds.
An existing source library can be opened with `--data "/path/to/existing/studio"`.

The app listens on localhost by default. Advanced private-network use:
`DirectorsCut.exe --listen 0.0.0.0 --port 7860`. No firewall/router rules are changed.

## macOS / Linux

Native bundles must be built on their target OS. The source ZIP includes launch
scripts and a native GitHub Actions build matrix; it is not a pretested Mac/Linux
binary. From the extracted source: `sh setup.sh`, then
`.venv/bin/python app_entry.py`. Python/uv is required for source setup.
To build a standalone native bundle: install `requirements-build.txt`, then run
`python tools/build_release.py`. macOS produces an app bundle ZIP, Linux a single
executable. Download artifacts from the native build workflow when published.

## Media support and known limits

- FFmpeg is needed for uploaded motion/audio references and soundtrack replacement.
  The app uses PATH, `OPENFRAME_FFMPEG` or a detected ComfyUI environment's existing
  FFmpeg. No FFmpeg binary is redistributed in this candidate.
- The binary is unsigned. Signing/notarization and native Mac/Linux validation are pending.
- This is a test release, not certification for every GPU/model precision. No large
  weights or GPU inference were used merely to validate packaging.
- The optional MCP bridge is in the source ZIP (`docs/mcp.md`); the standalone
  executable does not bundle a separate host LLM or stdio MCP runtime.

App: MIT. Dependency/font/icon notices are bundled and available in Settings.
