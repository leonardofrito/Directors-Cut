# Model setup and downloads

Settings now lists downloadable weights together with compatible installed files. Selecting a missing file reveals a highlighted Download button, file size and source. Choosing a file does not download automatically; the explicit button queues a local HTTP transfer. Shared progress and pause/resume controls appear under that selector. After installation, refresh the installed ComfyUI model listing automatically and keep the selected filename.

The allowlist is `openframe/model_download_catalog.json`, verified against upstream Hugging Face file metadata on 2026-10-23. It records exact paths, byte sizes and SHA-256 hashes. Downloads go to the model directory selected in **Engine settings â†’ Connection**, under `{diffusion_models,text_encoders,vae,loras}`. Portable/Desktop/manual installations are detected where possible; custom paths and ports remain editable. Remote engines require an explicitly mounted/shared folder. Source URLs and relative model filenames remain restricted to the verified catalog. See [connection setup](comfy-connection.md).

Transfers are serial, use partial files and HTTP Range when supported, retry network failures, validate size/SHA-256, then publish without overwriting existing files. A server restart preserves partial bytes; click Download again to resume. A failed hash is quarantined, never installed. Gated repositories require access at the original source; no credentials, patches, custom nodes or model licenses are silently accepted/installed.

## Catalog coverage and precise names

- Qwen 2.1 diffusion: Comfy-Org BF16 and INT8. Independent NVFP4 from BennyDaBall is marked Unofficial. Its text encoder acceleration needs an upstream patch, which this feature does not install.
- Qwen 2.1 encoder: BF16 and INT8 from Comfy-Org; W4A8 from Comfy-Org is marked experimental/Unofficial as requested, with its real source visible. Community NVFP4 is also Unofficial.
- Qwen 2.1 diffusion W4A8 is visibly unavailable: the verified Forge Neo release is sharded/runtime-specific, not a drop-in ComfyUI checkpoint. It is not offered as a working download.
- H3 REF2VA: Comfy-Org pruned BF16/INT8, community W4A8, matching BF16/INT8/NVFP4/W4A8 encoders. No FL2VA download is substituted.
- Comfy-Org currently publishes NVFP4 for the H3 encoder, not REF2VA diffusion. The latter is marked unavailable; Omni has a community NVFP4 option.
- H3 video VAE: **FP16 original**, not BF16, plus INT8 ConvRot. Audio VAE: FP32 original. These are the actual published precisions.
- Every Omni REF model is marked Unofficial, including FastVideo's BF16/INT8 and the independent mixed-W4A8 files. Omni and base-H3 still select different generation recipes automatically.
- Existing compatible installed files and GGUF imports remain selectable. Unknown community files retain their actual filenames. No generation workflow or SDK path was changed.

## Verification

Four small mocked download tests cover resumed byte ranges and final hash, rejected hashes, existing-file preservation/unknown IDs and destination traversal. Browser checks verified installed variants, missing-file Download highlight, disabled unavailable choices and the Video settings. No large model was downloaded and no GPU generation was used for verification.

API: `GET /api/models/catalog`, `GET /api/models/downloads`, `POST /api/models/downloads` with catalog ID, `POST /api/models/downloads/{id}/cancel`.

Primary sources: [Qwen Comfy files](https://huggingface.co/Comfy-Org/Qwen-Image-2.1), [H3 Comfy files](https://huggingface.co/Comfy-Org/MiniMax-H3), [Kijai H3 W4A8](https://huggingface.co/Kijai/MiniMax-H3-experimental), [H3 W4A8 encoder](https://huggingface.co/Winnougan/MiniMax-H3-INT4_Convrot_ComfyUI), [FastH3 Omni](https://huggingface.co/FastVideo/FastH3-Omni-Comfy), [Omni mixed W4A8](https://huggingface.co/tsolful/FastH3-Omni-Comfy-INT4mixed-INT6GPTQ), [Qwen community NVFP4](https://huggingface.co/BennyDaBall/Qwen-Image-2.1-NVFP4).

## Release candidate 0.1.0-rc.2 â€” 2026-10-26

- GGUF selectors now expose verified Qwen 2.1 files from leejet and original H3 REF2VA diffusion files, with the existing resumable Download button and source page. These are optional community conversions, not Omni checkpoints; current compatible GGUF nodes remain required.
- Dedicated Qwen 2.1 T2I/editing enhancers (INT8/W4A8) and the optional Qwen3.5 4B BF16 video enhancer use the same explicit download manager into text_encoders. Missing enhancer selection does not enable inference.
- Fixed malformed manual enhancer URLs. New catalog entries pin the public repository commit and published LFS SHA-256/size, verified using metadata only. Existing weights are preserved. No additional GPU generation or video-enhancer quality validation was performed.
