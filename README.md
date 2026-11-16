# 🗃️ Brackets — Sistema Operativo Personal de Productividad

Motor modular en Python para gestionar bitácoras semanales en Markdown, con sincronización bidireccional **Markdown ↔ YAML**, **Daily Hub CLI**, **Web Hub (PWA)**, API REST y skills nativas para asistentes de IA.

---

## 📁 Estructura Desacoplada (1 Repo de Sistema + Vaults Externos)

Brackets está diseñado con una **estructura plana** (sin subcarpetas redundantes `brackets/`) y **100% desacoplado de los vaults**:

```text
C:\Projects\                   # (O cualquier carpeta base en otro ordenador)
│
├── Brackets\                  # ⚙️ Repositorio único del Sistema
│   ├── core\                  # Controladores (DailyHub, Menús, Sync...)
│   ├── generators\            # Generadores y renderizadores Markdown
│   ├── managers\              # EntityManager, VaultManager, MarkdownSyncService...
│   ├── models\                # Entidades YAML y TaskTypeRegistry
│   ├── modules\               # Pomodoro Retro y extensiones
│   ├── services\              # Servicios de dominio
│   ├── utils\                 # Parsers y utilidades
│   ├── web\                   # Servidor HTTP y PWA Web Hub
│   ├── tests\                 # Suite de tests unitarios
│   ├── data\                  # Plantillas base y datos mock para tests
│   ├── .agents\skills\        # Skills para asistentes de IA (Antigravity, Copilot, Cursor)
│   ├── AGENTS.md              # Guía arquitectónica para IA
│   ├── main.py                # Punto de entrada CLI
│   ├── run_brackets.py        # Lanzador directo
│   ├── vaults.example.yaml    # Plantilla de configuración de rutas de vaults
│   ├── vaults.yaml            # (Local, ignorado por Git) Rutas de tus vaults en este PC
│   └── Brackets.code-workspace# Workspace Multi-Root para VS Code / Antigravity
│
├── MyJobNotes\                # 💼 Vault de Trabajo (Repo Git privado independiente)
└── MyPersonalNotes\           # 🏠 Vault Personal (Repo Git privado independiente)
```

---

## 🚀 Cómo Instalar / Clonar en Otro Ordenador

1. **Clona el sistema y tus vaults como carpetas hermanas** (o donde prefieras):
   ```powershell
   cd C:\Projects   # o tu carpeta global en el otro PC
   git clone git@github.com:Brackets-Core/Brackets.git Brackets
   git clone git@github.com:Brackets-Core/MyJobNotes.git MyJobNotes
   git clone git@github.com:Brackets-Core/MyPersonalNotes.git MyPersonalNotes
   ```
2. **Instala la única dependencia (`pyyaml`):**
   ```powershell
   pip install -r Brackets/requirements.txt
   ```
3. **Ubicación de los Vaults (Automática o Personalizada):**
   - **Si están como carpetas hermanas (`../MyJobNotes`):** `Brackets` los **autodescubre automáticamente** sin necesidad de configurar nada.
   - **Si están en otra ruta o disco (o quieres cambiarla en cualquier momento):**
     - **Opción A (Interactiva en consola):** Ejecuta `python run_brackets.py` y elige la opción **`🔗 Vincular vault existente / cambiar ruta (vaults.yaml)`**.
     - **Opción B (Archivo YAML):** Copia `vaults.example.yaml` como `vaults.yaml` (está en `.gitignore` para no chocar entre ordenadores) y pon las rutas que quieras:
       ```yaml
       default_vault: MyJobNotes

       vaults:
         - name: MyJobNotes
           path: ../MyJobNotes        # O ruta absoluta: "D:/MisVaults/MyJobNotes"
         - name: MyPersonalNotes
           path: ../MyPersonalNotes
       ```

---

## 💻 Comandos de Uso Diario (Desde `Brackets/`)

```powershell
# Selector interactivo de vaults
python run_brackets.py

# Abrir directamente el Daily Hub de un vault concreto (por nombre o ruta)
python run_brackets.py --vault MyJobNotes
python run_brackets.py --vault MyPersonalNotes

# Iniciar Brackets Web Hub (Interfaz PWA instalable + API REST en http://127.0.0.1:8080)
python run_brackets.py --web

# Crear acceso directo en el Menú Inicio (arranca el servidor oculto si no está activo y abre la app)
powershell -ExecutionPolicy Bypass -File .\scripts\launch_web_hub.ps1 -CreateShortcut
```

---

## 🧪 Ejecutar los Tests

```powershell
cd C:\Projects\Brackets
python -m unittest discover -s tests
```
