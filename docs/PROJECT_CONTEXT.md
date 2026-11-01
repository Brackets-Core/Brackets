# 🧠 Brackets Core - Contexto de Proyecto e Historial de Conversación

Este documento contiene un resumen estratégico y técnico detallado de **Brackets** para mantener la continuidad del desarrollo. Permite a cualquier agente de IA o desarrollador comprender el estado actual del proyecto, las decisiones de diseño tomadas y los próximos pasos.

---

## 🎯 1. Objetivo y Alcance del Proyecto

**Brackets** es un sistema modular y personalizable de gestión del tiempo y notas personales basado en texto. Su objetivo actual es evolucionar de un sistema tradicional de bitácoras en Markdown puro a una **arquitectura híbrida estructurada (relacional)**:
*   **Para Humanos:** Interfaz Markdown interactiva sencilla (`WeekXX.md`, `MonthTopics.md`) y herramientas CLI locales.
*   **Para Agentes de IA (Copilot / Rovo):** Una base de datos subyacente estructurada en YAML (`tasks.yaml`, `notes.yaml`, `projects.yaml`) para evitar el ruido de texto duplicado y habilitar capacidades de razonamiento relacional sobre el ciclo de vida del trabajo.

### Principio de Diseño "Hub and Spoke"
*   El **Core del Sistema** reside en [`brackets/`](file:///c:/Projects/brackets-workspace/brackets).
*   Los **Vaults de Notas** (como [`MyJobNotes`](file:///c:/Projects/brackets-workspace/MyJobNotes)) son carpetas independientes que contienen datos y configuraciones específicas (`config.yaml`), importando el core mediante un archivo de arranque llamado `run_brackets.py`.

---

## 🛠️ 2. Decisiones Técnicas y Arquitectónicas Tomadas

1.  **Deduplicación del "Rollover" (Arrastre de Tareas)**:
    *   *Antes:* Las tareas pendientes se copiaban íntegramente de un archivo semanal a otro, lo que generaba duplicados masivos y ruido para la IA en los resúmenes mensuales.
    *   *Ahora:* Cada tarea vive **una sola vez** en la base de datos central de tareas (`tasks.yaml`) identificada por un ID único. Su ciclo de vida se gestiona mediante metadatos relacionales (`created_at`, `completed_at`, `status`, `rollover_count`).
2.  **Identificación y Categorización por Proyectos**:
    *   Las tareas se mapean a proyectos de forma automática mediante algoritmos heurísticos basados en palabras clave (ej: "AMR" -> `AMR_LOGISTICS`, "ROVO" -> `ROVO_AI`).
3.  **Extracción de Definiciones con Iconos**:
    *   El parser identifica referencias clave de Jira, links y personas usando prefijos e iconos específicos (ej: `[🎫ATLM-12673]`, `[🦒EXPORT]`, `[🤖Export Ticket Validator]`).
4.  **Codificación Unificada UTF-8**:
    *   Para evitar problemas con caracteres especiales (emojis de estado, tildes) en Windows, la ejecución del motor de Python requiere forzar la variable de entorno `PYTHONUTF8=1`.

---

## 📁 3. Archivos Clave del Ecosistema y su Propósito

### 📄 Documentación y Guías
*   [`VISION_Y_ANALISIS_ESTRATEGICO.md`](file:///c:/Projects/brackets-workspace/brackets/docs/VISION_Y_ANALISIS_ESTRATEGICO.md): Detalla el dilema de arrastre de tareas, la estructura relacional orientada a IA y las próximas propuestas a implementar.
*   [`README.md` del Workspace](file:///c:/Projects/brackets-workspace/README.md): Guía de despliegue para nuevos vaults independientes y configuración del path del Core.

### 🐍 Scripts y Núcleo de Código
*   [`build_2026_mock_database.py`](file:///c:/Projects/brackets-workspace/brackets/scripts/build_2026_mock_database.py): Parser desarrollado para analizar de forma retrospectiva todas las bitácoras semanales del año 2026 presentes en `MyJobNotes` y generar las bases de datos de prueba estructuradas.
*   [`brackets/main.py`](file:///c:/Projects/brackets-workspace/brackets/brackets/main.py): Interfaz CLI de control de Brackets.
*   [`brackets/generators/weekly.py`](file:///c:/Projects/brackets-workspace/brackets/brackets/generators/weekly.py) y [`monthly.py`](file:///c:/Projects/brackets-workspace/brackets/brackets/generators/monthly.py): Generadores del formato Markdown.

### 🗃️ Base de Datos Relacional (Mock actual)
*   [`projects.yaml`](file:///c:/Projects/brackets-workspace/brackets/data/mock/tables/projects.yaml): Tabla consolidada de proyectos con número de tareas pendientes y resueltas.
*   [`definitions.yaml`](file:///c:/Projects/brackets-workspace/brackets/data/mock/tables/definitions.yaml): Tabla de enlaces externos útiles e IDs de Jira.
*   [`tasks.yaml` (mock)](file:///c:/Projects/brackets-workspace/brackets/data/mock/tables/tasks.yaml): Base de datos de tareas consolidada del año 2026.

---

## 🧪 4. Tareas Completadas y Pruebas Realizadas

*   **Generación del Dataset 2026**: El parser ejecutó con éxito la extracción deduplicada de todo el año y la guardó en `data/mock/`.
*   **Pruebas Unitarias y de Integración**: Se verificó la consistencia del motor mediante el comando de testeo:
    ```powershell
    $env:PYTHONUTF8=1; python brackets/tests/test_suite.py
    ```
    Los tests pasan exitosamente garantizando la validez de los esquemas YAML y Markdown resultantes.

---

## ⏳ 5. Estado de Implementación y Próximos Pasos

### ✅ Completado Recientemente:
1.  **Project Hub (Vista por Proyecto y Backlog)**: Implementado en `ProjectBacklogController` y accesible desde el Hub Diario (`[p] Proyectos`).
2.  **Rollover Relacional Inteligente con Regla de 2 Semanas**: Implementado en `EntityManager.rollover_week_to_new_week()`, traspasando tareas pendientes a `## 📋Week Tasks` y desasignando tareas de más de 2 semanas al Backlog de Proyecto.
3.  **Jerarquía `Proyecto ➔ Topic ➔ Tarea / Nota`**: Topics semanales persistidos en `topics.yaml` con asignación en cascada.
4.  **Motor de Tareas y Reuniones Recurrentes**: Persistencia única en `recurring_tasks.yaml` con soporte de días semanales (L-X-V) e intervalos periódicos (cada 4 semanas).

### 🚀 Próximos Pasos Prioritarios:
1.  **Exportador "AI-Context Pack" (`--export-ai`)**:
    *   Generar un documento consolidado sin ruido que sirva de contexto inmediato a IAs externas (pegado manual o exportación a OneNote/Teams).
2.  **Smoke test único para validar vault nuevo en un comando**:
    *   Verificación automática de creación de vault con tablas base.

---

## ⌨️ 6. Comandos y Configuración Clave

*   **Forzar UTF-8 (Crítico en Windows):**
    ```powershell
    $env:PYTHONUTF8=1
    ```
*   **Ejecutar Suite de Tests:**
    ```powershell
    python brackets/tests/test_suite.py
    ```
*   **Reconstruir Base de Datos Mock:**
    ```powershell
    python scripts/build_2026_mock_database.py
    ```
