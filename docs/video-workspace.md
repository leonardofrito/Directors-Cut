# Video workflows

Director’s Cut generates video through MiniMax H3 **REF2VA**, using reference images, a written scene and optional motion or speech conditioning.

## Model recipes

- **Omni** is the recommended local option. Its eight-step recipe uses native VSA without a separate acceleration LoRA. Omni REF variants are labelled unofficial.
- **Original H3** retains the original eight-step REF2VA recipe and its acceleration LoRA.
- **VSA** is an optional experimental variant of the original recipe.

A selected diffusion checkpoint chooses its matching recipe. Omni sampling settings are not applied to an original H3 checkpoint. Optional GGUF diffusion files require an H3-compatible loader.

The conditioning encoder, video VAE and audio VAE are separate model files. The optional Qwen3.5 4B prompt enhancer is also separate from H3's conditioning encoder.

## References and prompts

Project image references become `<Picture 1>`, `<Picture 2>` and so on in input order. Give each reference a clear role: character identity, clothing, prop or environment.

An attached motion clip is supplied as `<Video 1>`. An attached speech reference is supplied as `<Audio 1>`. These media slots are separate from image references. Their presence conditions generation; it does not guarantee an exact camera trajectory or exact lip synchronization.

Final audio is a separate soundtrack replacement step. It does not become an H3 speech reference.

For a video prompt, describe feasible actions in sequence, camera behavior, any cuts, continuity and sound. Preserve subject identities between shots. Reference images do not replace a clear scene request.

## Optional prompt enhancer

A local Qwen3.5 4B model can expand video direction through native ComfyUI text generation. Image-aware context depends on compatible nodes. This feature remains optional, and end-to-end visual-quality review is pending.

## Takes and saved settings

Video takes use the shared project queue and retain their original prompt, structured direction, references and selected model files. Reuse Settings restores that snapshot without generating automatically. Approved takes become the preferred shot in the Library.

Outputs are MP4, including generated audio or an optional replacement soundtrack. The source recipes are under [workflows/video](../workflows/video).

[Model setup](model-setup.md) · [Downloads](model-downloads.md) · [MCP setup](mcp.md)
