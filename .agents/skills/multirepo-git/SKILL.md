---
name: multirepo-git
description: >-
  Use this skill when checking git status, reviewing diffs, staging, committing,
  linking remotes, or pushing changes across the independent Git repositories of
  Brackets (the Brackets engine repo and external vault repos like MyJobNotes
  and MyPersonalNotes).
---

# Multi-Repo Git Workflow (`multirepo-git`)

El ecosistema de Brackets está compuesto por **repositorios Git independientes** (sin anidamiento): el repositorio del sistema (`Brackets`) y cada uno de los vaults (`MyJobNotes`, `MyPersonalNotes`, etc.) ubicados fuera del motor.

## Mapa de Repositorios

| Ámbito | Ruta habitual | Visibilidad / Sensibilidad | Contenido permitido |
|---|---|---|---|
| **1. Sistema (`Brackets`)** | `C:\Projects\Brackets` | **Público (`CodeAndRes/Brackets`)** | Código Python plano (`core/`, `managers/`, `models/`, `web/`...), tests, datos mock, `AGENTS.md` y `.agents/skills/`. **CERO datos reales de trabajo o rutas privadas (`vaults.yaml` está ignorado en `.gitignore`).** |
| **2. Vault Trabajo** | `C:\Projects\MyJobNotes` (o ruta en `vaults.yaml`) | **Privado** | Bitácoras `.md`, `assets/` y base de datos `data/` del trabajo. **CERO archivos `.py`.** |
| **3. Vault Personal** | `C:\Projects\MyPersonalNotes` (o ruta en `vaults.yaml`) | **Privado** | Bitácoras `.md` y base de datos `data/` personal. **CERO archivos `.py`.** |

---

## Procedimiento Seguro de Commit / Push

1. **Inspeccionar los repositorios de un vistazo:**
   ```powershell
   foreach ($r in @("C:\Projects\Brackets", "C:\Projects\MyJobNotes", "C:\Projects\MyPersonalNotes")) {
       Write-Host "=== $r ==="
       if (Test-Path "$r/.git") { git -C $r status -s; git -C $r branch -vv }
   }
   ```

2. **Auditoría de privacidad antes de commitear en `Brackets`:**
   - Revisa `git -C C:\Projects\Brackets diff --staged` asegurándote de que no se cuelan tickets reales, nombres propios ni rutas personales fuera de mocks genéricos.
   - Verifica que `vaults.yaml` sigue ignorado en `.gitignore`.

3. **Commits atómicos y descriptivos por repo:**
   - Usa Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`).
   - Pide confirmación explícita al usuario antes de ejecutar `git push`.
