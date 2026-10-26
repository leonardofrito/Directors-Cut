# Qwen 2.1: preset-first requests

For ordinary assets, start with a short request and the existing presets.
A preset-only request is valid. The application already expands selections;
do not duplicate all of that expansion in the free prompt. Leave the local
Prompt Enhancer off for this baseline. Add detail if intent is missing or a
result demonstrates a specific need. These are practical project defaults,
not a guarantee that short text always outperforms detail.

Call get_image_presets for exact available options. Pass those choices to
update_study as structured settings. Each choice uses {"value": "Exact label"};
custom uses {"value": "__custom__", "custom": "your detail"}. Supported multiple
categories use "values": ["Exact label", "Another label"] with a valid first
"value". Avoid contradictory selections, e.g. glasses and sunglasses.

JSON is the MCP/tool interface; the app sends assembled text to Qwen. You do
not need to paste JSON into the free-prompt field. Use preview_image_prompt to
inspect that exact text before generation. It neither saves nor runs a model.
Reference photos keep their real image order, and image edits can use the
edit_preset field instead of hand-writing a character sheet/pose/crop prompt.

For H3 use detailed REF2VA direction: stable subjects and reference roles,
sequential actions, camera, cuts, continuity and audio within the duration.
Full model guides remain optional for complex requests. Do not mix H3 syntax
into Qwen prompts or invent another Qwen version/model name.

## Example JSON and actual assembled prompt

```json
{
  "prompt": "A cheerful mechanic wearing a red scarf.",
  "asset_kind": "character",
  "ratio": "1:1",
  "megapixels": 2,
  "prompt_enhancer": false,
  "character_traits": {
    "character_type": {
      "value": "Average"
    },
    "gender": {
      "value": "Woman"
    },
    "age": {
      "value": "Young adult"
    },
    "hairstyle": {
      "value": "Bob"
    },
    "render_style": {
      "value": "Studio portrait"
    }
  }
}
```

The current shared generation assembler returns:

```text
A cheerful mechanic wearing a red scarf.
Character type: A normal human character with natural, believable facial features and proportions. Gender presentation: Woman. Age: Young adult. Hairstyle: Bob. Visual style: Studio portrait.
Rendering medium: a photorealistic studio portrait of a physically present subject. Natural skin pores, detailed hair strands, tangible materials and photographic lighting. Keep all requested unusual anatomy, but depict it photographically, without cartoon, painting or concept-art rendering. Use a seamless pure white studio background. Replace any described environment with white. Isolate the character, requested clothing and accessories; only a subtle grounding shadow.
```
