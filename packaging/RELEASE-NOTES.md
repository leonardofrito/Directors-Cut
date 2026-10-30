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
