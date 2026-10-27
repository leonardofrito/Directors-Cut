# Publication audit — October 27, 2026

Scope: the public repository and published rc.2/rc.3 downloads, before the rc.4 update. This is an exposure audit, not a penetration test or a guarantee that every dependency is vulnerability-free.

## Findings

- The repository had 762 tracked files across six commits. All fetched branches and tags were included in the history check.
- Gitleaks v8.30.1 scanned the six commits: no secrets detected. Its official release archive was verified against the publisher's SHA-256 checksum before use.
- No `.env` files, private keys, signing certificates, local engine settings, `.runtime`, project libraries, commercial source media or model weights were found in the published history's file inventory.
- Both published source ZIPs were checked independently and scanned with Gitleaks: no secrets or private project/configuration files detected.
- Both Windows EXEs' bundled-file inventories were checked. The `certifi/cacert.pem` file is the public CA certificate bundle used for HTTPS verification; it contains certificates, not private keys.
- Published PNG/JPEG metadata contained no detected prompts, workflows, comments, EXIF or private path records. Standard JPEG encoding metadata was excluded from privacy findings.
- A targeted search of historical text files found no references to the maintainer's Windows home directory.

Public contents are application code, dependencies and license notices, setup/build/test files, workflow graphs, model-source metadata, app logos/fonts/icons, 592 active preset thumbnails and three requested promotional images based on the app interface. The promotional images show the commercial project's name and generated character, as requested for the README.

Legacy image workflow graphs are also present in the existing catalog. They are not credentials or private projects; the running image-generation endpoint restricts generation to Qwen 2.1. This audit did not remove unrelated catalog compatibility code.

## Changes

The `.gitignore` was an ordinary exclusion-pattern file, not a secret store. It included patterns such as `.env` and `projects/`, not those files' contents. At the maintainer's request it is removed from the current public tree. Equivalent exclusions remain in the publisher checkout's private `.git/info/exclude`, and publishing continues through an explicit file allowlist.

Previous tags and commits were not rewritten: the old `.gitignore` contains only harmless exclusion patterns, and no exposed credential was detected that would justify destructive history rewriting. Earlier release source ZIPs did not contain it.

The regular EXE remains loopback-only by default. A separately requested Tailscale launcher binds to the detected Tailscale IPv4 address on port 7860. The app has no separate login: peers permitted by the tailnet's access rules can use its interface. No public-internet exposure, firewall modifications or Tailscale Funnel were enabled by that launcher.

The rc.4 source package and publication changes receive an additional scan before release. Scan output and machine-specific working files remain outside the public source allowlist.

Tool: [Gitleaks](https://github.com/gitleaks/gitleaks). Reports are retained privately by the maintainer.
