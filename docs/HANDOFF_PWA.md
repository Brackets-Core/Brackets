# Handoff PWA — Brackets Web Hub

**Fecha:** 2026-11-15  
**Estado actual de la PWA:** `brackets-shell-v17` (`web/static/sw.js`)  
**Repositorio unificado:** `C:\Projects\Brackets` (rama principal `main`, despliegue estático en `gh-pages`)

---

## 1. Últimas mejoras implementadas en la PWA

Las siguientes funcionalidades y mejoras visuales se implementaron y desplegaron hasta la versión `v17` en `gh-pages`:

### 1.1. Paridad con CLI y flujo de trabajo diario
- **Onboarding y auto-scaffolding en modo GitHub (`fb77a09`):** Al conectar un repositorio nuevo o vacío vía GitHub REST API v3, `github_adapter.js` crea automáticamente la estructura base del vault (`config.yaml`, `work_calendar.yaml`, `task_types.yaml`, `menu_config.yaml`, `tables/`, `weeks/`).
- **Configuración interactiva desde la app (`fb77a09`, `324684b`):** Editor visual para el patrón semanal de ubicación laboral (`L-V`), festivos, vacaciones y tareas recurrentes, respetado al generar nuevas semanas.
- **Arrastre diario automático (*rollover*) y ordenación (`9acb126`, `79d4f4e`):**
  - Al cargar el Hub, las tareas no resueltas de días anteriores de la misma semana se mueven automáticamente al día activo (tanto en `web/service.py` como en `web/static/github_adapter.js`), excluyendo reuniones (`task_type === 'meeting'`), tareas recurrentes y días de intervención (`🛠️`).
  - Ordenación *pendientes primero* al crear, completar o mover tareas.
  - Movimiento automático de tareas de semana resueltas al día activo y botón rápido *Mover a hoy*.
- **Autocompletado inteligente:**
  - Con `[` para **Definiciones y Enlaces**, con extracción automática de códigos de ticket Jira desde la URL (`2383833`).
  - Con `@` para **Personas guardadas** (`people`), con filtrado dinámico mientras se escribe y auto-registro (`c3f446e`).

### 1.2. Rediseño UX y estética Crystal Glass (`v13` → `v17`)
- **Creación unificada y limpieza visual (`24a3162`, `3b4dbd5`, `936a93d`):**
  - Eliminadas las barras de creación inline dentro de cada sección y las flechas de subir/bajar; el reordenamiento queda exclusivamente con los handles de 6 puntos (`⋮⋮`) compatibles con escritorio y móvil.
  - Añadido un **Floating Action Button (`+` Speed Dial)** para crear tareas, topics, notas, definiciones, etc., y un botón discreto `+` en la cabecera de cada sección (`.btn-section-quick-add`).
  - Títulos de sección ligeramente mayores, indentación de contenido (`.section-content`) y tareas completadas sin oscurecer (solo tachadas las canceladas).
- **Acabado Cristal Zafiro Traslúcido (`5c83d0f`, `64415f6`, `772aead`, `008352f`):**
  - Gradientes azul zafiro traslúcidos con `backdrop-filter: blur(...) saturate(...)`, bordes luminosos y reflejo especular superior aplicados a:
    - Botón flotante principal (`.fab-main-btn`).
    - Logotipos vectoriales (`web/static/icon-192.svg`, `web/static/icon-512.svg`, `.brand-logo`, `.drawer-logo`).
    - Flecha de creación de nueva bitácora semanal (`.btn-week-arrow.is-create-next`) con pulso suave.
    - Chip del día seleccionado (`.day-chip.active`).
  - Sombra sutil azulada y bisel superior en tarjetas de sección (`.collapsible-section`).
  - Reborde perimetral cristalino muy fino con esquinas suavemente redondeadas alrededor de toda la app (`body::after`).

---

## 2. Decisiones técnicas y de diseño a recordar

1. **Arquitectura Multi-Usuario Client-Side (`gh-pages`):**
   - La PWA publicada en `gh-pages` es 100% estática y se conecta directamente a la API REST de GitHub usando el Token (PAT) y repositorio configurados en el `localStorage` de cada usuario.
   - Compartir la URL de GitHub Pages con terceros **no** consume cuota ni afecta al repositorio del autor: cada persona opera contra su propio repositorio/vault y recibe actualizaciones de la UI cuando se despliega en `gh-pages`.
2. **Paridad obligatoria `service.py` ↔ `github_adapter.js`:**
   - Brackets Web Hub tiene dos motores de datos: el servidor local Python (`web/service.py`) y el adaptador cliente para GitHub (`web/static/github_adapter.js`).
   - Cualquier regla de negocio (rollover diario/semanal, ordenación, parseo/renderizado de bitácoras, scaffolding) debe mantenerse alineada en ambos sitios.
3. **YAML-First (Configuración antes que código):**
   - Tipos de tarea/premojis (`task_types.yaml`), calendario (`work_calendar.yaml`) y menús (`menu_config.yaml`) se leen dinámicamente desde el vault. No hardcodear en JS ni Python.
4. **Reglas de despliegue en `gh-pages` y caché del Service Worker:**
   - La rama `gh-pages` sirve los archivos estáticos directamente en la **raíz** del repositorio (no dentro de `web/static/`).
   - Al desplegar desde `main`, copiar los archivos de `web/static/` (`index.html`, `style.css`, `app.js`, `github_adapter.js`, `sw.js`, `manifest.webmanifest`, `icon-192.svg`, `icon-512.svg`) mediante una carpeta temporal antes de hacer `git checkout gh-pages`, evitando dejar subdirectorios residuales en `gh-pages`.
   - **Siempre** incrementar `CACHE_NAME` en `web/static/sw.js` (actualmente `brackets-shell-v17`) en cada despliegue para forzar la actualización de la PWA en navegadores y apps instaladas.
5. **Contorno redondeado global (`body::after`):**
   - Usa `position: fixed; inset: 2px; border-radius: 12px; pointer-events: none; z-index: 9999;` con máscara exterior `0 0 0 4px var(--bg-app)`. Tenerlo presente si se ajustan `safe-area-inset` en móviles o elementos pegados al borde.

---

## 3. Ideas, mejoras pendientes y próximos pasos

- **Adaptar el flujo de despliegue a la nueva estructura plana (`C:\Projects\Brackets`):**
  - Tras la migración (`beae702`), los estáticos están en `web/static/` (antes `brackets/web/static/`). Conviene crear un script reproducible (p. ej. `scripts/deploy_gh_pages.ps1`) que automatice la copia limpia a `gh-pages` y valide que `CACHE_NAME` se ha incrementado.
- **Validación visual en Modo Claro (`prefers-color-scheme: light`):**
  - El estilo *crystal glass* zafiro (`v14`–`v17`) se afinó sobre el tema oscuro (`#0f1115`). Conviene revisar contraste de bordes, reflejos blancos y sombras de `.fab-main-btn`, `.day-chip.active`, `.collapsible-section` y `body::after` en modo claro.
- **Paridad restante CLI → PWA:**
  - Consolidación mensual/anual directamente desde el modo GitHub.
  - Soporte en la PWA para el módulo de Proyectos (`#[Project]`, índices, hitos y métricas de backlog — Fase 4) y futuro módulo de Aprendizaje (`[🎓LEARNING]` — Fase 5).
- **Cobertura de tests para `github_adapter.js`:**
  - `tests/test_web_service_and_api.py` cubre la parte Python, pero `web/static/github_adapter.js` no tiene aún suite automatizada propia (p. ej. con Node test runner) para verificar rollover, renderizado Markdown y scaffolding ante regresiones.
