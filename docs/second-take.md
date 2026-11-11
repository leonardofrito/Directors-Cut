# Second Take

Import a source video, add replacement images, write an optional direction and choose Generate Video. Second Take keeps its own workspace and can import assets from any project.

## Modes

| Mode | Adapter | Purpose |
| --- | --- | --- |
| M | TARA Motion Transfer v1.0 | Reference-guided edits following the source video. |
| C1 | Akatz Character Swap v1.5 | Character replacement using the native video reference. |
| C2 | Alissonerdx Character Swap v1.1 | Character replacement using a latent guide. |

Entering Second Take checks and downloads all three missing LoRAs to the configured ComfyUI models/loras folder. Installed files are reused. Downloads use pinned revisions, size checks and SHA-256 verification, and never overwrite a different file. Progress and Retry appear when an adapter is missing. A remote ComfyUI needs an explicitly configured shared models folder. Downloading weights does not start a generation or restart ComfyUI.

M requires the BFS TARA node pack. Install missing packs in Connection → Workflow nodes; restart ComfyUI after installing new nodes. The adapter download and node installation are separate. HyperFlow is available for normal video generation, not Second Take.

## Source and cuts

Use Upload video, Use Generation or Adjust Trim. Choose a 4–30 second range. The trim dialog suggests scene boundaries on the CPU; keep or ignore each boundary, or use one shot. Accepted cuts are processed separately and joined with the source soundtrack.

View Cuts shows completed and pending cuts. Select a cut, edit its prompt, generate a revision and choose which version to keep. Join Cuts assembles the chosen versions. Existing results stay available. Changing a model or SelfLift affects new submissions; an already queued take keeps its submitted settings.

## References and prompts

Use @handles to assign replacement images. Keep source-to-reference mappings explicit when editing multiple people. The prompt enhancer is optional. It can describe image references, but cannot guarantee that identities, clothing, camera motion or lip sync remain exact. Source audio conditioning and final soundtrack restoration are separate.

## Downloads and limits

Select cards to download MP4 files individually or as a ZIP. In supported browsers, choose a destination folder. Select all and Delete are available with confirmation; active jobs and Timeline dependencies are protected. RTX Upscale works per cut before joining.

Character replacement remains experimental. Test a short range before a longer render. The application is MIT licensed; H3 and the community adapters have their own terms. See [Model licenses](model-licenses.md). No model weights are bundled in the app.
