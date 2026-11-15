# 🗃️ Brackets — Guía para Agentes de IA

> **Filosofía Lego:** "Si dudas cómo hacer algo... que se parezca a Lego."
> Cada pieza debe ser modular, encajable, intercambiable y configurable sin soldar.

Este archivo es leído automáticamente por los asistentes de IA (Antigravity/Gemini,
GitHub Copilot, Cursor, etc.) al inicio de cada conversación en el repositorio.
Su objetivo es transferir el conocimiento, las reglas y la filosofía del proyecto
para que cualquier sesión nueva parta del mismo nivel de contexto.

---

## 1. ¿Qué es Brackets?

Brackets es un **Sistema Operativo Personal de Productividad** basado en Python
que gestiona bitácoras de trabajo semanales en Markdown, con un Daily Hub
interactivo en consola (CLI), un Web Hub (PWA) y un modelo de datos relacional
persistido en YAML.

### Separación Motor / Contenido (Multi-Vault Desacoplado)

El sistema vive en un único repositorio plano (`Brackets/`) sin subcarpetas redundantes,
y los vaults son repositorios independientes ubicados fuera del motor (por ejemplo,
como carpetas hermanas en `C:\Projects\` o en cualquier ruta configurada en `vaults.yaml`):

```
C:\Projects\
├── Brackets/          ← Repositorio único del sistema (código Python plano, PWA, tests, skills IA)
│   ├── core/          ← Controladores (DailyHub, Config, Startup, Sync...)
│   ├── generators/    ← Generadores de bitácoras y renderizadores
│   ├── managers/      ← EntityManager, MarkdownSyncService, SettingsManager, VaultManager
│   ├── models/        ← Entidades (Task, Note, Topic...) y TaskTypeRegistry
│   ├── modules/       ← Extensiones (Pomodoro, futuros módulos)
│   ├── web/           ← Servidor HTTP y PWA Web Hub
│   ├── utils/         ← Parsers, helpers, file finders
│   ├── tests/         ← Suite de tests unitarios
│   ├── data/          ← Plantillas base para vaults y datos mock para tests
│   ├── .agents/skills/← Skills modulares para asistentes de IA
│   ├── main.py        ← Punto de entrada CLI
│   ├── run_brackets.py← Launcher principal (`python run_brackets.py`)
│   ├── vaults.yaml    ← Registro local de vaults (ignorado por Git, configurable por equipo)
│   └── AGENTS.md      ← Este archivo
│
├── MyJobNotes/        ← Vault activo de trabajo (repositorio Git privado independiente)
│   ├── data/          ← Base de datos YAML del vault (config, calendar, task_types, tables, weeks)
│   └── [YYYY][MM]WeekXX.md ← Bitácoras semanales
│
└── MyPersonalNotes/   ← Vault personal (repositorio Git privado independiente)
```

**Regla fundamental:** Los vaults son depósitos puros de información (Markdown y YAML).
NUNCA debe haber código Python dentro de un vault. El motor (`Brackets/`) se ejecuta
siempre desde su propia raíz con `python run_brackets.py` (con `--vault <nombre_o_ruta>`,
`$env:BRACKETS_VAULT` o seleccionándolo en el menú interactivo).

---

## 2. Regla de Oro: Configuración antes que Código

> **Prioridad absoluta:** Si un comportamiento puede definirse en un archivo YAML
> de configuración, DEBE hacerse ahí y NO hardcodearse en Python.

### Archivos de configuración del vault (`data/`)

| Archivo | Propósito |
|---------|-----------|
| `config.yaml` | Configuración general: vault_type, feature_flags, paths, proyectos activos |
| `work_calendar.yaml` | Calendario laboral: festivos, vacaciones, cierres, jornadas intensivas, patrón de ubicación |
| `task_types.yaml` | **Tipos de tareas y premojis** (meeting→🫱🏼‍🫲🏽, bug→🐛, etc.) — extensible sin código |
| `menu_config.yaml` | Estructura declarativa del menú CLI (ítems, atajos, acciones, contextos) |
| `tables/tasks.yaml` | Todas las tareas con id, título limpio, status, task_type, proyecto, fechas |
| `tables/recurring_tasks.yaml` | Definiciones de tareas recurrentes (días, intervalos, tipo) |
| `weeks/YYYY-WXX.yaml` | Programación semanal: días, task_ids por día, week_task_ids, topic_ids |

---

## 3. Modelo de Datos Relacional (YAML-First)

### Entidades principales

```
Task          → id: TSK-XXXX, title, status, task_type, project_id, topic_id, recurring_id
Note          → id: NOTE-XXXX, title, content[], project_id
Topic         → id: TOP-XXXX, title, project_id
Definition    → id: [🎫TICKET], url (enlaces Jira, docs, etc.)
RecurringTask → id: REC-XXXX, title, task_type, recurrence_type, weekdays[], active
WeekSchedule  → year, week_number, days[], week_task_ids[], topic_ids[], note_ids[]
DaySchedule   → day_number, location_emoji, location_note, task_ids[]
Person        → handle (@NombreApellido), first_seen
```

### Sincronización Bidireccional

```
Markdown (.md)  ←→  YAML (tasks.yaml, weeks/)
                ↕
       Daily Hub CLI / Web Hub
```

- **Markdown → YAML:** `MarkdownSyncService.sync_week_from_markdown()` parsea
  el `.md` y reconcilia con las entidades en YAML (crea, actualiza, elimina).
- **YAML → Markdown:** `BitacoraRenderer.render_and_save_week()` regenera
  el archivo `.md` desde los datos estructurados.
- **Idempotencia:** Ambas direcciones son idempotentes y preservan el estado.

---

## 4. Directrices para el Asistente de IA

### Prioridades al implementar cambios

1. **YAML antes que código:** Si se puede resolver con configuración, hazlo así.
2. **Modularidad Lego:** Cada pieza nueva debe ser independiente, encajable y
   reemplazable. Evita acoplamiento duro entre componentes.
3. **Preservar la bidireccionalidad:** Cualquier cambio en el modelo de datos
   debe funcionar tanto en dirección Markdown→YAML como YAML→Markdown.
4. **Tests obligatorios:** Todo cambio funcional debe acompañarse de tests
   unitarios. Ejecutar desde `Brackets/`: `python -m unittest discover -s tests`
5. **Preservar comentarios:** No eliminar docstrings ni comentarios existentes
   que no estén relacionados con el cambio.

### Cómo ejecutar los tests

```powershell
cd C:\Projects\Brackets
# Suite unittest estándar:
python -m unittest discover -s tests
# Suite completa con tests interactivos y legacy:
python -m tests.run_all_tests
```

### Archivos clave a consultar

| Necesidad | Archivo |
|-----------|---------|
| Punto de entrada principal | `main.py` / `run_brackets.py` |
| Coordinador desacoplado (BitacoraManager) | `core/bitacora_manager.py` |
| Entidades y modelos | `models/entities.py` |
| Tipos de tarea (registro) | `models/task_types.py` |
| Parser de Markdown y tags #[Project] | `utils/bitacora_parser.py` |
| Sincronización Markdown↔YAML | `managers/markdown_sync_service.py` |
| Renderizado de bitácoras | `generators/bitacora_renderer.py` |
| Daily Hub interactivo | `core/daily_hub_controller.py` |
| Backlog y métricas de proyectos | `core/project_backlog_controller.py` |
| Gestión de entidades | `managers/entity_manager.py` |
| Descubrimiento y registro de vaults | `managers/vault_manager.py` |
| Servicio Web Hub y API REST | `web/service.py` |
| Configuración de menús base | `data/menu_config.yaml` |
