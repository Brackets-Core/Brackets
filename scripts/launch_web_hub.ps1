<#
.SYNOPSIS
    Lanzador único de Brackets Web Hub para Windows (sin consola visible).

.DESCRIPTION
    Comprueba si el servidor local ya está escuchando en `127.0.0.1:8080`:
    - Si NO está activo: arranca `run_brackets.py --web` en segundo plano (sin ventana de consola)
      y abre automáticamente la ventana de la PWA.
    - Si YA está activo: abre la ventana de la PWA directamente sin duplicar el servidor.

.PARAMETER Port
    Puerto del servidor local (por defecto 8080).

.PARAMETER HostAddr
    Dirección de escucha (por defecto 127.0.0.1).

.PARAMETER CreateShortcut
    Crea un acceso directo "Brackets Web Hub.lnk" en el Menú Inicio (o Escritorio).

.PARAMETER ShortcutLocation
    Ubicación del acceso directo al usar -CreateShortcut: StartMenu (defecto), Desktop o Both.
#>
[CmdletBinding()]
param(
    [int]$Port = 8080,
    [string]$HostAddr = "127.0.0.1",
    [switch]$CreateShortcut,
    [ValidateSet("StartMenu", "Desktop", "Both")]
    [string]$ShortcutLocation = "StartMenu"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot

function Resolve-PythonExecutable {
    param([string]$Root)
    $candidates = @(
        (Join-Path $Root ".venv\Scripts\python.exe"),
        (Join-Path $Root ".venv\Scripts\pythonw.exe")
    )
    foreach ($cand in $candidates) {
        if (Test-Path $cand) {
            return $cand
        }
    }
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $cmdW = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($cmdW) { return $cmdW.Source }
    throw "No se encontró Python (.venv ni en PATH)."
}

if ($CreateShortcut) {
    $scriptPath = $MyInvocation.MyCommand.Path
    $targets = @()
    if ($ShortcutLocation -in @("StartMenu", "Both")) {
        $targets += [Environment]::GetFolderPath("Programs")
    }
    if ($ShortcutLocation -in @("Desktop", "Both")) {
        $targets += [Environment]::GetFolderPath("Desktop")
    }

    $shell = New-Object -ComObject WScript.Shell
    foreach ($dir in $targets) {
        $shortcutPath = Join-Path $dir "Brackets Web Hub.lnk"
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = "powershell.exe"
        $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`" -Port $Port -HostAddr $HostAddr"
        $shortcut.WorkingDirectory = $RepoRoot
        $shortcut.WindowStyle = 7  # Minimizado / oculto
        $shortcut.Description = "Iniciar Brackets Web Hub (servidor + PWA)"
        $shortcut.Save()
        Write-Host "Acceso directo creado en: $shortcutPath" -ForegroundColor Green
    }
    return
}

function Test-PortListening {
    param([string]$TargetHost, [int]$TargetPort)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $iar = $client.BeginConnect($TargetHost, $TargetPort, $null, $null)
        $connected = $iar.AsyncWaitHandle.WaitOne(250, $false)
        if ($connected -and $client.Connected) {
            $client.EndConnect($iar)
            return $true
        }
        return $false
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

$pythonExe = Resolve-PythonExecutable -Root $RepoRoot
$url = "http://${HostAddr}:${Port}"

if (Test-PortListening -TargetHost $HostAddr -TargetPort $Port) {
    # Servidor ya activo: abrir únicamente la ventana de la app
    $pyCode = "import webbrowser; from web.server import open_in_app_mode; url='$url'; open_in_app_mode(url) or webbrowser.open(url)"
    Start-Process -FilePath $pythonExe -ArgumentList @("-c", $pyCode) -WorkingDirectory $RepoRoot -WindowStyle Hidden
}
else {
    # Servidor apagado: arrancarlo en segundo plano (incluye apertura de app + GitSync)
    $launcher = Join-Path $RepoRoot "run_brackets.py"
    Start-Process -FilePath $pythonExe -ArgumentList @($launcher, "--web", "--port", "$Port") -WorkingDirectory $RepoRoot -WindowStyle Hidden
}
