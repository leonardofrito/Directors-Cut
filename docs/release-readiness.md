# Release candidate 0.1.0-rc.1 — 2026-10-24

## 0.1.0-rc.2 update — 2026-10-26

Adds explicit verified downloads for optional Qwen 2.1 / original H3 REF2VA GGUF
diffusion files and dedicated image/video prompt enhancers. Manual enhancer URLs
and installed GGUF detection are corrected. Five targeted download checks passed;
no new GPU inference or video-enhancer quality test was performed. The original
packaging evidence below remains historical; second-PC validation is still pending.

## Prepared locally

- Windows x64 single-file EXE with the Python runtime, web UI, 592 active preset
  JPEGs, workflow graphs, prompt guides and dependency notices. No weights, user
  projects, generated videos, original PNG masters or machine configuration.
- Source ZIP, quick start, release notes and SHA-256 checksums.
- Native Windows/Linux/macOS build workflow. It uploads artifacts only; it does
  not publish a release or submit a competition entry.
- Both preview correction batches finished: v4 126/126; v5 68/68. Leonardo accepts
  the current generation direction; no further preview regeneration is planned.
- Local pre-launch code save point under `.runtime/savepoints`. Original projects
  and media stay untouched in this workspace.

## Verified on this Windows PC

Fifteen targeted CPU tests passed (release paths/proxy dispatch, connection and
download behavior). The actual EXE passed `tools/smoke_release.py`: managed official
proxy startup, HTTP UI/resources, verified catalog listing, persistent project
across restart, graceful quit and bundled resource self-test. The self-test loads
the image graph, all three video recipes, prompt guides and all 592 referenced
JPEGs. It does not generate images/video or download model weights.

A separate packaged UI instance detected this machine's existing Portable ComfyUI
and showed the first-run Connection panel, app version, licenses, data-folder and
Quit controls. Quit was verified from the browser. The workspace studio was then
reopened against its original library with private-network listening preserved.

Data lives outside the one-file extraction directory. The normal binary defaults
to the per-user data folder; `--data` can select an existing studio library without
moving it. The app reuses the same data directory on restart. A conflicting default
port can fall back to a free port; explicit `--port` errors are preserved.

## Still pending before a stable/public launch

- Second-PC test with the friend's actual ComfyUI, GPU, model downloads and one
  small image/video run. Existing same-PC generation is not a clean-machine test.
- Native Linux/macOS builds and execution; no Linux environment or Mac was
  available for local native packaging. The CI matrix is prepared but not run.
- Windows code signing / macOS signing and notarization. This candidate is unsigned.
- Public Git repository/release location, final public license/asset review,
  approved demo/social post, competition registration/submission confirmation.

The local SDK route stays intact; packaging adds no closed inference provider.
Model terms remain separate. Follow [competition memory](competition-rules.md)
and [quick start](../packaging/QUICKSTART.md); do not call this a completed public
submission or universal hardware certification.
