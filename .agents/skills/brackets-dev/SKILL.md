---
name: brackets-dev
description: >-
  Use this skill when designing, implementing, refactoring, or testing features
  in the Brackets Python engine, including CLI controllers, YAML models,
  Markdown parsers/renderers, Pomodoro modules, or the PWA Web Hub and REST API.
---

# Brackets Engine Development (`brackets-dev`)

Protocolo de ingeniería modular ("Filosofía Lego") para evolucionar el motor `Brackets/` manteniendo compatibilidad multi-vault y cobertura de tests al 100%.

## Checklist de Diseño (Antes de tocar código)

1. **YAML antes que Python:** ¿El nuevo comportamiento (tipos de tarea, emojis, opciones de menú, festivos, flags) puede declararse en `config.yaml`, `task_types.yaml`, `menu_config.yaml` o `work_calendar.yaml`? Si es así, configúralo en YAML + `data/templates/`, nunca hardcodeado.
2. **Agnóstico al tipo y ruta del vault:**
   - No asumas semanas de 5 días: consulta `vault_type` (`work` = 5 días, `personal` = 7 días) y `days_per_week`.
   - No asumas rutas fijas: resuelve siempre mediante `VaultManager` (`--vault`, `BRACKETS_VAULT`, `vaults.yaml` o autodescubrimiento de carpetas hermanas `../`).
   - Jamás escribas ni esperes código Python dentro de un vault.
3. **Simetría Bidireccional (`MD ↔ YAML`):**
   - Si añades un campo o sintaxis nueva en entidades (`models/entities.py`), actualiza **ambos sentidos**:
     - Parseo/absorción: `BitacoraMarkdownParser` y `MarkdownSyncService`.
     - Renderizado: `BitacoraRenderer`.
   - Verifica que `render -> sync -> render` sea idempotente.

---

## Reglas para Tests Unitarios

1. **Aislamiento total de los vaults reales:** Ningún test que cree o modifique tareas/semanas puede escribir sobre `MyJobNotes` ni `MyPersonalNotes`. Usa siempre `tempfile.TemporaryDirectory()`.
2. **Ubicación:** Todos los tests residen en `tests/test_*.py`.

---

## Validación Obligatoria

Ejecuta siempre la suite completa desde la raíz de `Brackets/` antes de dar cualquier cambio por terminado:

```powershell
Set-Location 'C:\Projects\Brackets'
python -m unittest discover -s tests
```

Todos los tests deben terminar en `OK` con código de salida `0`.
