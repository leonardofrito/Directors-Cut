# ComfyUI connection and portability

Open **Engine settings → Connection**. Detect finds known Desktop data paths,
Portable/manual folders and local running ComfyUI processes, including custom
`--port` values. It probes `/system_stats` before listing a server as online.
Detection never installs ComfyUI, changes drivers or starts a generation.

Select a detected folder/address, or enter them manually, then **Test** and
**Save connection**. A folder must contain `models/`; a Portable parent with
`ComfyUI/models/` is also accepted. Choose Desktop's **data/installation folder**,
not `ComfyUI.exe`, an app bundle or an AppImage. Desktop's optional primary shared
model directory is read from `installations.json`. A separate models directory
can be selected for custom installations. These are server-side filesystem paths,
even if the browser is on a phone or a different PC.

Settings persist in `.runtime/engine.json`. Legacy environment variables remain
supported: `OPENFRAME_COMFY_URL`, `OPENFRAME_COMFY_ROOT`, `OPENFRAME_MODELS_DIR`,
`COMFY_BASE_URL`. Explicit environment values override saved settings at startup.
CLI overrides:

```sh
python run.py --comfy-url http://127.0.0.1:9000 --comfy-root "/path/to/ComfyUI"
python run.py --models-dir "/mounted/shared/models"
```

The studio retains the official AsyncComfy path. For a different ComfyUI address,
it starts its own loopback-only official API proxy on a free port. Advanced users
can choose an already running v2 proxy. The studio only terminates proxies it
started itself; existing ComfyUI and external proxy processes are never killed.
Changing connections is blocked while generations or model downloads are active.
MCP status/memory operations follow the studio's current connection.

Fresh installations use the app-managed SDK proxy by default. The native ComfyUI
address is not an SDK v2 proxy address; keep **Use an existing SDK proxy** off
unless you intentionally run a separate official v2 proxy.

Saving first persists the validated model/data folders independently, then attempts
the generation connection. A proxy failure is reported as **Folders saved.
Generation connection is not ready**; local model downloads can still use the saved
folder while ComfyUI is offline or its proxy is being repaired. Active queues and
downloads still block destination changes, and remote folders still require an
explicit shared-filesystem confirmation. Quoted folder paths with spaces are accepted.

## Downloads

Model selection does not download. A missing catalog entry gets an explicit
Download button, writing to the selected `models/{diffusion_models,text_encoders,
vae,loras}` directory with resume and SHA-256 verification. Existing files are
preserved. A remote engine needs an explicitly confirmed mounted/shared models
folder; otherwise downloads are disabled to avoid saving weights on the wrong PC.
This does not upload a multi-gigabyte model over the generation API. Folder write
permissions and sufficient disk space are required. Atomic publication uses hard
links (standard NTFS/APFS/ext4); filesystems without hard-link support need a
compatible models destination. See [model downloads](model-downloads.md).

## OS and GPU scope

The client/proxy/settings/download code is portable Python. Windows has
`setup.bat` and the existing launcher; Linux/macOS have `sh setup.sh` and
`sh start.sh`. ComfyUI stays in its own environment and supplies GPU support.
Portable is a Windows distribution; Desktop/manual installs are detected using
their platform-specific paths. Custom addresses/paths remain available when
automatic detection cannot see a process or a sandboxed Desktop installation.

ComfyUI supplies hardware and backend support. Quantized loaders and optional custom nodes need compatible kernels and drivers. Install versions suited to your ComfyUI backend; Director’s Cut does not replace PyTorch or drivers, or convert unsupported formats silently.

### Verification, 2026-10-24

- On this Windows PC: actual Portable discovery, current live ComfyUI/SDK proxy
  connection, Settings save interaction, and startup/shutdown of a separate
  official managed proxy while preserving the external proxy. No new GPU
  generation for verification.
- Twelve focused CPU checks: OS path fixtures for legacy/current Desktop on
  Windows/Linux/macOS, Portable normalization, nonstandard ports, backend reporting,
  remote shared-folder rules, managed proxy arguments/lifecycle, busy connection
  guard, actual tiny HTTP resume/hash/download to the selected folder, and the
  existing no-overwrite/hash/path checks.
- `.github/workflows/portable-connection.yml` defines Windows/Linux/macOS CI for
  these checks. The initial published runs did not complete successfully; native macOS/Linux packages are not currently available.
- Linux/macOS path tests run as fixtures on Windows. Physical Linux/Mac/AMD/Intel
  machines and large model downloads on those machines are **not tested here**.
  Do not label this as universal hardware certification.

Sources: [ComfyUI system requirements](https://docs.comfy.org/installation/system_requirements),
[manual installation](https://docs.comfy.org/installation/manual_install),
[Comfy Desktop](https://github.com/Comfy-Org/Comfy-Desktop),
[official SDK](https://docs.comfy.org/development/api-development/sdks),
[self-hosted proxy](https://docs.comfy.org/development/comfyui-server/api-proxy).
