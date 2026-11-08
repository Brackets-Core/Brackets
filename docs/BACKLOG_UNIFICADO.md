# Backlog Unificado Brackets

Fecha de consolidacion: 2026-05-24

Este backlog centraliza funcionalidades de producto detectadas en:
- SharedContext/MENU_AUDIT_REPORT.md
- brackets/docs/PROPOSITO_ESTRUCTURA_MENU.md
- brackets/docs/pomodoro_spec_v1.md
- brackets/docs/pomodoro_implementation_report.md
- MyJobNotes/[📋PROJECTS][🗃️BRACKETS][📋PLANIFICACION]✅BackLog.md
- MyJobNotes/[📋PROJECTS][🗃️BRACKETS][📋PLANIFICACION]Roadmap.md
- MyJobNotes/[📋PROJECTS][🗃️BRACKETS][📋PLANIFICACION]Main.md
- SharedContext/WORKSTYLE_SYSTEM_SUGGESTIONS.md
- brackets/HANDOFF_PROMPT_CONTEXT_2026-02-22.md

## Paquete de continuidad para nuevo agente

- docs/HANDOFF_AGENTE_SIGUIENTE.md
- docs/PLAN_YAML_RELACIONAL.md

## Kanban continuo (activo desde 2026-05-24)

Modelo operativo:
- Fuente unica: este backlog.
- Estados: `Ideas` -> `Priorizado` -> `En ejecucion` -> `Verificado`.
- Limite WIP: 1 bloque principal simultaneo.
- Checkpoint: revisar y reordenar cada 3-4 movimientos de estado.

Bloque activo (WIP principal):
- [Verificado] Fallback automatico a flujo manual cuando no existen bitacoras previas.

Cola inmediata priorizada:
- [Verificado] Restringir visibilidad de vaults: desde `run_brackets.py` local mostrar solo el vault local; el root mantiene vista global.
- [Verificado] Definir y aplicar una politica unica de versionado (README/setup/modulos internos).

## Implementado

- [x] Desacoplamiento de menu principal y submenus a configuracion YAML.
- [x] Motor de menu reutilizable con `context_tag`, quick-keys y validacion de conflictos de teclas.
- [x] Navegacion de menu sin Enter para seleccion por quick-key.
- [x] Navegacion por flechas (arriba/abajo) + Enter en menus YAML.
- [x] Script de arranque rapido en `C:/Projects/brackets_quickstart.ps1` que activa venv y lo desactiva al finalizar.
- [x] Integracion de Pomodoro v1 en modo standalone y desde el menu/CLI (`--timer`).
- [x] Reporte de implementacion Pomodoro con trazabilidad a spec y criterios de aceptacion PASS.
- [x] VaultManager con selector de vaults, creacion de vault y flujo de entrada interactivo.
- [x] Configuracion viva de patron laboral, festivos y vacaciones en menu de configuracion.
- [x] Separacion fisica core/vault (repo `brackets` desacoplado de vaults).
- [x] Motor de Base de Datos Relacional YAML-first (`data/tables/`) con proyectos, topics, tareas, notas, definiciones y recurrencias.
- [x] Sincronización Bidireccional Markdown ➔ YAML (`MarkdownSyncService`) y renderizador unificado (`BitacoraRenderer`).
- [x] Hub Diario interactivo (Opción B) con dashboard en vivo, subpantallas temáticas (`[t]`, `[n]`, `[p]`, `[d]`, `[8]`) y footer limpio.
- [x] Entidad `Topic` y jerarquía relacional `Proyecto ➔ Topic ➔ Tarea / Nota` con herencia automática de atributos.
- [x] Sección `## 📋Week Tasks` en bitácoras para tareas semanales sin día fijo y ciclo de vida de rollover con regla de 2 semanas hacia el Backlog del Proyecto.
- [x] Motor de Tareas y Reuniones Recurrentes (`RecurringTask`) para días fijos (L-X-V) e intervalos de semanas (cada 4 semanas) con inyección automática e idempotente.
- [x] Controlador y vista de Backlog de Proyectos (`ProjectBacklogController`).

## Alta prioridad

