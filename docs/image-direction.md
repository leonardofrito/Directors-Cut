# Image prompting and enhancers

Director’s Cut uses Qwen-Image 2.1 for image creation and editing. A request combines your written prompt, selected presets and any attached references.

## Start simple

Use presets for traits you can select directly. Add a short written request for the details that remain. A longer prompt is useful for a complex composition, but it is not required for a straightforward asset or edit.

Presets expand into backend descriptions while retaining short labels. To change those descriptions, see [Editing prompts](editing-prompts.md).

## Image references

References can come from project assets or uploaded images. The app assigns them in order as `<image1>`, `<image2>` and so on. State what to preserve or change; avoid asking for an exact composition when you want a new viewpoint.

The first reference is cropped to fill the selected output canvas, avoiding added white borders. Changing the requested camera angle is still model-dependent.

## Optional prompt enhancer

The dedicated Qwen T2I enhancer expands text-to-image requests. The editing enhancer also uses attached image references. Both offer INT8 and W4A8 download variants in the configured `models/text_encoders` folder.

Enhancement requires compatible native ComfyUI text-generation nodes. A missing model can be downloaded, but that alone does not satisfy missing node requirements. The enhancer stays optional; the original prompt can be sent directly.

The backend preserves explicit subjects, unusual anatomy, reference bindings and requested rendering style. Empty or unusable enhancer output falls back to the original request. This guard does not guarantee visual fidelity; review the generated result.

## Source files

- [Character presets](../openframe/characters.py)
- [Location and prop presets](../openframe/asset_presets.py)
- [Preset directions](../openframe/preset_directions.py)
- [Enhancer instructions](../openframe/enhancer.py)
- [Prompt assembly](../openframe/provider.py)

[Assets and references](asset-library.md) · [Model downloads](model-downloads.md)
