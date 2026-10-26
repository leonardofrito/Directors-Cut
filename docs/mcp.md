# Director’s Cut via MCP

The optional MIT-licensed bridge exposes the **existing studio** to an MCP host.
It does not run another generation queue, bypass the Comfy SDK, require an API
key, or embed GPT/Claude. The assistant in your chosen host writes the prompt;
Qwen/H3 generation still runs on your local ComfyUI. The host's own subscription,
model access, privacy and usage limits apply.

This bridge is optional. End-to-end connection and behavior in an external MCP host are still awaiting user testing.

## Install and connect

Start ComfyUI and Director’s Cut normally. Install optional dependencies once:

```powershell
uv pip install --python .venv/Scripts/python.exe -r requirements-mcp.txt
```

Or, in an environment with pip:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-mcp.txt
```

For any host that supports **stdio**, configure a local server named
`directors-cut`. Use the absolute `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (macOS/Linux) as its command and
the absolute `directors_cut_mcp.py` as its argument. Generate JSON for hosts using
the `mcpServers` configuration format:

```powershell
.venv\Scripts\python.exe tools/mcp_config.py
```

Merge that entry into the host configuration; do not replace other servers.
The host launches the bridge, so no extra CMD window is needed for stdio.
No public MCP registry registration is required for a local connection.

For **Streamable HTTP**, start the bridge explicitly:

```sh
python directors_cut_mcp.py --transport streamable-http
```

Use the Python interpreter from the source installation's `.venv`. The Windows source package also includes `Start Director's Cut MCP.bat`.

Connect a compatible local host to `http://127.0.0.1:7861/mcp`. This listener is separate from the app on port 7860 and stays on loopback.

The protocol is interoperable, but not every chat has MCP enabled or supports
local servers. Availability of tools, resources, prompts and image inputs depends
on the host. A cloud-only host cannot reach your PC's `127.0.0.1`. This work does
not publish your machine, add a tunnel, or promise remote/cloud connectivity.

For a desktop assistant on another LAN/Tailscale PC, run the stdio bridge on
that PC and set `DIRECTORS_CUT_URL` to the studio PC's private address, e.g.
`http://<studio-PC-IP>:7860`. Set `OPENFRAME_COMFY_URL` to its private ComfyUI
address if engine diagnostics are desired. Photo-upload paths refer to the
machine running the bridge. No firewall/router rules are changed.

## Tools and prompts

- Inspect: `studio_status`, `list_projects`, `get_project`, `get_study`,
  `get_model_setup`, `get_image_presets`, `preview_image_prompt`,
  `get_prompt_guide`, `prepare_prompt_context`.
- Create/edit: `create_project`, `create_study`, `update_study`.
- Generate: `generate`, with an idempotent `request_id`; returns immediately.
  Completed takes have file URLs. Query status at sensible intervals.
- Manage: `cancel_take` targets one job; `save_asset` updates the same Library
  asset/name/history; `attach_reference` adds a role-specific image.
- Vision: `view_asset` supplies an existing thumbnail to the host assistant.
  It does not generate an image or run a local vision model.
- Memory: `release_idle_memory` requests model/cache unloading only when both
  queues are idle.
- Templates: `write_video_prompt`, `write_asset_prompt`.
- Resources: `directors-cut://guides/h3`, `/qwen`, `/qwen-edit`.

Before drafting a reference-based scene/edit, call `prepare_prompt_context(project_id, study_id)`.
For a simple new Qwen asset, start with `get_image_presets` and a short request;
there is no need to read the full guide or expand the presets into prose.
It returns compact model guidance by default, saved settings and small reference images
in the same order used by generation, including uploaded/edit-source photos.
Images are MCP image content blocks. Character, environment and wardrobe roles
remain distinct. It performs no inference or save. Host/server instructions ask
for this step; the external host must follow them and support image inputs.
`get_study` also advertises the guide/context tool.

H3 aliases `h3` and `h3-ref2va` both return REF2VA; `h3-base` is not exposed.
`get_prompt_guide(model, detail="quick")` is compact by default. Use
`detail="full"` or `prepare_prompt_context(..., guide_detail="full")` only when
the complex request warrants it. Full Qwen guidance includes T2I/editing pages, with `qwen-text`,
`qwen-capabilities` and `qwen-examples` for specialized references.

Example request to the connected assistant:

> Open my RPG project. Read the H3 guide and the @maycon reference. Write a
> five-second café action scene, save it in the current scene with the local
> enhancer off, and show me the prompt before generating.