- [x] Corregir traspaso de tareas entre semanas para no migrar tareas tachadas `[x]` y respetar jerarquias (incluye no migrar subtareas de padre completado).
- [x] Si no hay bitacoras previas, que la opcion "Crear bitacora semanal" redirija automaticamente al flujo manual.
- [x] Corregir formato del titulo de `MonthTopics` (ejemplo esperado: `# July Topics ☀️`).
- [x] Definir y aplicar una politica unica de versionado (README/setup/modulos internos).
- [x] Restringir visibilidad de vaults: desde `run_brackets.py` local mostrar solo el vault local; el root mantiene vista global.

## Prioridad media

- [x] Menu por tipo de vault (work/personal) con reglas de visibilidad mas finas (implementado con `context_tag: vault_type_work` / `vault_type_personal`).
- [x] Inyeccion de contexto vivo en dashboard principal (implementado en `DailyHubController`: semana actual, tareas del dia, notas semanales, proyectos vinculados).
- [x] Limpieza de pausas no esenciales en la navegacion de menus (quick-keys + flechas + Enter).
- [ ] Añadir smoke test unico para validar vault nuevo en un comando.
- [ ] Crear `MULTIROOT_WORKFLOW.md`.
- [x] Corregir rutas desactualizadas en README de `test-vault` (obsoleto: el repo `test-vault` ya no esta presente en el workspace actual).
- [ ] Modularizar aun mas `main.py` por responsabilidades.
- [ ] Modernizar empaquetado a `pyproject.toml`.

## Configuracion por vault y bitacoras

- [ ] Hacer configurable por vault el bloque de preguntas iniciales semanales (incluyendo peso/salud).
- [ ] Hacer configurable por vault la pregunta de ubicacion (casa/oficina/remoto).
- [ ] Hacer configurable por vault la duracion de semana (5 dias trabajo, 7 dias personal).
- [ ] Definir modo opcional sin dimension temporal (solo notas/proyectos, sin bitacoras semanales).
- [x] Crear opcion de ejecucion diaria para traspaso de tareas entre dias (implementado en `DailyHubController`: dashboard diario con cambio de dia activo).
- [x] Opcion interactiva para anadir tareas del dia en curso (implementado en `DailyHubController` acciones `[n]`, `[j]`).
- [x] Crear y usar archivo de tareas recurrentes (semanal/mensual/cuatrimestral) (implementado en `data/tables/recurring_tasks.yaml`).

## Modulos funcionales futuros

- [ ] Sistema de tipos de entrada por documento (Topic, Note, Task, Def) con orden configurable.
- [ ] Asistente "siempre escuchando" para crear entradas en dia correcto y en cualquier vault.
- [x] Crear categoria de tareas programadas y lista de tareas recurrentes autoinsertadas cada semana (implementado con `RecurringTask` y `apply_recurring_tasks`).
- [ ] Posibilidad de cuentas atras para eventos al inicio de semana.
- [ ] Consulta de prevision meteorologica semanal.
- [ ] Plantilla editable de bitacora semanal con secciones predefinidas.
- [ ] Crear apartado mensual de resumen del mes anterior por semanas.
- [ ] Potenciar sistema de links cruzados entre documentos para navegacion de agentes.

## Nuevas ideas agrupadas por tema (verificadas)

### CLI y punto de entrada

- [x] Brackets estilo CLI (ya existe CLI con `argparse` y entrypoint por `brackets.main`).
- [x] Poner un ejecutable en `C:/Projects/` (existente: `C:/Projects/brackets_quickstart.ps1`).
- [ ] Pensar opciones generales para directorio `Projects` (config global, defaults y comandos de entorno).

### Servicio residente y ejecucion continua

- [ ] Pasarlo a un servicio que arranque solo siempre (Windows Service / Task Scheduler).
- [ ] Que siempre este escuchando (modo daemon/watcher con canal de comandos).

### Tiempo, tareas y bitacora automatica

