# 🗓️ Brackets

<div align="center">

**Sistema Operativo Personal de Productividad: Bitácoras Semanales, Base Relacional YAML, CLI y Web Hub (PWA)**

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-3.0.0-green.svg)](https://github.com/CodeAndRes/Brackets/releases)

[Características](#-características) •
[Instalación y Ejecución](#️-requisitos-e-instalación) •
[Web Hub y API REST](#-brackets-web-hub-pwa--api-rest) •
[Estructura](#-estructura-del-repositorio) •
[Tests](#-tests)

</div>

---

## 🎯 ¿Qué es Brackets?

Brackets es un motor modular en Python que combina **bitácoras semanales en Markdown** con una **base de datos relacional YAML-First**, manteniendo tus vaults **100% libres de código Python**:

- 🖥️ **Daily Hub en CLI y Web (PWA)**: Gestiona el día a día desde consola o desde navegador/móvil instalable como app.
- 🔄 **Sincronización Bidireccional `Markdown ↔ YAML`**: Edita tus archivos `.md` en cualquier editor o usa la interfaz/API; Brackets reconcilia ambos mundos de forma idempotente.
- 🗂️ **Multi-Vault Externo y Agnóstico**: Opera múltiples vaults (`work` de 5 días o `personal` de 7 días) alojados en `vaults/` o en cualquier ruta externa mediante `--vault`, `BRACKETS_VAULT` o `vaults.yaml`.
- 🏷️ **Tipos de Tareas y Premojis Declarativos**: Configurables sin tocar código en `data/task_types.yaml` (`meeting` → `🫱🏼‍🫲🏽`, `habit` → `🌱`, etc.) y soporte de proyectos con `#[ProjectCode]`.
- 📦 **Consolidación Mensual/Anual y Categorías `[BRACKETS]`**: Archivo histórico jerárquico y nomenclatura estructurada por corchetes.
- 🍅 **Pomodoro Timer + Tomatín**: Temporizador de foco integrado en consola y modo visual retro.

---

## ✨ Características Principales

### 🗃️ Modelo Relacional YAML-First
- **Tablas desacopladas en `data/tables/`**: `tasks.yaml`, `topics.yaml`, `projects.yaml`, `definitions.yaml`, `recurring_tasks.yaml`, `people.yaml` y notas mensuales en `data/tables/notes/`.
- **Programación por semana en `data/weeks/YYYY-WXX.yaml`**: Vincula días, ubicaciones (`🏠`/`🚗`), tareas del día, `Week Tasks` sin día fijo y `Topics`.
- **Backlog y métricas por proyecto**: Trazabilidad mediante tags `#[Proyecto]` y rollover inteligente de tareas pendientes entre semanas.

### ⚙️ Adaptación Nativa `work` vs `personal`
Definido en `data/config.yaml` (`vault_type: work | personal`):
- **Work**: Semanas laborables (Lunes a Viernes + soporte opcional de guardia), calendario laboral con festivos/cierres/jornada intensiva y foco en proyectos/tickets.
- **Personal**: Semanas naturales completas (7 días, Lunes a Domingo), premojis orientados a hábitos (`🌱`), recados, salud y finanzas.

---

## 🛠️ Requisitos e Instalación

- **Python 3.9+**
- **PyYAML** (`pip install -r requirements.txt`) — el servidor Web/API usa exclusivamente la librería estándar de Python.

### Ejecución Externa (Cero Python en los Vaults)

El motor siempre se lanza desde fuera del vault (desde el launcher del workspace o desde este repositorio):

```powershell
# Selector interactivo de vaults descubiertos / registrados en vaults.yaml
python run_brackets.py

# Apuntar a un vault por nombre o ruta absoluta externa
python run_brackets.py --vault MyJobNotes
python run_brackets.py --vault "D:/MisNotas/VaultPersonal"

# Mediante variable de entorno
$env:BRACKETS_VAULT="MyJobNotes"
python run_brackets.py
```

### Comandos Rápidos CLI

```powershell
python run_brackets.py --vault MyJobNotes --weekly                  # Generar nueva bitácora semanal
python run_brackets.py --vault MyJobNotes --add-task "Revisar PR"   # Añadir tarea rápida
python run_brackets.py --vault MyJobNotes --list                    # Listar bitácoras recientes
python run_brackets.py --vault MyJobNotes --consolidate 2026-10     # Consolidar mes
python run_brackets.py --vault MyJobNotes --consolidate-year 2026   # Consolidar año
python run_brackets.py --timer                                      # Pomodoro CLI
python run_brackets.py --timer-gui                                  # Pomodoro GUI retro (Tomatín)
python run_brackets.py --web --port 8080                            # Iniciar Web Hub + API REST
```

---

## 🌐 Brackets Web Hub (PWA & API REST)

Al ejecutar `python run_brackets.py --web`, Brackets levanta un servidor ligero (`127.0.0.1:8080` por defecto) que sirve la **PWA instalable** (PC/móvil) y una **API REST JSON** pensada también para que agentes de IA y automatizaciones registren tareas o actividad directamente:

| Método | Ruta | Propósito |
|---|---|---|
| `GET` | `/api/vaults` | Lista todos los vaults disponibles (`name`, `path`, `vault_type`). |
| `GET` | `/api/hub?vault=<name>&year=YYYY&week=WW&day=DD` | Devuelve el estado completo de la semana y día activo (tareas, progreso, ubicaciones, proyectos). |
| `POST` | `/api/tasks` | Crea una tarea (pendiente o ya completada) y regenera el `.md` semanal automáticamente. |
| `POST` / `PATCH` | `/api/tasks/{task_id}/toggle` | Alterna el estado `pending` / `done` de una tarea y sincroniza el `.md`. |
| `POST` / `PATCH` | `/api/days/{day_number}/location` | Actualiza el emoji/nota de ubicación de un día (`🏠`, `🚗`, etc.). |
| `POST` | `/api/sync` | Fuerza reconciliación `Markdown ➔ YAML ➔ Markdown` de la semana activa. |

**Ejemplo de alta de tarea ya resuelta desde IA o script (`POST /api/tasks`):**

```json
{
  "vault": "MyJobNotes",
  "title": "🫱🏼‍🫲🏽 Revisión de arquitectura API #[BRACKETS]",
  "target": "today",
  "is_done": true,
  "description": "Acordado diseño desacoplado de vaults y skills."
}
```

---

## 📁 Estructura del Repositorio

```text
brackets/
├── brackets/                  # 🎯 Paquete principal Python
│   ├── core/                  # Controladores modulares (DailyHub, Startup, MenuEngine, Backlog...)
│   ├── managers/              # EntityManager, MarkdownSyncService, VaultManager, SettingsManager
│   ├── models/                # Entidades relacionales (Task, Note, Topic...) y TaskTypeRegistry
│   ├── generators/            # WeeklyGenerator, MonthlyGenerator y BitacoraRenderer
│   ├── consolidators/         # Consolidación mensual y anual segura
│   ├── modules/               # Módulos enchufables (Pomodoro Timer, mascota retro Tomatín)
│   ├── web/                   # Servidor HTTP estándar, BracketsWebService y PWA estática
│   ├── services/              # Servicios de dominio auxiliares
│   ├── worklog/               # Registro de eventos y actividad (log4brackets)
│   ├── utils/                 # Parsers de Markdown, buscadores y creadores de vaults
│   ├── tests/                 # Suite de tests automatizados (unittest)
│   └── main.py                # Punto de entrada del paquete
├── data/                      # Plantillas YAML por defecto y base mock para tests
├── docs/                      # Especificaciones, diseño y contexto técnico
├── scripts/                   # Utilidades de mantenimiento y demos del motor
├── run_brackets.py            # Launcher local del motor
├── requirements.txt           # Dependencias (PyYAML)
├── setup.py                   # Empaquetado pip
└── LICENSE                    # Licencia MIT
```

---

## 🧪 Tests

El proyecto cuenta con una suite de **144 tests unitarios y de integración** (incluyendo sincronización bidireccional, premojis, descubrimiento multi-vault y endpoints HTTP de la API Web):

```powershell
# Ejecutar toda la suite estándar desde la carpeta brackets/
python -m unittest discover -s brackets/tests
```

---

## 📝 Licencia

Distribuido bajo la licencia MIT. Consulta [`LICENSE`](LICENSE) para más información.
