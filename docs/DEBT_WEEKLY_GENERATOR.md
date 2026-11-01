# Deuda Técnica: Weekly Generator y Date Calculation

**Origen**: Fix de Week13 missing days (branch: `fix/week13-missing-days-analysis`)

## Issues Abiertos (Prioridad Baja)

### 1. Edge cases en `_calculate_next_week_dates_iso()`
- **Descripción**: No testiados cruces de año (week 52→1) ni inputs inválidos
- **Cómo reproducir**: Ejecutar con `year=2026, week=52` o `week=0`
- **Impacto**: Bajo (raro en uso manual, pero tests completos > robustez)
- **Effort**: ~5 min (añadir 2 tests en `test_generators_weekly.py`)
- **Ticket potencial**: "Add edge case tests for ISO week calculation"

### 2. Deprecation warning en `ContentParser.get_next_week_dates()`
- **Descripción**: Método legacyrepresentando basado en parser de headers
- **Ruta canónica ahora**: `WeeklyGenerator._calculate_next_week_dates_iso()`
- **Acción**: Marcar con `@deprecated` o comentario claro + warning si se llama directo
- **Impacto**: Bajo (internal call path, pero buena documentación > mantenibilidad)
- **Effort**: ~2 min (docstring + comment)
- **Ticket potencial**: "Deprecate get_next_week_dates in favor of ISO calendar"

### 3. Hardcoded `extract_daily_dates()[:5]` limit
- **Descripción**: Línea 155 en `content_parser.py` silencia semanas con +5 encabezados
- **Riesgo**: Si se mejora parser en futuro, este corte puede ocultar bugs
- **Acción**: Documentar con `TODO` inline + considerar parametrizar
- **Impacto**: Bajo (now fixed in WeeklyGenerator, but good hygiene)
- **Effort**: ~2 min (comment + TODO)
- **Ticket potencial**: "Document [:5] limit in extract_daily_dates()"

## Decisión Actual
Todos estos TODOs quedan para **próximo sprint** (después del PR). El fix actual es minimalista y bien testado.

## Links
- PR branch: `fix/week13-missing-days-analysis`
- Commit: `5b25151`
- Test nuevo: `brackets/tests/test_generators_weekly.py`
