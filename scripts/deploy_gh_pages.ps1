<#
.SYNOPSIS
    Despliega los estáticos de la PWA Brackets Web Hub desde `web/static/` a la rama `gh-pages`.

.DESCRIPTION
    Automatiza el flujo descrito en docs/HANDOFF_PWA.md:
    1. Verifica que el repositorio esté en `main` (o rama origen) y sin cambios sin commitear.
    2. Valida que `CACHE_NAME` en `web/static/sw.js` sea distinto al publicado en `gh-pages:sw.js`.
    3. Copia los 8 archivos estáticos a una carpeta temporal.
    4. Cambia a `gh-pages`, limpia archivos residuales en la raíz y copia los nuevos estáticos.
    5. Crea el commit en `gh-pages` (y hace push solo si se indica `-Push`).
    6. Vuelve siempre a la rama original y elimina la carpeta temporal.

.PARAMETER Push
    Si se especifica, ejecuta `git push origin gh-pages` tras crear el commit.

.PARAMETER AllowSameCache
    Permite desplegar aunque `CACHE_NAME` en `sw.js` coincida con el de `gh-pages`.

.PARAMETER DryRun
    Valida precondiciones, compara `CACHE_NAME` y lista los archivos sin cambiar de rama ni commitear.
#>
[CmdletBinding()]
param(
    [switch]$Push,
    [switch]$AllowSameCache,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$StaticDir = Join-Path $RepoRoot "web\static"

$StaticAssets = @(
    "index.html",
    "style.css",
    "app.js",
    "github_adapter.js",
    "sw.js",
    "manifest.webmanifest",
    "icon-192.svg",
    "icon-512.svg"
)

function Get-SwCacheName {
    param([string]$Content)
    $match = [regex]::Match($Content, "CACHE_NAME\s*=\s*['""]([^'""]+)['""]")
    if (-not $match.Success) {
        return $null
    }
    return $match.Groups[1].Value
}

Push-Location $RepoRoot
try {
    # 1. Verificar estado limpio del working tree
    $dirty = git status --porcelain
    if ($dirty -and -not $DryRun) {
        throw "El repositorio tiene cambios sin commitear. Haz commit o stash antes de desplegar a gh-pages."
    }

    $OriginalBranch = (git rev-parse --abbrev-ref HEAD).Trim()
    if (-not $OriginalBranch) {
        throw "No se pudo determinar la rama actual."
    }

    # 2. Verificar que existen todos los estáticos esperados
    foreach ($asset in $StaticAssets) {
        $fullPath = Join-Path $StaticDir $asset
        if (-not (Test-Path $fullPath)) {
            throw "Falta el archivo estático requerido: $fullPath"
        }
    }

    # 3. Validar incremento de CACHE_NAME en sw.js
    $LocalSwContent = Get-Content -Path (Join-Path $StaticDir "sw.js") -Raw -Encoding UTF8
    $LocalCacheName = Get-SwCacheName -Content $LocalSwContent
    if (-not $LocalCacheName) {
        throw "No se pudo extraer CACHE_NAME de web/static/sw.js."
    }

    $GhPagesSwContent = git show "gh-pages:sw.js" 2>$null
    $GhPagesCacheName = if ($GhPagesSwContent) { Get-SwCacheName -Content ($GhPagesSwContent -join "`n") } else { $null }
    $GhPagesCacheDisplay = if ($GhPagesCacheName) { $GhPagesCacheName } else { "(no encontrado)" }

    Write-Host "Rama origen        : $OriginalBranch"
    Write-Host "CACHE_NAME local   : $LocalCacheName"
    Write-Host "CACHE_NAME gh-pages: $GhPagesCacheDisplay"

    if ($GhPagesCacheName -and ($LocalCacheName -eq $GhPagesCacheName) -and -not $AllowSameCache) {
        throw "CACHE_NAME ('$LocalCacheName') no se ha incrementado respecto a gh-pages ('$GhPagesCacheName'). Incrementa web/static/sw.js o usa -AllowSameCache."
    }

    if ($DryRun) {
        Write-Host "[DryRun] Validación completada. Archivos listos para copiar desde web/static/:" -ForegroundColor Cyan
        $StaticAssets | ForEach-Object { Write-Host "  - $_" }
        return
    }

    # 4. Copiar estáticos a carpeta temporal
    $TempStage = Join-Path ([System.IO.Path]::GetTempPath()) ("brackets_gh_pages_" + [System.Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $TempStage | Out-Null

    try {
        foreach ($asset in $StaticAssets) {
            Copy-Item -Path (Join-Path $StaticDir $asset) -Destination (Join-Path $TempStage $asset) -Force
        }

        # 5. Cambiar a gh-pages y sincronizar raíz limpia
        git checkout gh-pages
        if ($LASTEXITCODE -ne 0) {
            throw "Error al cambiar a la rama gh-pages."
        }

        # Eliminar solo archivos trackeados en gh-pages que no formen parte de los estáticos
        # (preserva archivos locales ignorados como .venv/ o vaults.yaml)
        $trackedFiles = git ls-files
        foreach ($tracked in $trackedFiles) {
            if ($StaticAssets -notcontains $tracked) {
                $trackedPath = Join-Path $RepoRoot $tracked
                if (Test-Path $trackedPath) {
                    Remove-Item -Path $trackedPath -Force
                }
            }
        }

        foreach ($asset in $StaticAssets) {
            Copy-Item -Path (Join-Path $TempStage $asset) -Destination (Join-Path $RepoRoot $asset) -Force
        }

        # Actualizar borrados de archivos trackeados y añadir solo los estáticos de la PWA
        git add -u
        git add -- @StaticAssets
        $staged = git status --porcelain
        if (-not $staged) {
            Write-Host "No hay cambios respecto a gh-pages." -ForegroundColor Yellow
        }
        else {
            git commit -m "chore(pwa): deploy $LocalCacheName to gh-pages"
            if ($LASTEXITCODE -ne 0) {
                throw "Error al crear el commit en gh-pages."
            }
            Write-Host "Commit creado en gh-pages para $LocalCacheName." -ForegroundColor Green

            if ($Push) {
                git push origin gh-pages
                if ($LASTEXITCODE -ne 0) {
                    throw "Error al hacer push de gh-pages."
                }
                Write-Host "Push a origin/gh-pages completado." -ForegroundColor Green
            }
            else {
                Write-Host "Push omitido (ejecuta con -Push para publicar en origin/gh-pages)." -ForegroundColor Cyan
            }
        }
    }
    finally {
        if (Test-Path $TempStage) {
            Remove-Item -Path $TempStage -Recurse -Force -ErrorAction SilentlyContinue
        }
        $currentBranch = (git rev-parse --abbrev-ref HEAD).Trim()
        if ($currentBranch -ne $OriginalBranch) {
            git checkout $OriginalBranch | Out-Null
        }
    }
}
finally {
    Pop-Location
}
