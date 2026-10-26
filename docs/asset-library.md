# Assets and references

An asset keeps its name, generation history and selected cover together. Characters, props and locations belong to a project and can be reused as references in other generations.

## Covers and history

Setting a cover changes the image used for the asset's Library thumbnail and reference. It does not create a duplicate asset or remove earlier takes.

Saving a renamed new asset keeps the existing study and its generations together. Reuse Settings restores a take's original editable prompt, presets and references; it does not start another generation.

## Reference images

Use an existing project asset or upload an image for a particular request. Uploaded references remain associated with their study; they are not automatically added as separate Library assets.

Known asset handles can be mentioned with `@`. The app resolves them to ordered reference images for the selected model. Each reference needs a real image binding; text alone is not a visual reference.

During image editing, the edited image is the first reference. Additional images follow it. The combined image-editing limit is ten images, including that source image. H3 video accepts up to nine image references.

## Files and downloads

Generated images download as PNG and videos as MP4. Downloaded filenames use the asset or shot name. Approved video takes provide the preferred shot for Library playback and download.

The packaged app stores projects in its per-user data folder. See [Quick Start](../packaging/QUICKSTART.md) for paths and backups.

[Image prompting](image-direction.md) · [Video workflows](video-workspace.md) · [Editing prompts](editing-prompts.md)
