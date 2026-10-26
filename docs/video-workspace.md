# Video workspace

Video generation uses a duplicate of Leonardo's ComfyUI workflow
`user/default/workflows/H3 REF2VA.json`. Its original file was not changed.
`workflows/video/source.json` records the source path and SHA-256. The preserved
source copy is `H3_REF2VA_original.json`.

The default **Original · 8 steps** keeps the source Ref2VA W4A8 diffusion model,
32B INT4 encoder, video/audio VAEs, eight-step Ref2VA LoRA, res_multistep sampler
and simple scheduler. Scene references, prompt, seed, duration, size and output
prefix are controlled by the app. The old motion-transfer example video is not
an input to new scenes.

**VSA · 8 steps** is a separate, optional experimental variant. It transplants
the VSA gates after the eight-step LoRA, with sparsity .50. Its sampling branch
bypasses the source attention-backend override to avoid stacking attention
overrides. No four-step LoRA is used in either app preset.

Video scenes and their takes are project-owned `mode: video` shots, excluded
from the image storyboard and asset-study lists. Each take records its exact
workflow/settings and downloads an MP4 through the official Comfy SDK proxy.
The player supports HTTP range requests and a direct MP4 download, including
generated audio. The same persistent FIFO queue handles image and video jobs.
The video tab accepts up to nine project image references via Library or @handle;
bindings become `<Picture N>` in reference order. The reference picker shows only
assets with add buttons, supports search, and closes with Done, Escape or an
outside click. References have a separate removal button on hover/focus.
Typing @ in the prompt offers matching project assets and adds the selected image.
The editable scene selector also offers saved scenes and a compact plus button.
Three compact controls share a popover: nine aspect ratios from 16:9 to 9:16,
0.2–2 MP in 0.1 MP increments, and 2–30 seconds in one-second increments.
Native frame alignment still applies to the resulting duration. Workflow selection
remains available. Ctrl+Enter submits the active video scene.

Click the connected-engine button to open Engine settings directly. Its Images
and Video sections separate image weights/LoRAs/enhancers from H3 configuration.
Video settings contain Original/VSA and installed compatible Ref2VA diffusion,
32B H3 encoder, video/audio VAE, eight-step LoRA and optional VSA gate files.
Selections persist in browser preferences and each take's immutable settings.
Reuse Settings restores the selected take's model files. The Qwen3.5 4B visual
prompt enhancer is separate from H3's 32B conditioning encoder and is never listed
as its replacement. Its video-enhancer integration remains a separate task.

The video tab and server enforce the product minimum of a 12 GB GPU, allowing
normal driver overhead in the reported VRAM figure. That is an eligibility limit,
not a promise that every resolution/reference count/duration fits on every card.
The initial size is .5 MP and duration five seconds. The native frame alignment
rounds this to 124 frames at 24 fps, or about 5.17 seconds.

Validation on this machine:

- Both original and VSA runtime graphs validated without missing nodes/models.
- A VSA render with the original 32B encoder/eight-step LoRA completed at
  960 × 544, 124 frames, with one video and one audio track, in about 189 seconds.
- The completed test is saved in project RPG, video scene **Elogio Certeiro**.
  New generations still default to Original; its first take is labelled VSA.
- SDK MP4 download was checked by remuxing the existing clip, without another
  diffusion render. MP4 file serving and byte-range playback were checked too.
- Character fidelity, dialogue pronunciation and visual preference remain for
  Leonardo's review; successful execution does not establish quality equivalence.

Source node: https://github.com/Kablex/ComfyUI-Ref2VA-VSA

## FastH3 Omni INT8

The separate **FastH3 Omni · INT8 · 8 steps** preset in Engine settings uses
`fasth3_omniref_8step_pruned_int8_convrot.safetensors`, Euler/simple, guidance 1,
video/audio shifts 12/3 and native BlockSparseAttention VSA with 10% keep.
It uses the checkpoint's own compression gates, without an acceleration LoRA
or the older external VSA gate patch. Original and experimental VSA remain separate.
The installed H3 32B INT4 encoder and existing video/audio VAEs are reused.

The editable workflow `workflows/video/FastH3_OmniRef_8step.json` is also copied to
ComfyUI's `user/default/workflows/Directors Cut/` folder. It includes the dungeon,
Narciso and Bardo references. Runtime graphs use the matching `.api.json` template.

The local ComfyUI 0.41.2 loader misread this checkpoint's 32 PDD output heads as
latent channels, causing the reported 24-versus-768 tensor error. A local fix in
`comfy/model_detection.py` derives channels per head from `pdd_steps`; the MiniMax
final layer allocates all heads and uses its existing PDD combination math.
Single-head models retain their previous dimensions and behavior. Original files
were backed up under `.runtime/`; the reproducible diff is
`workflows/video/fasth3-pdd-loader.patch`. A future ComfyUI update may replace this
local patch; check upstream support before reapplying. ComfyUI must restart after
changing its loader.

