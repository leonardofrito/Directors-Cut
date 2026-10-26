# Model setup

Director’s Cut connects to an existing ComfyUI. It uses the model files and custom nodes available to that engine.

## Images

Qwen-Image 2.1 requires a diffusion model, a compatible text encoder and its VAE. These are selected independently. Standard uses native safetensors files; optional GGUF diffusion files use a compatible GGUF loader.

For image workflows, a GGUF text encoder uses `CLIPLoaderGGUF`. Video's conditioning encoder currently uses its native safetensors path.

## Video

H3 REF2VA requires a diffusion checkpoint, conditioning encoder, video VAE and audio VAE. The original and optional VSA recipes have their own additional files. Omni uses a separate recipe and does not take the original H3 acceleration LoRA.

## Downloads

Choose a listed model variant to see its source and download size. An explicit Download action starts a resumable transfer into the configured ComfyUI models folder. Existing files are preserved, and completed downloads are checked against the catalog size and SHA-256.

Model installation does not install custom nodes. Precision labels and filenames alone do not establish loader compatibility. Community variants are labelled unofficial; their original model licenses still apply.

Optional prompt enhancers are separate from generation encoders and must be installed explicitly.

[Download catalog](model-downloads.md) · [Connection setup](comfy-connection.md) · [Quick Start](../packaging/QUICKSTART.md)