- [ ] Medicion del tiempo con asignacion de tarea (PARCIAL: hay timer, falta asignacion formal a task-id).
- [ ] Edicion automatica de Bitacora basada en eventos de trabajo.
- [x] Gestion de tareas por codigo (task-id unico, estado, prioridad y relaciones) — implementado via `EntityManager` con IDs estables `TSK-XXXX`, estados `pending/done/cancelled`, y `project_id` como relacion.

### Motor de documentos y render

- [x] Modulo de renderizado de `.md` para aplicar cambios estructurados en archivos — implementado en `BitacoraRenderer`.
- [x] Que `.md` sea solo render de un estado interno (modelo de datos como fuente de verdad) — implementado: YAML es fuente de verdad, `.md` se regenera desde `WeekSchedule` + `EntityManager`.

### IA y resumenes

- [ ] Usar modulo de IA para crear resumenes.
- [ ] Gestion de API Key (segura) para integracion IA.

## Vision de mediano/largo plazo (Roadmap)

- [x] Fase 4: Modulo de proyectos (estructura, hitos, reporteria, integracion con bitacoras) — implementado en `entities.py:Project`, `EntityManager.ensure_project()`, `prompt_project_selection()`.
- [ ] Fase 5: Modulo de aprendizaje (notas estructuradas, busqueda, resumenes).
- [ ] Fase 6: Automatizacion avanzada (predicciones de tareas, analisis de productividad).
- [ ] Fase 7: Mejoras de interfaz (dashboard enriquecido y posibles exportaciones).
- [x] Fase 8: YAML-first como persistencia estructurada con modelos y generacion YAML -> Markdown — implementado en `EntityManager`, `BitacoraRenderer`, `entities.py`.

## Notas de estado

- La parte de menu quedo funcionalmente adelantada respecto a los checkboxes antiguos de auditoria.
- Se recomienda usar este archivo como unica fuente de backlog funcional y mantener los demas docs como historico/contexto.

## Auditoria tecnica de pendientes

Ultima auditoria: 2026-08-23

- ✅ Traspaso de tareas entre semanas: resuelto y validado en parser/tests (no migra `[x]` ni subtareas de padre completado).
- ✅ Fallback automatico a flujo manual sin bitacoras previas: resuelto en `WeeklyGenerator.create_next_or_manual_weekly_bitacora` + `BitacoraManager.handle_weekly_creation`, validado con `brackets/tests/test_generators_weekly.py`.
- ✅ Titulo `MonthTopics`: resuelto con formato `# {MonthName} Topics {emoji}` en `ContentGenerator.create_monthly_topics`; validado con `brackets/tests/test_utils_content_generator.py`.
- ✅ Politica unica de versionado: resuelto con fuente unica en `brackets/version.py`, integrada en `setup.py`, `brackets.__version__` y `config.VERSION`; validado con `brackets/tests/test_version_policy.py`.
- ✅ Visibilidad de vault local vs root: resuelto en `resolve_workspace_context` y flujo de `main`, con tests en `brackets/tests/test_cli_vault_scope.py`.
- ✅ Limpieza de modelo de datos: eliminados campos fantasma (`definition_ids`, `parent_id`, `tags`, `project_ref`, contadores de `Project`, `Definition.project_id`). Eliminada escritura dual de notas. Validado con 118 tests al 100%.
- ✅ Limpieza de codigo muerto: eliminadas ~186 LOC de metodos, clases y funciones sin uso. Eliminado test legado roto `test_week_calculation.py`.
- ✅ Consolidacion de test suite: registrados 4 tests excluidos (`file_rename_manager`, `global_search_replace`, `manual_creation`, `pomodoro_timer`). Suite completa: 118 tests.
- ✅ Correccion de bugs: fix `datetime` en `main.py`, fix `render_dashboard` duplicado, fix indexacion en `run_analyze_file`, fix regex duplicado en renderer.

Regla para marcar una tarea como resuelta:

- Debe existir evidencia en codigo (archivo/metodo) y una verificacion ejecutable (test o comando reproducible).


- [ ] **Pomodoro Flotante en PWA (Web Hub)**: Al trabajar en una tarea, abrir temporizador Pomodoro flotante con fondo desenfocado (`backdrop-filter: blur`) y tracking de sesión.
