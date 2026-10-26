# Editing Director’s Cut prompts

These are local Python sources. Restart Director’s Cut after editing backend prompt text. Existing images and saved prompts are preserved; changes affect new generations.

| What to change | File / section |
| --- | --- |
| Character type descriptions (Average, Bold, Extreme, animals, etc.) | [characters.py](../openframe/characters.py), `TYPE_HINTS` |
| Character categories and visible option names | [characters.py](../openframe/characters.py), `SPECS` and `EXTRAS` |
| Character prompt assembly and photographic rendering guidance | [characters.py](../openframe/characters.py), `character_prompt` and `character_render_direction` |
| Location and prop presets and descriptions | [asset_presets.py](../openframe/asset_presets.py), `LOCATION`, `PROP`, `asset_prompt` |
| Storyboard camera, framing, light, lens, film, look and color grade descriptions | [presets.py](../openframe/presets.py), the corresponding preset dictionaries |
| Prompt enhancer instructions | [enhancer.py](../openframe/enhancer.py), `SYSTEM` |
| How scene text, references and art direction become the final prompt | [provider.py](../openframe/provider.py), `build_graph` |

To keep a short label in the interface and a longer prompt behind it, keep the option key unchanged and edit its `hints` description. `TYPE_HINTS` is the existing example. Categories without a hint currently use the visible option text; add a hint mapping to that category to expand it without renaming the option. For custom selections, the text you enter is used directly.

The preset preview recipe is separate: [plan_preset_previews.py](../tools/plan_preset_previews.py). Editing a prompt does not generate preview images automatically.
