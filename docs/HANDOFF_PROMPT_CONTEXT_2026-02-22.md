# Handoff para nuevo prompt en `brackets`

Fecha: 2026-02-22
Objetivo: Retomar la reforma del sistema Brackets sin perder contexto.

## 1) Estado actual consolidado

- Arquitectura separada en dos repos:
  - `MyJobNotes` (vault/datos/notas)
  - `brackets` (core Python independiente)
- En `MyJobNotes` la rama activa es:
  - `PosibleSeparacionMyNotes&Brackets`
- En `brackets` la rama activa es:
  - `main`
- El core `brackets` ya está desacoplado y funcional como paquete.

## 2) Cambios recientes relevantes (historial)

### MyJobNotes (rama `PosibleSeparacionMyNotes&Brackets`)
- `e89f22f`: workspace config inicial para MyJobNotes
- `f8acfbd`: claridad en comentario de path del core en `run_brackets.py`
- `910dd9a`: eliminación de utilidades deprecadas y refactor de generación/parseo
- `725b027`: documentación + Week 9/10 + mejoras integración core
- `ed711ab`: modo opcional sin bitácoras y mejoras de configuración

### brackets (rama `main`)
- `7137938`: mejora README (badges, estructura, ejemplos)
- `9a7478c`: URL de repo en `setup.py`
- `bbb289d`: commit inicial del core independiente v3.0.0

## 3) Fuentes de verdad leídas

- Workspace root README: `brackets-workspace/README.md`
- Vault README: `MyJobNotes/README.md`
- Documentación BRACKETS en MyJobNotes:
  - `.../[📋PROJECTS][🗃️BRACKETS][🎨DOCUMENTACION]/Readme.md`
  - `.../Architecture.md`, `GuiaCreacion.md`, `GuiaRenombrado.md`, `Nomenclatura.md`, `SETUP.md`
  - `.../[📋PLANIFICACION]/Main.md`, `Roadmap.md`
  - `.../[📜HISTORIAL]/Changelog.md`, `Fase2.md`
- Backlog/ideas/todo:
  - `MyJobNotes/[📋PROJECTS]✅BackLog.md`
  - `MyJobNotes/[📋PROJECTS]🧩Tasks.md`
  - `MyJobNotes/[🧩GENERAL]ToDo.md`
  - `MyJobNotes/[🧩GENERAL]💡Insights.md`
  - `MyJobNotes/[🧩GENERAL]🧠Ideas.md`
- Repo core `brackets` leído completo (README, módulos `brackets/*`, tests).

## 4) Hallazgos técnicos importantes

- Hay desalineación de versiones entre docs/paquete/módulos:
  - `setup.py` y README hablan de `3.0.0`
  - `brackets/config.py` y `brackets/__init__.py` mantienen `2.0.0`
- `main.py` es el orquestador con menús ampliados:
  - generación, consolidación, categorías, búsqueda/reemplazo, sync YAML, configuración viva.
- `SettingsManager` ya implementa:
  - patrón laboral editable
  - festivos y vacaciones persistidos en `data/work_calendar.yaml`
- `FileRenameManager` evolucionó a búsqueda/reemplazo global con dry-run + estadísticas.
- Hay señales de deuda técnica/inconsistencias en tests vs APIs actuales en algunos scripts legacy.

## 5) Reforma en curso (qué parece estar activo)

Prioridades recurrentes detectadas en docs y TODO:
1. Mejorar traspaso de tareas entre semanas:
   - no pasar tareas tachadas
   - respetar mejor subtareas jerárquicas
2. Corregir formato de título de `MonthTopics` (ejemplo esperado: `# July Topics ☀️`)
3. Consolidar modo opcional “sin dimensión temporal” (solo notas/proyectos)
4. Reforzar configuración de tareas recurrentes + festivos/vacaciones
5. Mantener separación limpia core/vault y flujo multi-vault

## 6) Prompt sugerido para arrancar en `brackets`

Usa este bloque como primer mensaje en el nuevo chat:

---
Quiero retomar la reforma de Brackets con este contexto de handoff (2026-02-22).

Trabaja sobre el repo `brackets` (core), manteniendo compatibilidad con vaults externos como MyJobNotes.

Objetivo inmediato (ordenado):
1) Diagnosticar y corregir traspaso de tareas semanales para que NO migre tareas `[x]` y respete mejor jerarquías/subtareas.
2) Corregir formato del título de `MonthTopics` según especificación actual.
3) Validar coherencia de versiones (README/setup vs módulos internos) y proponer ajuste mínimo.
4) Ejecutar y/o ajustar tests afectados por los cambios realizados (sin arreglar issues no relacionados).

Antes de editar, muestra un plan corto y los archivos exactos a tocar.
Después de editar, resume: cambios, validación, riesgos pendientes.
---

## 7) Riesgos/decisiones pendientes

- Definir contrato exacto de “jerarquía” para migración de tareas (qué pasa con padres vacíos, bullets intermedios, etc.).
- Decidir política de versionado única (`3.0.0` vs `2.0.0` interno).
- Revisar documentación duplicada entre `MyJobNotes` (histórica) y `brackets` (core actual) para evitar drift.

## 8) Recomendación de ejecución

- Implementar primero en `brackets` con tests focalizados de parser/generador.
- Validar luego integración desde `MyJobNotes/run_brackets.py`.
- Mantener cambios pequeños y trazables por commit (cuando se vaya a commitear).
