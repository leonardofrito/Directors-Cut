# Competition memory — Director’s Cut

Rechecked on 2026-10-24. Read this before changing inference providers, licensing,
packaging or submission plans. Recheck the official page before submission.

Sources:
- https://comfy.org/open-source-higgsfield
- https://blog.comfy.org/p/higgsfield-promised-to-open-source
- https://docs.comfy.org/development/api-development/sdks

The requirements accordion is client-rendered. During this check its text was
retrieved from the public HowToEnterSection component and English translations
used by that page, not inferred from an empty accordion in the extracted HTML.

## Rules to preserve

- Build with the Comfy Developer Platform: Router, SDK, or both.
- Publish code and workflows, with an open-source license and runnable setup.
- Explain additional tools and models in the demonstration.
- Submit lawful, SFW material with appropriate IP/likeness rights.
- One entry per person; submission grants credited promotional use to organizers.
- Supply a demo of at most two minutes and a social demo post using
  `#OpenSourceHiggsfield`. A hosted trial link is encouraged, not mandatory.
- Deadline: October 30, 2026, 09:00 Pacific time. Winners: November 6.
- Open Weights Only excludes partner nodes and closed model APIs.
- The H3 bonus requires H3 as the core model. The LTX bonus requires LTX instead.

## Implementation evidence and decisions

The intended category is **Open Weights Only**. Preserve a fully local entry path.

- `requirements.txt` pins the official `comfy-sdk==0.5.0` and API proxy.
- `openframe/provider.py` instantiates `AsyncComfy`, submits workflow graphs,
  monitors jobs and downloads outputs through the SDK. Image and video generation
  use this provider. It is a real runtime integration, not just an installed package.
- The proxy connects to the user's ComfyUI; the official SDK documentation supports
  self-hosted ComfyUI. A separate Python/web interface is consistent with this setup.
- Image generation: local Qwen-Image 2.1. Video: Leonardo's H3 REF2VA eight-step
  workflow, with optional VSA. Do not silently change the video core back to LTX.
- The app has an MIT `LICENSE`, setup instructions in `README.md`, workflow JSONs,
  and attribution in `THIRD_PARTY_NOTICES.md` for Comfy Cinematic Studio and Lucide.
- An open local enhancer fits the intended architecture. Qwen3.5-4B is an Apache-2.0
  candidate, not installed or quality-tested as a video enhancer yet.
- The geocine H3 enhancer uses Liquid LFM1.0; local availability is not the same as
  Apache licensing. Review the actual model terms before bundling or distributing it.
- Do not enable GPT or another closed model API in the competition path. Such a
  dependency would conflict with Open Weights Only, even if the app code stays MIT.
  Do not assume an optional switch is automatically exempt; isolate another edition
  or obtain an organizer clarification if that option is later requested.
- Automatic setup/model downloads are compatible with the published requirements
  as reviewed on 2026-10-20; no mandatory manual-download rule was found. This is
  our reading, not a separate organizer ruling. Official ComfyUI Desktop already
  supports Download all into the matching model folders:
  https://docs.comfy.org/interface/features/template#model-storage-location
  Downloading weights over HTTP is different from closed model inference. Fetch
  from the original repositories, honor each model's license and gated access,
  preserve existing files, and keep inference on the SDK/local workflow path.
  Engine settings now offers explicit per-file downloads (BF16/INT8 and verified optional quantizations), with source labels, resume, expected-size/SHA-256 checks and no overwrite. See docs/model-downloads.md. Selection alone never starts a transfer; unavailable/incompatible releases are not invented or substituted.
- Model licenses remain separate from the app license. Qwen-Image 2.1 is labelled
  qwen-research; H3 uses its community license. This audit does not certify every
  model, LoRA, asset or future commercial use.

Model references:
- https://huggingface.co/Comfy-Org/Qwen-Image-2.1
- https://huggingface.co/MiniMaxAI/MiniMax-H3
- https://huggingface.co/Qwen/Qwen3.5-4B
- https://huggingface.co/geocine/minimax-video-prompt-enhancer-2.6b

## Connection, distribution and platform audit — 2026-10-24

The official SDK guide explicitly supports a self-hosted ComfyUI through the
official local API proxy and a configurable `COMFY_BASE_URL`. Choosing an existing
Portable/Desktop/manual installation, a custom address/port and model-download
folder preserves that integration. Downloading open weights does not introduce a
closed inference provider; the Open Weights Only path stays local.

No published requirement to support **every OS or GPU** was found in the reviewed
competition page, its app-requirements content recorded above, or linked blog.
The public page says to run the ComfyUI app wherever you like. Broad compatibility
is a distribution improvement, not a condition we should invent. This is our
reading of the published rules, not an eligibility guarantee from organizers.

The implementation now has Desktop path discovery for Windows/macOS/Linux,
Portable/manual folder selection, custom URLs/ports, an app-owned official proxy
and guarded downloads to the configured model folder. Actual tests versus simulated
platform fixtures and the remaining hardware limits are recorded in
[ComfyUI connection](comfy-connection.md). GPU detection is not proof that every
quantized model/custom node runs on every backend. Do not claim universal testing.

## Submission work still unverified or unfinished

Architecture is aligned; this is not a completed submission or an organizer ruling.
No Git remote is configured in this checkout, so public publication was not verified.
Registration, final public repository, clean-machine setup, demo, social link,
submission form and final rights/license review still need confirmation or completion.
Use original project characters and authorized references in the public demonstration.

Do not publish, submit forms or post on Leonardo's behalf without his authorization.


## Publication verified — 2026-10-26

With Leonardo's explicit authorization, the curated application source was published to https://github.com/leonardofrito/Directors-Cut and Windows release candidate v0.1.0-rc.2 was published with a standalone EXE, source package, setup guide and checksums. The public EXE link returned HTTP 200 and the expected 33,301,801-byte size. This supersedes the historical no-public-repository note above. It does not complete competition registration, social/demo submission, signing, second-PC validation or Mac/Linux native testing. Publication details and the separate clean checkout are in docs/publication.md.
