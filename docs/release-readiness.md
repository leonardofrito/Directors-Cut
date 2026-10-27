# Release status

## Available now

[Director’s Cut 0.1.0-rc.4](https://github.com/leonardofrito/Directors-Cut/releases/tag/v0.1.0-rc.4) includes a standalone Windows x64 EXE, source package, Quick Start, release notes and checksums.

The Windows EXE includes Python, the web app, 592 preset thumbnails, workflow graphs and prompt references. Model weights, personal projects and generated media are separate.

## Checked locally

The packaged Windows app opens with independent user data, loads its bundled resources and exposes the new GGUF and prompt-enhancer download controls. Targeted downloader checks cover resume, verification, existing-file preservation and destination validation.

The MCP bridge and video enhancer are optional. End-to-end MCP host testing and video-enhancer visual-quality review remain pending.

## Still pending

- First-use testing on a second computer.
- Published native macOS/Linux packages and execution on those systems.
- Windows signing and macOS signing/notarization.
- Competition registration, final demo/social post and submission.

The current Windows binary is unsigned and labelled pre-release. Publishing the source does not complete those remaining steps.

The build now supports verified Authenticode signing before ZIP/checksum creation, with a required-signing option. No trusted signing identity is configured and no signed release has been published. See [Windows signing](windows-signing.md).

[Quick Start](../packaging/QUICKSTART.md) · [Connection setup](comfy-connection.md) · [Competition record](competition-rules.md)
