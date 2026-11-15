---
name: bitacora-ops
description: >-
  Use this skill when the user asks to log completed work, create pending or done
  tasks, add notes or topics, update daily work locations, or synchronize weekly
  Markdown bitacoras and YAML tables in any Brackets vault (such as MyJobNotes
  or MyPersonalNotes).
---

# Bitácora & Vault Operations (`bitacora-ops`)

Runbook para operar sobre bitácoras semanales y entidades de cualquier vault sin romper la sincronización bidireccional `Markdown ↔ YAML`.

## Reglas Inquebrantables

1. **Nunca edites `.md` y YAML por separado a mano:** Si tocas el `.md`, debes sincronizar hacia YAML; mejor aún, usa `BracketsWebService` (que absorbe cambios previos del `.md`, muta el YAML y re-renderiza el `.md` atómicamente).
2. **Respeta el catálogo declarativo del vault:** Consulta `data/task_types.yaml` del vault destino antes de inventar premojis o prefijos, y `data/tables/projects.yaml` para usar códigos `#[PROYECTO]` existentes cuando encajen.
3. **Cero código en el vault:** Jamás crees scripts temporales dentro de un vault.

---

## Procedimiento 1: Registrar tareas o trabajo ya realizado (Recomendado)

Usa `BracketsWebService` desde Python (funciona en frío sin necesidad de que el servidor HTTP esté encendido):

```python
import sys
sys.path.insert(0, r"C:\Projects\Brackets")
from web.service import BracketsWebService

svc = BracketsWebService(workspace_root=r"C:\Projects\Brackets")

# Registrar trabajo ya resuelto (is_done=True) o tarea pendiente (is_done=False)
res = svc.create_task(
    vault_identifier="MyJobNotes",          # o "MyPersonalNotes" o ruta externa
    title="🫱🏼‍🫲🏽 Revisión de API #[BRACKETS]", # detecta premoji/prefijo y tag #[PROYECTO]
    target="today",                         # "today", "week" o "day:15"
    is_done=True,                           # True = [x] completada, False = [ ] pendiente
    description="Detalle opcional bajo la tarea.",
)
print(res["created_task"])
```

---

## Validación Obligatoria

- Comprueba que la tarea/nota aparece tanto en el archivo `[YYYY][MM]WeekXX.md` del vault como en `data/tables/tasks.yaml` (o `notes/`) y `data/weeks/YYYY-WXX.yaml`.
- Verifica con `git diff` en el repositorio del vault correspondiente que no se han perdido ni duplicado líneas previas de la semana.