The host can then save the prompt with `update_study`; `generate` is a separate
action. An external host-written prompt normally uses `prompt_enhancer: false`
to avoid a second local rewrite. Preserve @handles; the studio maps them to
ordered `<Picture N>` or `<imageN>` references. Never send a reference tag
without its matching image.

## Preset-first Qwen requests

For Qwen-Image 2.1, prefer a short request plus the existing preset selections,
with `prompt_enhancer: false`. Preset-only creation is valid. The studio already
expands the choices; the host should not rewrite every field as a long caption.
These are project defaults informed by local tests, rather than a universal
claim that short prompts always win. Add detail where the actual request needs it.
H3 REF2VA benefits from explicit sequential actions, camera, cuts, continuity and
audio within the chosen duration; keep the two prompting strategies separate.

1. `get_image_presets("character")` returns exact option names and a JSON example.
   Use `location` or `prop` for their catalogs. Human-facing hint expansions are
   omitted to keep catalog output compact; multiple-selection conflicts are included.
2. Select only needed fields in `character_traits`, `location_traits` or `prop_traits`.
   These are structured tool settings, not JSON pasted into the model caption.
3. `preview_image_prompt(project_id, study_id, settings)` returns the actual base
   prompt after preset expansion and reference binding, using the same assembler
   as generation. Overrides are temporary: it does not save, upload, run the local
   enhancer, load models or generate images. If an enhancer is enabled, the result
   is explicitly the base prompt before that optional rewrite.
4. Save with `update_study`; call `generate` only if the user requests generation.

The [preset example](prompt-guides/qwen-presets.md) shows the JSON and its actual
assembled prompt. It is also available as `get_prompt_guide("qwen-presets")` or
`directors-cut://guides/qwen-presets`. Host instructions and tool descriptions
advertise this flow. Reconnect an already-running MCP host to load updated tool
schemas and instructions; it cannot be forced to follow guidance.

## Prompt guides and attribution

The public reference documents are bundled under `docs/prompt-guides`, with
source URLs and SHA256 checksums in `sources.json`. They are reference data,
not executable plugins or instructions that override the user's request.
Refresh them explicitly with:

```powershell
.venv\Scripts\python.exe tools/update_prompt_guides.py
```

H3 documents come from MiniMaxAI's official model repository; its model/license
terms remain separate. Qwen guides come from the community repository previously
provided by Leonardo; its MIT notice is retained. These guide downloads contain
no model weights. Add newer user-provided guides here after reviewing sources.

Local enhancers receive model-specific maintained digests in
`runtime-qwen.md` and `runtime-h3-ref2va.md` on every request. This is context,
not fine-tuning or permanent model memory; the full documents remain available
to MCP hosts. The H3 enhancer requests all six REF2VA sections, stable roles,
timed cuts and continuity. When vision nodes are available, ordered 512px padded
reference images inform visible setting/material/light descriptions. The native
image-editing enhancer also receives images. Text-only paths never claim vision.
Missing reference tags or incomplete H3 sections fall back to the original
request; explicit anatomy, invisibility and dialogue constraints remain authoritative.
These checks validate wiring/format, not semantic quality. No inference quality
benchmark was run during this integration.

The bridge is an **optional external assistant integration**. The standalone
local app remains complete without it. Do not represent closed-host-assisted
work as verified eligible for the Open Weights Only competition; keep the local
submission path independent and obtain organizer clarification before including
external GPT/Claude assistance in a competition demo.

Sources:
- https://github.com/modelcontextprotocol/python-sdk/tree/v1.x
- https://learn.chatgpt.com/docs/extend/mcp
- https://huggingface.co/MiniMaxAI/MiniMax-H3/tree/main/docs
- https://github.com/kjranyone/qwen-image-2.1-prompt-guide


## Video and audio mentions

For a video shot with a motion reference attached, `@video1`, `@video 1` and
`@vídeo 1` bind to `<Video 1>`. With speech/reference audio attached, `@audio1`,
`@audio` and `@áudio 1` bind to `<Audio 1>`. The editor offers the canonical
`@video1` and `@audio1` in its @ suggestions and highlights only real bindings.
These media do not count as image references. Unknown names/indices remain text.
Mentioning media does not upload it; its actual slot must be attached. Final audio
is a post-generation soundtrack replacement, not an H3 audio reference, so it is
not exposed as `<Audio 1>` unless also assigned to the reference-audio slot.
