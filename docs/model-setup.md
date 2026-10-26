# Model setup

Automatic model downloading is not a requirement stated on the [competition page](https://comfy.org/open-source-higgsfield). Settings provides explicit verified model downloads, source links, configurable target folders and live installed-file discovery. See [downloads](model-downloads.md) and [connection setup](comfy-connection.md). Model weights stay on the original publishers' services and are governed by their own licenses.

1. Choose an image model in Director's Cut.
2. Choose **Standard** or **GGUF** and open **Model setup**.
3. Download a compatible variant from its publisher; use the missing-file list and the supplied workflow as the reference. Some links point to optional prompt-enhancer models.
4. Put diffusion weights under `ComfyUI/models/diffusion_models/`, encoders under `ComfyUI/models/text_encoders/`, and VAEs under `ComfyUI/models/vae/`. Existing ComfyUI model-directory mappings remain in effect.
5. Install any required loader nodes separately, following their documentation. Restart ComfyUI if adding custom nodes. Director's Cut does not modify the ComfyUI environment.
6. Click **Refresh installed models**, select the installed files, then generate when the workflow reports ready.

## Formats and precision

Standard and GGUF are the loader/container choices. BF16, FP8, INT8, INT4 and W4A8 describe precision or quantization variants, not universally interchangeable files. GGUF has its own quantization levels. A variant must be supported by the specific model architecture and loader; renaming an extension does not convert weights.

The app changes `UNETLoader` to `UnetLoaderGGUF` for a GGUF diffusion model and removes inputs that do not belong to that loader. Encoder format is independent: it uses `CLIPLoaderGGUF` only for a selected GGUF encoder. It never attempts to load both diffusion variants via a model switch. Multiple diffusion loaders, such as Ideogram's conditional/unconditional pair, must all have matching available files before its GGUF path is ready.

GGUF support is model-specific. The installed ComfyUI-GGUF code has an explicit architecture allowlist; generic GGUF nodes do not guarantee support for every new model. There are no compatible image GGUF files installed for the supplied catalog, so only graph substitution and availability behavior were tested. A real generation test is still needed for each new variant. [ComfyUI-GGUF documentation and source](https://github.com/city96/ComfyUI-GGUF).

## Current verification

Qwen 2.1 native INT8 diffusion + W4A8 encoder + BF16 VAE is generation-tested. The eight source workflows are preserved and grouped into seven visible model choices, including the supplied FLUX 3 Image Klein workflow. Qwen 2.1 generation and editing use one selector entry. Project references automatically connect native Qwen or FLUX conditioning; these reference paths are graph-verified but have not been image-generation tested. Other models remain untested. No large model downloads were started.
