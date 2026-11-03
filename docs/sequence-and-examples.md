# Sequences, camera previews and Bank of Ideas

The 26 camera movement cards use bundled silent WebM previews in web/assets/video-presets. They autoplay and loop while visible, without hover. Offscreen or hidden-page clips pause; no inference is used to show them.

Framing and pacing use the same visible-only, muted-loop preview system. The local follow-up batch reuses the pavilion reference: 15 framing examples and five pacing examples, 4 seconds at 0.4 MP. Ready files are added to the manifest automatically; progress is in `Direction Preview Progress.txt`. Framing is curated only in Video; saved legacy directions and Assets choices remain compatible. The batch never retries failed generations automatically.

Camera Type, Sensor and Lens also show available silent sample clips. Aperture and Focal length keep their continuous controls. A full-width video-only panel sits above each active numeric slider and loops its closest available sample. Drag, wheel or use the keyboard to update the example. It remains present after the pointer leaves; offscreen or hidden-page media pauses and resumes when visible. There are no captions or sample-card rows beneath the sliders. The local **Camera Preset Tests** project contains all 23 original MP4 shots with numbered category/value titles for larger playback in Library → Shots. These originals are 0.4 MP; larger playback does not change the generated resolution. UI WebMs are lightweight copies, not replacements for those originals.

Video camera directions describe visible photographic effects through `video_optics.py`. Leonardo found V3 less effective than V2; that batch is not a quality certification. The later comparison preserves all 52 captions in Camera Prompt Comparisons. Optical cues now sit in the visual-description section (or before free text), with looser framing-independent lens descriptions. Custom directions and editable original prompts stay unchanged. Lens setup applies from the opening frame; separately requested motion remains independent. The slider preview is an inline full-width panel above the control, with no floating tooltip. New test media is not installed into the UI manifest automatically; Leonardo reviews results first.

## Shots

Library → Shots → Reorder enables drag/drop and earlier/later arrows for the source-shot list. Without a saved timeline, playback and export use that order, preferring approved takes and falling back to the latest completed take.

Library → Shots → Timeline opens a small non-destructive editor with V1/V2 and A1/A2. Initially it assembles the completed shots in source order. Drag clips to move them or change tracks; drag their edges to trim. Start, source In and Length also accept precise seconds, snapped to 24 fps. Split cuts the selected clip at the playhead. Undo/Redo and autosave preserve editing progress. Source media remains unchanged.

Link A/V moves and trims linked video/audio together. Disable it to offset audio independently for manual J/L cuts. Overlap clips across separate tracks; clips on the same track cannot overlap. V2 covers V1, and A1/A2 mix together. Gaps show black or silence. The built-in browser preview uses at most two video and two audio elements, and pauses on closing or hiding the page. Browser seeking is a working preview, not a frame-accurate external monitoring guarantee.

Once saved, the edited timeline owns Play sequence and exports; reordering the source-shot list does not rearrange existing timeline clips. New shots can be added from its source list. Shots used by a saved timeline must be removed from the timeline before deleting their source shot. The editor intentionally excludes transitions, effects and ripple editing.

Export → MP4 renders the saved edits, fitting mixed frame sizes onto the first source's frame without cropping. Encoding is CPU-only, bounded to two threads, with one export at a time. Export → DaVinci Resolve creates an OTIOZ timeline with original media, source trims, gaps and four separate tracks. Import with File → Import → Timeline in Resolve 18.5 or newer. The official OpenTimelineIO reader validated the bundle, clips, timing and media extraction; the Resolve GUI has not been certified by this check.

## Example

Projects → Bank of Ideas installs the curated bundled example on explicit request. Its 14 approved clips and 12 image references are compressed for distribution (8.8 MB). It contains no failed takes, unselected generations, machine settings, uploaded motion/speech recordings or model weights. Opening it again preserves edits instead of overwriting the project. The original local commercial project remains separate.


The release staging script includes only the curated examples directory, not local projects or runtime data. Changes are local until a new release is explicitly published.

Validation: live UI ordering/restoration/playback, completed DaVinci export, 26 muted looping previews; isolated CPU mixed-size/silent-clip export and duration checks; official OTIOZ parse/extraction; temporary example import and non-overwrite checks. No GPU inference for verification.

Format references:
- https://documents.blackmagicdesign.com/SupportNotes/DaVinci_Resolve_18.5_New_Features_Guide.pdf
- https://github.com/AcademySoftwareFoundation/OpenTimelineIO/blob/main/src/opentimelineio/bundle.h
