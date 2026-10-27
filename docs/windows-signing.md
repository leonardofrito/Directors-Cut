# Windows signing

The published **0.1.0-rc.2 Windows EXE is unsigned**. Authenticode signing has not been completed, and the download has not been certified or approved by Microsoft. The release process now supports signing when a real signing identity is available.

## Why Windows shows a warning

Microsoft Defender SmartScreen considers publisher and file reputation. An unsigned new app may show “Windows protected your PC” or an unknown publisher. This does not identify the exact warning seen on a particular computer: Smart App Control, antivirus detections and administrator policies are separate cases.

A valid signature identifies the publisher and protects the file's integrity. It does **not** guarantee that a newly published file will immediately stop receiving SmartScreen warnings. Self-signed certificates do not solve public distribution trust; users should not be asked to install a project-made root certificate or disable Windows protection.

Download releases only from the [official repository](https://github.com/leonardofrito/Directors-Cut/releases) and compare against the published SHA256SUMS.txt. A checksum checks integrity, not publisher identity or absence of malware.

## Getting a signing identity

- **SignPath Foundation:** free signing for eligible open-source projects, subject to review and approval. [Apply](https://signpath.org/apply). This project has not applied or been approved. After approval, configure its service and GitHub build integration using the issued project/policy identifiers; the local certificate hook below does not itself integrate SignPath.
- **Certificate authority:** obtain a public code-signing certificate from a trusted provider, using its hardware token or HSM. Identity verification and fees depend on the provider. Configure its Windows certificate-store integration before using the local hook.
- **Microsoft Store MSIX:** the Store signs accepted MSIX packages after certification. An EXE uploaded to GitHub is not covered by Store signing; this project does not currently publish an MSIX package.

Microsoft's current eligibility table limits Azure Artifact Signing public-trust individual accounts to the USA and Canada. A developer in Brazil should verify current eligibility before paying for that service. Azure region availability is not the same as public-trust identity eligibility.

## Local signed build

Install Windows SDK Signing Tools and provision a trusted code-signing certificate with its private key accessible through `Cert:\CurrentUser\My`. Private keys should remain in the provider's token/HSM; no certificate, password or private key is stored in this repository.

In PowerShell, set the public certificate thumbprint and build:

```powershell
$env:DIRECTORSCUT_SIGNING_THUMBPRINT = 'YOUR_40_CHARACTER_CERTIFICATE_THUMBPRINT'
python tools/build_release.py --require-windows-signing
```

The build signs the completed Windows EXE using SHA-256 and an RFC 3161 SHA-256 timestamp. It verifies the Windows signature and timestamp **before** generating release ZIPs and checksums. Signing failures stop packaging. Without an identity, ordinary developer builds remain explicitly unsigned; release builds can require signing with the flag above.

Verify an already signed EXE without changing it:

```powershell
powershell -NoProfile -File tools/sign_windows.ps1 -File release/0.1.0-rc.2/DirectorsCut-0.1.0-rc.2-windows-x64.exe -VerifyOnly
```

The current unsigned release is expected to fail that check. For a cloud-signed EXE, place the returned signed file in the release directory, then run `python tools/build_release.py --source-only --require-windows-signing` on Windows to verify and regenerate archives/checksums without rebuilding or re-signing the executable. Publish the verified EXE and matching checksums together. Do not silently describe an unsigned download as signed.

No end-to-end signed build has been tested yet: a trusted signing identity is still required. The existing GitHub Actions workflow remains an unsigned candidate build; enabling a signing provider in CI is a separate configuration step.

Sources checked October 27, 2026:

- [Microsoft: SmartScreen reputation](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation)
- [Microsoft: signing options and regional eligibility](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options)
- [SignPath Foundation](https://signpath.org/)
