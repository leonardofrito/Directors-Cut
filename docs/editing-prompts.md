# Editing the default prompts

Prompt definitions live in local Python sources. Restart Director’s Cut after changing backend text. New generations use the changes; existing takes retain their saved settings and prompts.

| What to edit | Source |
| --- | --- |
| Character types, traits and appearance descriptions | [characters.py](../openframe/characters.py) |
| Location and prop presets | [asset_presets.py](../openframe/asset_presets.py) |
| Expanded preset directions | [preset_directions.py](../openframe/preset_directions.py) |
| Camera, framing and lighting dictionaries | [presets.py](../openframe/presets.py) |
| Image enhancer instructions | [enhancer.py](../openframe/enhancer.py) |
| Video direction and enhancer instructions | [video_prompt.py](../openframe/video_prompt.py) |
| Image-edit presets | [edit_presets.py](../openframe/edit_presets.py) |
| Image prompt assembly | [provider.py](../openframe/provider.py) |

Keep option keys unchanged when you only want a richer backend description. That preserves the short labels and saved selections. Custom written details remain part of the user's request.

Preset thumbnails are separate image files. Editing a prompt does not regenerate them.

[Image prompting](image-direction.md) · [Video workflows](video-workspace.md)
