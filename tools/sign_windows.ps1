[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$File,
    [string]$CertificateThumbprint,
    [string]$TimestampServer = 'http://timestamp.digicert.com',
    [switch]$VerifyOnly
)
$ErrorActionPreference = 'Stop'
$target = (Resolve-Path -LiteralPath $File).ProviderPath
if ([IO.Path]::GetExtension($target) -ne '.exe') { throw 'Only the built Windows EXE may be signed.' }

if (-not $VerifyOnly) {
    $thumbprint = ($CertificateThumbprint -replace '\s', '').ToUpperInvariant()
    if ($thumbprint -notmatch '^[0-9A-F]{40}$') { throw 'Provide an existing code-signing certificate thumbprint; no certificate is created automatically.' }
    $certificate = Get-Item -LiteralPath "Cert:\CurrentUser\My\$thumbprint"
    if (-not $certificate.HasPrivateKey) { throw 'The signing certificate has no accessible private key.' }
    if ($certificate.NotAfter -le (Get-Date) -or $certificate.NotBefore -gt (Get-Date)) { throw 'The signing certificate is not currently valid.' }
    if ($certificate.Subject -eq $certificate.Issuer) { throw 'Self-signed certificates are not accepted for public releases.' }
    $usages = @($certificate.Extensions | Where-Object { $_.Oid.Value -eq '2.5.29.37' } | ForEach-Object { $_.EnhancedKeyUsages } | ForEach-Object { $_.Value })
    if ($usages -notcontains '1.3.6.1.5.5.7.3.3') { throw 'The certificate must permit code signing.' }

    $signTool = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($signTool) { $toolPath = $signTool.Source }
    else {
        $sdkRoot = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'
        $tools = @(Get-ChildItem -Path "$sdkRoot\*\x64\signtool.exe" -File -ErrorAction SilentlyContinue | Sort-Object FullName -Descending)
        if (-not $tools.Count) { throw 'Install the Windows SDK Signing Tools (signtool.exe) first.' }
        $toolPath = $tools[0].FullName
    }
    & $toolPath sign /sha1 $thumbprint /s My /fd SHA256 /tr $TimestampServer /td SHA256 /d "Director's Cut" $target
    if ($LASTEXITCODE -ne 0) { throw "SignTool failed with exit code $LASTEXITCODE." }
}

$signature = Get-AuthenticodeSignature -LiteralPath $target
if ($signature.Status -ne 'Valid') { throw "Windows signature verification failed: $($signature.Status)." }
if (-not $signature.TimeStamperCertificate) { throw 'The release signature must have a trusted timestamp.' }
Write-Output "Valid timestamped Authenticode signature: $($signature.SignerCertificate.Subject)"
