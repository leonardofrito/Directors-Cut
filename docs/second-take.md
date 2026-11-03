# Second Take

Second Take replaces selected performers in a source video with characters from your image assets. Open it from the app switcher. It uses a separate persistent workspace and can select assets from any project or import a photo from your computer.

## Use

1. Choose a source video or an existing generated clip. Trim the source to a 4–30 second range.
2. Identify the source performers and assign each a replacement image. Add an optional written direction when needed.
3. Choose resolution, seed behavior and duration, then select **Generate Video**.

The local pipeline detects cuts, processes them separately and joins the results with the source audio. Replacement uses your selected compatible H3 recipe and the required Character Swap v1.5 LoRA. SelfLift follows your Engine settings choice. Engine settings provide model and node setup. Model licenses remain separate from the application license.

## Prompting

Name the original performer by distinctive source features and assign the replacement @handle. For multiple people, keep each original-to-reference assignment explicit. Use clear, short replacement instructions for each performer.

Automatic appearance captioning is currently disabled in Second Take. Explicit swap directions pass directly to H3 after resolving @handles to the attached image/video references, without added visual descriptions, placement boilerplate or audio instructions. Regenerating a saved cut also removes the previous automatic caption nodes. Source audio conditioning and final soundtrack restoration remain separate from prompt enhancement.

Second Take preserves the source environment. Environment replacement is not supported.

## Review cuts

Open a completed result and choose **View cuts**. A cut with one version activates its editable prompt. Multiple versions open a selection board; choose the version you want and generate another revision if necessary. **Join Cuts / Finish** assembles the selected versions while preserving earlier results.

## Limits

This is generative video editing, not exact pixel replacement. Identities, wardrobe, expressions, mouth shapes and occlusions can drift. Source audio is retained; that does not guarantee accurate lip sync. Automatic cut detection and person tracking may need manual correction. Smaller resolutions and shorter clips are useful for evaluating a result before a larger render.

Second Take is included in the rc.8.2 Windows executable and source package.

RTX Upscale runs sequentially per cut and restores the completed source video’s audio when joining. The default prompt supports up to six references and preserves the original scene; custom prompts remain editable.

New generations and individual cut regenerations use the model and SelfLift choices currently selected in Engine settings. An already queued generation retains its submitted settings.
