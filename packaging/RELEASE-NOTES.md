# 0.1.0-rc.8.2 — Interface hotfix

- Thumbnail size control stays fixed in the lower-right corner across workspaces and cut views.
- Gallery rows use the available width, with a small size tolerance to avoid unnecessary empty space.
- Second Take keeps its own workspace when switching projects, without overwriting asset drafts.
- New swaps and cut regenerations respect the selected engine models and SelfLift setting.
- A stronger lime outline makes the selected Second Take result easier to identify.

This hotfix keeps the existing generation workflow. Relay experiments, first-frame editing tests and their media are not included. Character replacement remains experimental; multiple-person identity and clothing consistency are not guaranteed.

The Windows build is unsigned. Native macOS/Linux packages are not published; source instructions are available.

# 0.1.0-rc.8.1 — Hotfix

- Second Take RTX Upscale processes each source cut separately, then assembles one result with the completed video's audio. Other video workspaces retain their existing upscale path.
- Modular default swap prompt supports one to six references and explicitly preserves the original scene, lighting and camera. Automatic prompt expansion remains disabled. Custom directions are preserved.
- Regenerated cuts stay grouped under their original video, including queued/running versions. Initial generations expose individual cut progress and completed previews. Additional cut revisions can be queued without waiting for the current revision.
- Text-free continuous thumbnail scale control across all three workspaces, with saved per-workspace sizing.
- Case-insensitive @reference binding in Second Take.
- Windows remains unsigned. Native package checks and CPU fixtures do not certify RTX processing on physical hardware or character-swap fidelity.

# 0.1.0-rc.8

- Three canvas workspaces: Asset Creation, Director’s Cut and Second Take, with a shared floating video prompt, seed controls, glass materials and media player.
- Second Take imports a video, detects cuts and lets you assign replacement characters. Review individual cuts, generate new versions and join the chosen versions into a new result. Original takes remain available.
- Explicit character-swap prompts now pass directly to H3 after resolving @references. Automatic visual captioning and prompt expansion are disabled in Second Take, including cut regeneration. Source audio remains attached separately.
- Updated media review, quick reuse/download actions and take approval. Portrait batches scroll through all versions. Image-edit presets are accessible again.
- Unified selector heights and generation controls, fixed closing menus intercepting clicks, and shared playback controls in the trim dialog. Header actions read Edit Timeline, Preview Final Cut and Download.
- Includes the Bank of Ideas demo and existing MP4/DaVinci timeline export.
- Character replacement remains experimental: identities, clothing and lip sync can drift. Model terms remain separate from the MIT application license.
- Windows remains unsigned. macOS/Linux source instructions are included; native packages are not published. Package verification uses isolated data with no GPU generation or model downloads.

# 0.1.0-rc.7

- Bundled Bank of Ideas example with 14 approved shots and 12 references. Opening the demo preserves your previous edits; no generation starts automatically.
- Library shot ordering, sequence playback, and a non-destructive V1/V2/A1/A2 timeline with trims, split, independent audio offsets, undo/redo and autosave. Export MP4 or an OTIOZ media package for Resolve 18.5+.
- Silent looping camera-movement, framing, pacing and optical previews. Framing, Movement, Pacing and Lens display two cards per row. Aperture and focal length retain sliders with full-width looping previews above them.
- Updated optical examples from the V4 comparisons. Removed Video lighting, Camera Type, Sensor and Halation Vintage options; historical takes are preserved.
- Clear separation between MIT application code and upstream model terms, including local H3 territorial restrictions. Bundled upstream H3 license and model-terms links. These notices do not certify legal compliance or grant restricted-territory authorization.
- Windows package remains unsigned. Native macOS/Linux packages are not included. No new inference was run for package verification.

# 0.1.0-rc.6

