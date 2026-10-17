param(
    [string]$CacheDirectory = '',
    [string]$OutputDirectory = '',
    [string]$BoostRoot = 'D:\NewProgram\librime-rs\target\regex-oracle-cache\boost_1_89_0'
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
if (-not $CacheDirectory) { $CacheDirectory = Join-Path $repo 'target/research/icu-probe/reference' }
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $repo 'target/research/icu-probe/empty-keys' }
$CacheDirectory = [IO.Path]::GetFullPath($CacheDirectory)
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$asset = 'icu4c-77_1-Win64-MSVC2022.zip'
$archive = Join-Path $CacheDirectory $asset
$hashManifest = Join-Path $CacheDirectory 'SHASUM512.txt'
$icu = Join-Path $CacheDirectory 'icu77'
foreach ($required in @($archive, $hashManifest, (Join-Path $icu 'include/unicode/utypes.h'))) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Reference cache missing: $required. Run reference/run.ps1 first." }
}
$hashLine = @(Get-Content -LiteralPath $hashManifest | Where-Object { $_ -match "\s+\*?$([regex]::Escape($asset))$" })
if ($hashLine.Count -ne 1) { throw 'Cannot identify one official archive hash' }
$archiveHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA512).Hash.ToLowerInvariant()
if ($archiveHash -ne ($hashLine[0] -split '\s+')[0]) { throw 'ICU archive SHA512 mismatch' }
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'MSVC x64 tools not found' }
& (Join-Path $vs 'Common7/Tools/Launch-VsDevShell.ps1') -Arch amd64 -HostArch amd64 -SkipAutomaticLocation | Out-Null
$source = Join-Path $PSScriptRoot 'empty-keys.cpp'
$exe = Join-Path $OutputDirectory 'empty-keys.exe'
$buildLog = Join-Path $OutputDirectory 'build.log'
$arguments = @('/nologo', '/std:c++17', '/EHsc', '/O2', '/MD', '/utf-8', "/I$(Join-Path $icu 'include')", $source, "/Fo$(Join-Path $OutputDirectory 'empty-keys.obj')", "/Fd$(Join-Path $OutputDirectory 'empty-keys.pdb')", "/Fe$exe", '/link', "/LIBPATH:$(Join-Path $icu 'lib64')", 'icuuc.lib', 'icuin.lib', 'icudt.lib')
& cl.exe @arguments *> $buildLog
if ($LASTEXITCODE -ne 0) { throw "Compilation failed; see $buildLog" }
$start = [Diagnostics.ProcessStartInfo]::new($exe)
$start.UseShellExecute = $false
$start.RedirectStandardOutput = $true
$start.RedirectStandardError = $true
$start.Environment['PATH'] = (Join-Path $icu 'bin64') + [IO.Path]::PathSeparator + $env:PATH
$start.ArgumentList.Add($OutputDirectory)
$process = [Diagnostics.Process]::Start($start)
$stdout = $process.StandardOutput.ReadToEndAsync()
$stderr = $process.StandardError.ReadToEndAsync()
$process.WaitForExit()
$stdout.Result | Set-Content -LiteralPath (Join-Path $OutputDirectory 'stdout.log') -Encoding UTF8
$stderr.Result | Set-Content -LiteralPath (Join-Path $OutputDirectory 'stderr.log') -Encoding UTF8
if ($process.ExitCode -ne 0) { throw "Empty-key expected-value export failed: $($process.ExitCode)" }
$dlls = @('icuuc77.dll', 'icuin77.dll', 'icudt77.dll') | ForEach-Object { Join-Path $icu "bin64/$_" }
$files = @($source, $PSCommandPath, $exe, $archive, $hashManifest, (Join-Path $BoostRoot 'boost/regex/v5/icu.hpp')) + $dlls
$files += @(Get-ChildItem -LiteralPath $OutputDirectory -File | Where-Object { $_.Name -notin @('manifest.json', 'empty-keys.exe') } | Select-Object -ExpandProperty FullName)
$manifest = [ordered]@{
    purpose = 'Expected values for approved empty-input compatibility exception; not a Rust implementation pass'
    original_boost_reference_modified = $false
    input = 'Valid UTF-16 sentinel pointer with explicit length 0'
    boost_wrapper_rule = 'Strip one trailing zero only if length > 1; promote each remaining byte to u32'
    release_url = 'https://github.com/unicode-org/icu/releases/tag/release-77-1'
    asset_url = "https://github.com/unicode-org/icu/releases/download/release-77-1/$asset"
    archive_sha512 = $archiveHash
    official_manifest_sha512_match = $true
    signatures_verified = $false
    generated_utc = [DateTime]::UtcNow.ToString('o')
    os = [Runtime.InteropServices.RuntimeInformation]::OSDescription
    architecture = [Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture.ToString()
    files = @($files | ForEach-Object { [ordered]@{ path = $_; bytes = (Get-Item -LiteralPath $_).Length; sha256 = (Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLowerInvariant() } })
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'manifest.json') -Encoding UTF8
Write-Output $stdout.Result
Write-Output "Empty-key expectations: $OutputDirectory"
