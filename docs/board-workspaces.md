# Canvas workspaces

Director’s Cut has three workspaces with shared controls, image viewers and video playback.

- **Asset Creation** creates and edits characters, props and locations within a project.
- **Director’s Cut** builds project shots and assembles them in a timeline.
- **Second Take** replaces performers in an imported video and keeps its results in a separate workspace. See [Second Take](second-take.md).

## Browsing and review

The project canvas shows one card per asset or shot, using its approved take or the latest completed result. A lime border marks approval. Names and take counts appear on hover or keyboard focus. Video thumbnails play silently on hover and pause when hidden.

Open a card to browse its takes. The grid scrolls vertically, including portrait images and larger batches; its scrollbar is hidden. Full review hides the prompt island and contains the media, Back, download and available take actions on one surface. Photos have no playback controls. Previous/next arrows appear at the sides on nearby hover or keyboard focus.

**Reuse Prompt** explicitly restores the selected take’s editable prompt, presets and references. Saved compiled or enhanced generation text does not replace the editable prompt. Working drafts are remembered separately per project and item.

## The floating composer

The composer overlays the canvas. Asset Creation and Director’s Cut share the header controls, full-width prompt, reference actions and generation material. Second Take uses the same video prompt, seed, size, duration and Generate controls, with its source and character cards on the left.

The asset-kind icon selects Character, Prop or Location. The corresponding Lab opens a compact panel above the island. Image editing exposes **Edit presets** in the same position, with repeat-click deselection and optional free text. Camera, Direction and Advanced use the same panel treatment in Director’s Cut.

Ratio, size and duration menus remain open after selection. Clicking outside dismisses the menu without activating an item behind it. Dismissal also completes when a background tab suspends its animation. Seeds support random, fixed, increment and decrement modes.

Image references accept the picker, local drops, pasted images and supported web-image drops. Video and audio references use separate media slots. The shared video trim dialog preserves the source and offers draggable In/Out handles and a range grip.

## Editing the final cut

Director’s Cut puts **Edit Timeline**, **Preview Final Cut** and **Download** in the app header. Download offers MP4 or DaVinci Resolve export. The timeline uses non-destructive source ranges on V1/V2 and A1/A2, with split, linked A/V, undo/redo and saved edits. Final preview uses the same player as generated videos. See [Sequences and examples](sequence-and-examples.md).

## Lightweight rendering

The app reuses the existing generation controls and endpoints rather than maintaining separate editors for each view. Thumbnails load lazily; offscreen videos pause. Glass materials use static textures, gradients and small highlights. Motion respects reduced-motion preferences. Layout work does not require model inference.

The thumbnail size slider stays in the lower-right corner. Full rows fill the available width; a sparse final row retains its natural card size. Second Take is independent of the selected project and highlights the current result with a stronger lime outline.
