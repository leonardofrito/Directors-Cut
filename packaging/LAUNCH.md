# Launch handoff

## Friend's Windows test

Send the Windows x64 EXE (or the Windows ZIP). Start with `START-HERE.md`.
No Python installation, source checkout, API key or copied model weights is needed.
Start ComfyUI, detect/select its real data/models folder, then download the chosen
missing files. Check their source/format labels; all Omni variants are unofficial.

Verify one asset, one image reference and one short video; approve/download a take,
quit from Settings, reopen and confirm the project is still there. Use a small
generation first. This real second-PC/GPU check is still pending.

For the existing source library on the same machine, use
`DirectorsCut.exe --data "/path/to/existing/studio"`, or copy its `projects` folder
to the new per-user data folder while both studios are closed. Do not send that
library, `.runtime/engine.json` or personal media to other users as part of a release.

## Native packages

Run the **Build release candidates** workflow on the repository, or build on each
target OS with Python 3.12 and `requirements-build.txt`. The checked-in workflow
builds and smoke-tests the EXE, Linux executable and macOS app ZIP without GPU
inference. Those Mac/Linux jobs have not been run in this local workspace.

## Public release draft

**Title:** Director's Cut 0.1 — Create locally.

**Description:** Create characters, props and locations, then bring your assets
into reference-driven video. Director's Cut connects to your own ComfyUI, keeps
projects on your computer and uses local Qwen-Image 2.1 and MiniMax H3 workflows
through the official Comfy SDK. Open-source app, no paid inference API required.

**Attachments:** native package, source ZIP, quick start, release notes and
SHA256SUMS. Identify this build as a release candidate until the second-PC test.
The application is MIT; model licenses and hardware requirements are separate.

Choose/approve the public repository and release destination before publishing.
Code signing, final demo/social post and competition submission are separate steps.
The build workflow never publishes or posts automatically.
