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