- Select multiple assets or shots in the Library to download or delete them together. Deletion confirms once and refuses active generations; deleted assets and their studies retain the existing archive recovery behavior.
- Download individual images and MP4s directly to a chosen folder in supported browsers. Existing names receive numbered suffixes instead of being overwritten. Other browsers use their normal download settings; ZIP is not the default.
- Fixed click feedback moving corner buttons before a click could complete. Selection buttons stay anchored and show their selected state.
- Compact SelfLift control, fewer model-setup helper texts and source links grouped at the bottom. Omni REF automatically uses its VSA recipe without an additional toggle or label; normal H3 uses the original recipe.
- Windows package checks use an isolated fake engine with no GPU generation. The EXE remains unsigned. macOS/Linux source instructions remain available; no new native-platform claim is made.

# 0.1.0-rc.5

- Clearer settings typography with native system fonts, larger helper text and no text blur/shadow effects. The shared installed Qwen3.5 4B INT8 enhancer has a readable precision label.

- Optional SelfLift for H3 REF2VA: four lower-resolution sampling steps followed by four at the selected size. Off preserves the existing sampler recipe. H3 SelfLift remains experimental; quality, adherence and memory savings are not guaranteed.
- Opt-in automatic installation of missing, pinned KJNodes/GGUF/VSA/SelfLift node packs using the configured local ComfyUI Python. Existing node folders and numerical-stack versions are preserved. New nodes need a ComfyUI restart.
- Organized model selectors with Omni first and independent Standard/GGUF encoder controls; official H3 encoder NVFP4-AWQ is visible. Qwen encoder GGUF downloads include their vision companion. H3 encoder GGUF remains experimental.
- Shared Qwen3.5 4B enhancer settings for Assets and Video, with task-specific instructions. Saved take settings remain reusable.
- No MLX runtime or MLX weight downloads were added. Native ComfyUI on Apple Silicon uses PyTorch MPS; GPU-specific quantizations require supported kernels.
- Focused graph/setup checks and native package verification do not certify SelfLift output quality or physical Mac/Linux/AMD operation.

# 0.1.0-rc.4

- Added a visible Quit button beside Engine settings. It uses the existing shutdown action and keeps the active-generation/download guards. Closing a browser tab still does not terminate the server automatically.
- Removed the public .gitignore at the maintainer's request; local exclusion rules remain private. Previous commits contain only exclusion patterns, not environment values.
- Audited the six previously published commits with Gitleaks, both published source archives, and bundled file inventories of both Windows EXEs. No credentials or private configuration/project files were detected. See docs/publication-audit.md for scope and limitations.

# 0.1.0-rc.3

- Fresh installations now start with the app-managed official SDK proxy. A native ComfyUI server is no longer selected as an external SDK v2 endpoint by default.
- Connection settings save validated data/model folders before attempting the generation connection. A failed proxy connection no longer discards the selected download folder.
- Quoted Portable paths with spaces are accepted. Download destinations still require explicit shared-folder confirmation for remote engines.
- Clearer repair instructions distinguish the ComfyUI address from an optional external SDK proxy address.
- Windows build remains unsigned. No model recipes, weights or GPU generation changed.

# 0.1.0-rc.2

- Direct, resumable downloads for Qwen 2.1 GGUF and original H3 REF2VA GGUF.
- Dedicated Qwen image enhancers (INT8/W4A8) and the optional Qwen3.5 4B BF16 video enhancer now have Download buttons and original source links.
- Corrected malformed manual enhancer URLs and installed GGUF detection.
- Download size and SHA-256 metadata verified from original repositories on 2026-10-26; new entries pin their source revision.
- No new GPU inference or video-enhancer quality claim; the local generation recipes are unchanged.

# 0.1.0-rc.1

- Assets and Video workspaces, project library and @reference bindings.
- Qwen-Image 2.1 image generation/editing with current preset thumbnails.
- MiniMax H3 REF2VA: separate base, optional VSA and recommended Omni recipes.
- Configurable Portable/Desktop/manual ComfyUI connection and custom ports.
- Verified, resumable per-model downloads to the selected ComfyUI model folder.
- Single-file Windows build, persistent user data and a browser launch/quit flow.
- Source package and native Windows/macOS/Linux build workflow.

No user projects, generated videos, source PNG masters, model weights or machine
configuration are shipped. The 592 active JPEG preset thumbnails are included.
This release candidate needs testing on a second PC before a stable launch.
