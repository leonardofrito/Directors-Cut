# Director’s Cut

**0.1.0-rc.2 — portable release candidate.** Windows packaging includes Python and
opens the app in your browser. Start ComfyUI, launch the EXE, then select its
installation and models in Settings. See [quick start](packaging/QUICKSTART.md).
Native Windows/macOS/Linux build jobs are in `.github/workflows/release-build.yml`;
`python tools/build_release.py` builds on the current OS. Public release uploads,
code signing and the second-PC test are separate steps, not completed by creating
the files. No personal projects or model weights are shipped.

A local asset and video studio powered by **Qwen-Image 2.1**, **MiniMax H3**, **ComfyUI**, and the official **Comfy SDK**. Create characters, props and locations, then reference them in video scenes. No node editor, paid service, or API key required.

The interface uses black glass surfaces, lime actions and a left-controls/right-output layout inspired by [Comfy’s hosted Cinematic Studio](https://comfy.org/hub/apps/cinematic-studio/). Director’s Cut is an independent project. Attribution is in `THIRD_PARTY_NOTICES.md`; product direction is in `docs/design-reference.md`.

## Download

[Download the Windows EXE](https://github.com/leonardofrito/Directors-Cut/releases/download/v0.1.0-rc.2/DirectorsCut-0.1.0-rc.2-windows-x64.exe) · [Release notes and source](https://github.com/leonardofrito/Directors-Cut/releases/tag/v0.1.0-rc.2)

Open the EXE, connect your own ComfyUI, choose model variants and use Download for missing files. No Python setup is needed for the Windows EXE. GGUF and prompt-enhancer downloads are available in Engine settings; optional formats still need compatible ComfyUI nodes.

## Run on Windows

1. Have Python 3.12 (or [uv](https://docs.astral.sh/uv/)) and a running, compatible ComfyUI install.
2. Run `setup.bat`. Dependencies install in this project's `.venv`; ComfyUI's Python and custom nodes are not modified.
3. Start your existing ComfyUI on `http://127.0.0.1:8188`.
4. Run **Start Director's Cut.bat** and open **http://127.0.0.1:7860**.
5. Choose **New project**, name it, describe a shot, and click **Add to queue**.

The app reuses a reachable existing official SDK proxy or starts its own loopback proxy on a free port for the selected ComfyUI. Closing the app stops only its own proxy; it does not stop ComfyUI or an external proxy.

`Start Director's Cut.bat` listens on `0.0.0.0:7860` so another computer on your LAN or Tailscale can open `http://<studio-PC-IP>:7860`. Restart an existing app instance to apply this setting. ComfyUI and the SDK proxy are still contacted locally by the studio server. Windows Firewall must allow inbound TCP 7860 on the intended network; the app does not change firewall rules or configure router forwarding. Network access uses IP addresses, keeps same-origin write checks, and has no login, so use a trusted private network. For local-only launch, use `.venv\Scripts\python.exe run.py --listen 127.0.0.1 --port 7860`.

## Linux / macOS and existing ComfyUI installs

Run `sh setup.sh`, start your compatible ComfyUI, then `sh start.sh` (Python 3.12;
`uv` is used when available). This does not change ComfyUI’s Python or drivers.

In **Engine settings → Connection**, detect/select a Portable, Desktop or manual
installation, or enter its address, port and data/models folder. Custom ports and
remote engines are supported; remote model downloads require a mounted shared
models folder. `python run.py --comfy-url http://127.0.0.1:9000 --comfy-root "/path/to/ComfyUI"`
is also supported. Settings persist locally.

Windows is the physical test environment. Linux/macOS discovery fixtures and a
three-OS CPU CI workflow are provided; that does not certify all model kernels or
GPUs. Read [connection setup and verification limits](docs/comfy-connection.md).

## Installed workflow requirements

The default API graph was flattened from Leonardo's existing `Qwen2.1.json` subgraph, preserving its model and sampler choices:

| ComfyUI model folder | File |
| --- | --- |
| `diffusion_models` | `qwen_image_2.1_int8_convrot.safetensors` |
| `text_encoders` | `qwen3vl_8b_w4a8.safetensors` |
| `vae` | `qwen_image_2.1_vae_bf16.safetensors` |

Required nodes: `UNETLoader`, `CLIPLoader`, `VAELoader`, `TextEncodeQwenImage21`, `EmptyLatentImage`, `KSampler`, `VAEDecode`, and `SaveImage`. The tested ComfyUI version is **0.37.1**. The startup status checks live node and model availability. Model weights are not included; install them under their respective licenses. Source model links: [Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1).

The app uses a regular `SaveImage` output in place of `SaveImageAdvanced`. It sets a new output prefix, prompt, dimensions, seed, and step count per take. It never edits the original workflow. To import that specific saved subgraph again:

```powershell
.venv\Scripts\python.exe tools\import_workflow.py "C:\path\to\Qwen2.1.json"
```

That importer supports the supplied single Qwen subgraph shape; it is not a general ComfyUI workflow converter. For other setups, adapt `workflows/qwen21_api.json` and the mapping in `openframe/provider.py`.

## Workspace

Optional assistant control: see [MCP setup and prompt guides](docs/mcp.md).
It exposes projects, assets and video generation to stdio/Streamable HTTP MCP
hosts while keeping generation on the local studio's official Comfy SDK path.
Install `requirements-mcp.txt` separately; no external LLM API key is required.
The standalone local app does not depend on this bridge.

For Leonardo's 12 GB GPU investigation, see
[the measured VRAM findings](docs/vram-diagnosis-2026-10-21.md).

The studio uses **Qwen-Image 2.1 only**, with generation and reference editing selected automatically. Historical workflows and takes remain on disk. Engine settings are available from the connected-engine button in the upper-right corner.

**Model setup** lists detected model files, expected ComfyUI folders, missing nodes/weights, and model-page links taken from the supplied workflows. Missing verified catalog files have an explicit Download button with resume and SHA-256 validation, saved to the configured ComfyUI models folder. Selecting a model alone never downloads it. No model hosting, conversion or custom-node installation is performed. See [model downloads](docs/model-downloads.md). Choose **Standard** or **GGUF**, installed weight variants, and a compatible prompt enhancer in Engine settings. These choices are remembered in this browser. Standard selects native safetensors files (including compatible BF16/INT8/FP8/W4A8 variants); GGUF substitutes the diffusion loader in the submitted graph. Text encoders are selected independently and get a GGUF loader only when a GGUF encoder is chosen. No switch nodes are added to the original workflows and inactive loaders are not submitted.

The file chooser filters installed filenames to the expected model family. Filename matching does not certify quantization or architecture compatibility: some models/variants are not supported by a given GGUF node version. No compatible image GGUF weights were installed for the current catalog during verification, so the GGUF branch has structural tests but no real generation test. See [model setup](docs/model-setup.md).

Original workflow copies and their hashes are recorded under `workflows/directors_cut/` and `workflows/catalog.json`. Executable copies flatten subgraphs, resolve constant switches and use a standard PNG output. The optional local Prompt enhancer requires explicit selection of an installed model. The dedicated Qwen PE has download links for INT8/W4A8. General FLUX 3 encoder reuse is disabled after repeated empty/refused captions. It expands the scene through native ComfyUI text generation, then appends exact art direction before image conditioning. With it off, prompts route directly to the image encoder. The Qwen text-to-image entry retains the already-tested core graph; the supplied source is preserved alongside it. See [image direction and enhancer setup](docs/image-direction.md).

- Create and reopen projects; add and revisit individual shots.
- Open the right-side project library to import character, prop and location images, save a completed take as an asset, or copy assets from another project. Type @ for mention suggestions and attach up to ten references.
- The two workspaces are Assets and Video. Assets offers Qwen image generation and separate character, location and prop presets. Custom text remains first in every menu. See [asset library and reference workflows](docs/asset-library.md) and [video generation](docs/video-workspace.md).
- Compact controls above Add to queue share the video tab's visual aspect-ratio picker and styled megapixel slider. Assets offers 0.5–4 MP in 0.1 MP increments, default 2 MP, and one to four queued takes. Project and asset selectors in the header include create-new actions.
- The frame fills the center vertically. Click it for a zoomable viewer; open the bottom asset label to read and copy the actual prompt. Save to Library is the primary action; PNG download is in the image actions menu.
- For backend prompt editing, see [editing prompts](docs/editing-prompts.md).
- Camera has independent lens type, sensor/film format and focal length slider (8–500mm), plus aperture from f/0.7 to f/32. Light has style, color/warmth and custom written direction. Choose among 25 framing options, 22 looks, 27 film/processing looks and 20 grades, both with swatches and eight aspect ratios. These instructions become part of the saved generation prompt.
- Choose an installed enhancer model explicitly in Engine settings; the composer contains only its on/off toggle. The dedicated Qwen 2.1 PE is listed as missing until installed. Qwen3-VL 4B remains labeled as a general encoder and is disabled for enhancement after repeated failures in this integration. The original scene stays intact; completed takes show their actual expanded prompt.
- Add 1–16 takes per click, including more takes of the same shot while generation is running. Each item keeps its prompt, model and settings. Fixed seeds advance by one within a batch; random seeds differ per take.
- The global generation queue shows running work and waiting positions across projects. Remove waiting items, keep editing, or open the corresponding shot. Jobs run one at a time; queued work resumes in order after restart.
- The right-side take strip shows four square previews on desktop, with continuous scrolling and scroll snapping. Adding queued takes preserves the current scroll position. A subtle generation gradient stays at the strip bottom while pending placeholders are outside the view and disappears when they become visible. Preview arrows browse ready images and newly completed takes are selected automatically. Repeated submission retries do not duplicate a batch.
- Each take retains its original settings, full prompt, and executed API graph.
- Review any take, reuse its settings, edit the image, or save it to the project library without losing previous generations.
- Preset menus use local JPEG previews, capped at 256×256 and quality 75. Files remain separate for lazy loading and individual updates; original PNG masters remain in the review catalog. See `web/assets/previews/README.md`.
- Download images as PNG and completed videos as MP4.
- Active jobs with a recorded SDK job ID resume monitoring after restart. An interrupted, ambiguous submission is flagged for manual inspection instead of silently submitting twice.

Projects live in `projects/<name>_<id>/project.json`, with generations under `shots/shot_001/`. Existing project files remain compatible. ComfyUI also retains its original outputs. Generated files and runtime data are Git-ignored.

Set environment variables before starting to configure paths and ports:

```powershell
$env:OPENFRAME_PROJECTS = 'D:\Director’s Cut\projects'
$env:OPENFRAME_COMFY_URL = 'http://127.0.0.1:8188'
$env:OPENFRAME_PORT = '7860'
.venv\Scripts\python.exe run.py
```

Changing `OPENFRAME_PROJECTS` selects a different project library; existing files stay where they are. Output-folder selection is currently configured here, rather than through a folder picker. The legacy OPENFRAME environment-variable names remain supported after the rename. `COMFY_BASE_URL` optionally points at an already-running local Comfy API v2 proxy (default `http://127.0.0.1:8189`). The server defaults to loopback; the Director’s Cut launcher enables LAN/Tailscale access. Both modes check write origins.

## Developer Platform integration and competition

The runtime path is **Director’s Cut → official `comfy-sdk` → official `comfy-api-proxy` → existing local ComfyUI**. This is the self-hosted SDK route documented by Comfy, rather than treating legacy `/prompt` calls alone as Developer Platform integration:

- [Official SDK guide](https://docs.comfy.org/development/api-development/sdks)
- [Official self-hosted API proxy guide](https://docs.comfy.org/development/comfyui-server/api-proxy)
- [Competition requirements](https://comfy.org/open-source-higgsfield)

The competition explicitly accepts Comfy SDK integration; the SDK guide explicitly supports self-hosted ComfyUI. This implementation follows that documented route. Final category eligibility is determined by the organizers. Inference uses local weights only, with no partner nodes or external model API calls. Dependency installation requires Internet access.

Asset and video generation run locally through the official SDK. Public hosting, GitHub publication, social posting and final competition submission are still pending. No clean-machine hardware certification or public submission has been performed yet.

## Development

Small aiohttp backend, plain HTML/CSS/JavaScript interface, modular SDK provider, and JSON project storage. No frontend build is needed.

```powershell
.venv\Scripts\python.exe -m unittest tests.test_core -q
node --check web\app.js
```

The default checks cover project persistence and path containment. Run one directly relevant check only when a concrete bug or risk warrants it. Legacy storyboard checks and duplicate video recipe checks were removed. The full suite is optional, not a requirement for every edit. These checks run locally without AI calls or GPU generation. Real local generation and UI/export checks are recorded in `docs/environment.md`.
