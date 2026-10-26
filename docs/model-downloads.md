# Model downloads

Director’s Cut downloads selected model files from their original publishers into the configured ComfyUI models folder. Selecting an option does not start a transfer; downloads are explicit.

## Available families

| Purpose | Files |
| --- | --- |
| Qwen-Image 2.1 | Diffusion models, text encoders and VAE; optional GGUF diffusion conversions |
| H3 REF2VA | Original checkpoints, conditioning encoders, video/audio VAEs and optional GGUF diffusion conversions |
| Omni REF | Separate Omni checkpoints; all variants labelled unofficial |
| Image prompt enhancement | Dedicated Qwen T2I/editing enhancers, INT8 or W4A8 |
| Video prompt enhancement | Optional Qwen3.5 4B BF16 |

Published precision options vary by model. Unavailable or incompatible variants are not silently substituted. GGUF needs a compatible ComfyUI loader; downloading weights does not install that loader.

## Where files go

The selected ComfyUI models directory contains `diffusion_models`, `text_encoders`, `vae` and `loras`. Portable, Desktop and manual installations are supported. For a remote engine, use an explicitly mounted or shared models folder.

See [ComfyUI connection](comfy-connection.md) for paths and custom ports.

## Transfer behavior

Downloads run one at a time and support pause/resume when the source permits byte ranges. Partial files survive a restart. Completed transfers are checked against the expected size and SHA-256 before installation. Existing files are never overwritten; rejected content is not installed.

Restricted repositories still require access at the original publisher. The app does not bypass account gates or accept model terms on the user's behalf.

## Catalog and verification

The allowlist is [model_download_catalog.json](../openframe/model_download_catalog.json). It records file paths, byte sizes, SHA-256 hashes and source pages. Entries added on October 26, 2026 also pin their upstream revision.

Targeted checks cover resumed transfers, hash rejection, existing-file preservation, destination validation and GGUF installed-file detection. The download controls were checked in the Windows EXE. Video-enhancer visual quality is still awaiting user review.

## Original sources

[Qwen Comfy files](https://huggingface.co/Comfy-Org/Qwen-Image-2.1) · [H3 Comfy files](https://huggingface.co/Comfy-Org/MiniMax-H3) · [FastH3 Omni](https://huggingface.co/FastVideo/FastH3-Omni-Comfy) · [Qwen GGUF](https://huggingface.co/leejet/Qwen-Image-2.1-GGUF) · [H3 GGUF](https://huggingface.co/leejet/MiniMax-H3-GGUF) · [Qwen3.5](https://huggingface.co/Comfy-Org/Qwen3.5)

Model licenses remain separate from Director’s Cut's MIT license.