Recipe source:
https://raw.githubusercontent.com/Comfy-Org/workflow_templates/main/templates/video_fasth3_ominiref_r2v.json

Verified locally on 2026-10-20: the corrected INT8 workflow completed with three
RPG references at 960 × 544, 124 frames, eight steps. Sampling took 81 seconds;
the whole ComfyUI prompt took 120 seconds. The SDK downloaded the result into
RPG / **Elogio Certeiro · Fast Omni INT8**, take 2 (take 1 records the initial
loader error). This confirms execution; character and dialogue quality await
Leonardo's review.

## Model-driven video settings (2026-10-21)

Engine settings now show one diffusion-model picker, with Omni files first.
Selecting Omni chooses its Euler/native-VSA/no-acceleration-LoRA recipe;
selecting original H3 Ref2VA chooses Leonardo's res_multistep/eight-step-LoRA
recipe. Filename-based routing is also enforced by the backend for saved takes.
Omni BF16/INT8/W4A8 names and original Ref2VA GGUF filenames are accepted.
The two installed `w4a8gptqmixed` Omni files and the mixed-W4A8 32B encoder are
listed. New Omni scenes default to that encoder; video/audio VAEs stay independent.

Optional video LoRAs support multiple files, enable switches and strengths.
They are saved with each take. Do not use base-H3 acceleration LoRAs on Omni.
The settings include model download links and explicit local file imports for
LoRAs and GGUF. Set `OPENFRAME_COMFY_ROOT` if ComfyUI is outside the default
portable Windows folder. Imports do not overwrite existing files or start jobs.
No GGUF weights were downloaded or rendered during this change. GGUF selects
`UnetLoaderGGUF`; actual H3 execution requires an H3-compatible version, such as
the linked leejet fork, rather than assuming every older generic loader works.

Video @mentions have inline highlights and hover previews. The picker inserts
the mention into the prompt; deleting that mention removes the corresponding
reference. Legacy explicitly attached references without @mentions are retained
when opening an existing scene.

Workspace navigation uses the current asset/scene name in the left editor header,
with rename, delete and browse icons. Browse opens a searchable project grid with
thumbnails and the New action; only the project picker remains in the global
header. Both editor bodies remain visible. Deletion removes the linked library
entry for assets, archives take metadata without deleting media files, and is
refused while an affected item is generating.

## Optional direction and references (2026-10-21)

Video uses the same visible preset groups, icons, counters, square cards and Custom
fields as Assets/Location, supplying genre, era, pacing/cuts,
camera medium, sensor, lens, aperture, framing, color palette, lighting and 26
camera moves. Automatic emits no instruction. The free prompt remains separate;
Reset only clears the selected directions. Choices are stored with each take.

The video enhancer uses the installed Qwen3.5 4B via native TextGenerate, with a
video-specific system instruction, selected directions and duration. It reads attached reference images when the native BatchImagesNode and
ResizeAndPadImage nodes are available, keeping their assigned roles and tags.
Each image is padded to 512 × 512 for analysis without cropping; the original
references still feed H3. Without those nodes, rewriting is text-only. The final prompt appends the original scene, reference bindings, exact dialogue
and chosen direction as authoritative constraints. Empty/refused expansions, or
ones that discard requested invisibility, fall back to the directed prompt. Enablement requires the selected installed model and nodes.
The initial runtime smoke test encountered a ComfyUI startup failure,
`RuntimeError: operator torchvision::nms does not exist`, in the installed
Torch/Torchvision environment. The engine subsequently became available again;
no Torch packages were changed by this work. A text-only SDK smoke test completed after the existing user queue finished.
Qwen3.5 4B returned a structured expansion retaining invisible anatomy and the
continuous shot. It dropped the reference tag and altered dialogue punctuation;
the final graph now appends the original authoritative constraints to preserve
those exactly. The completed video graph, including reference-image analysis,
passed live workflow validation. No image/video render was used for validation.
Image-aware character fidelity and creative quality still require review.

Project Library now opens the full asset manager in both tabs, so deletion is
available in Video too. Both project browsers have a persisted preview-size
slider. Header names are larger; the bare pencil sits beside the name and
double-click also opens rename.

Assets' Image reference action uploads an image directly to the study, with a
role (wardrobe, identity, hair, style, background, prop). These photos live in
project `reference_images` and per-study `upload_reference_ids`, not the Library.
Role-specific Qwen instructions restrict what gets copied. Wardrobe/hair photos
override their matching character presets in the generated prompt. Removing a
chip detaches it without deleting the source file or old take metadata. Video
still uses Library assets and @mentions; its redundant +Reference button was
removed.

The video preset list has no collapsible outer panel. Only reference thumbnails
have their own compact, collapsible strip above the prompt. Existing location
preview images are reused where choices match. Library image heights scale with
their card widths; editor names use a specific 22px rule that overrides the older
small editor-heading style. Six legacy/overlapping tests were removed; this UI
change used only a targeted syntax/structure check, without renders or a suite run.
