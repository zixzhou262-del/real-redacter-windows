param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$AppName = "ReaL Redacter"
$Version = "2.2.2"
$VenvDir = Join-Path $RootDir ".venv-windows"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
$DistDir = Join-Path $RootDir "dist"
$AppDir = Join-Path $DistDir $AppName
$ReleaseDir = Join-Path $RootDir "release"
$ZipPath = Join-Path $ReleaseDir "$AppName-$Version-windows-x64.zip"

Set-Location $RootDir

function Get-SystemPython {
    $candidates = @(
        @{ Command = "py"; Args = @("-3.12") },
        @{ Command = "py"; Args = @("-3.11") },
        @{ Command = "py"; Args = @("-3") },
        @{ Command = "python"; Args = @() },
        @{ Command = "python3"; Args = @() }
    )

    foreach ($candidate in $candidates) {
        $command = Get-Command $candidate.Command -ErrorAction SilentlyContinue
        if (-not $command) {
            continue
        }

        $args = @($candidate.Args)
        try {
            & $command.Source @args -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" *> $null
            if ($LASTEXITCODE -eq 0) {
                return [pscustomobject]@{
                    Command = $command.Source
                    Args = $args
                }
            }
        } catch {
            continue
        }
    }

    return $null
}

function Invoke-SystemPython {
    param(
        [pscustomobject]$Python,
        [string[]]$Arguments
    )
    $baseArgs = @($Python.Args)
    & $Python.Command @baseArgs @Arguments
}

if (-not (Test-Path $PythonExe)) {
    Write-Host "Creating local Python environment..."
    $SystemPython = Get-SystemPython
    if (-not $SystemPython) {
        Write-Host ""
        Write-Host "Python 3.11 or newer was not found on this Windows computer."
        Write-Host "Please install Python 3.12 from:"
        Write-Host "https://www.python.org/downloads/windows/"
        Write-Host ""
        Write-Host "Important: during installation, select 'Add python.exe to PATH'."
        exit 1
    }
    Invoke-SystemPython -Python $SystemPython -Arguments @("-m", "venv", $VenvDir)
}

if (-not $SkipInstall) {
    & $PythonExe -m pip install --upgrade pip
    & $PythonExe -m pip install -e ".[gui]" pyinstaller
}

& $PythonExe -m PyInstaller "build\offline_anonymizer_windows.spec" --noconfirm --clean

if (-not (Test-Path $AppDir)) {
    throw "打包失败，未找到输出目录：$AppDir"
}

$ExePath = Join-Path $AppDir "$AppName.exe"
if (-not (Test-Path $ExePath)) {
    throw "打包失败，未找到主程序：$ExePath"
}

& $ExePath --self-check

if (-not (Test-Path $ReleaseDir)) {
    New-Item -ItemType Directory -Path $ReleaseDir | Out-Null
}

if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}

Compress-Archive -Path $AppDir -DestinationPath $ZipPath -CompressionLevel Optimal

Write-Host "Windows package created: $ZipPath"
