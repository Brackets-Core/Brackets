/**
 * Brackets Web Hub — Adaptador Híbrido GitHub REST API v3 & Multi-Vault
 * =====================================================================
 * Permite operar la PWA de forma 100% serverless desde el móvil o navegador
 * leyendo y escribiendo archivos .md y YAML directamente contra repositorios
 * privados de GitHub (/repos/{owner}/{repo}/contents/{path}), mientras mantiene
 * intacto el funcionamiento local en PC cuando se usa el servidor Python.
 */

(function (global) {
  'use strict';

  const STORAGE_KEY_CONFIG = 'brackets_github_config_v1';
  const STORAGE_KEY_ACTIVE_VAULT = 'brackets_preferred_vault_v1';

  // Catálogo base de tipos de tarea y premojis (compatible con task_types.yaml)
  const DEFAULT_TASK_TYPES = [
    { key: 'meeting', premoji: '🫱🏼‍🫲🏽', prefixes: ['reunión:', 'reunion:', 'meeting:'], aliases: ['🤝', '🫱🏼‍🫲🏽'] },
    { key: 'habit', premoji: '🌱', prefixes: ['hábito:', 'habito:', 'habit:'], aliases: ['🌱'] },
    { key: 'bug', premoji: '🐛', prefixes: ['bug:', 'fix:'], aliases: ['🐛'] },
    { key: 'call', premoji: '📞', prefixes: ['llamada:', 'call:'], aliases: ['📞', '☎️'] },
    { key: 'urgent', premoji: '🔥', prefixes: ['urgente:', 'urgent:'], aliases: ['🔥', '🚨'] },
    { key: 'health', premoji: '💪', prefixes: ['salud:', 'entreno:', 'gym:'], aliases: ['💪', '🏃'] },
    { key: 'errand', premoji: '🛒', prefixes: ['recado:', 'compra:', 'compras:'], aliases: ['🛒'] },
    { key: 'finance', premoji: '💰', prefixes: ['finanzas:', 'pago:', 'gasto:'], aliases: ['💰'] }
  ];

  // Menú declarativo por defecto cuando se opera en modo GitHub directo
  const DEFAULT_WEB_TOP_MENU = [
    {
      id: 'bitacoras',
      label: '📅 Bitácoras',
      items: [
        { id: 'next_weekly', label: '➕ Nueva Bitácora Semanal (arrastrar pendientes)', command: 'next_weekly' },
        { id: 'switch_week', label: '🗓️ Cambiar / Navegar Semana', command: 'switch_week' },
        { id: 'add_extra_day', label: '🛠️ Añadir Día Extra / Intervención', command: 'add_extra_day' }
      ]
    },
    {
      id: 'sync_recurring',
      label: '🔄 Sincronización',
      items: [
        { id: 'sync_current_week', label: '🔄 Refrescar Semana desde GitHub', command: 'sync_current_week' }
      ]
    },
    {
      id: 'projects_backlog',
      label: '📁 Proyectos e Ideas',
      items: [
        { id: 'projects_overview', label: '📊 Estado de Proyectos en Semana', command: 'projects_overview' },
        { id: 'ideas_manager', label: '💡 Gestionar Ideas ([🧩GENERAL]🧠Ideas.md)', command: 'ideas_manager' },
        { id: 'schedule_week_to_today', label: '➡️ Agendar Tarea Semanal a Día Activo', command: 'schedule_week_to_today' }
      ]
    },
    {
      id: 'tools',
      label: '🛠️ Herramientas y GitHub',
      items: [
        { id: 'pomodoro_focus', label: '🍅 Temporizador Pomodoro (Modo Focus)', command: 'pomodoro_focus' },
        { id: 'github_settings', label: '☁️ Configurar GitHub API / Vaults Remotos', command: 'github_settings' }
      ]
    }
  ];

  // ===========================================================================
  // 1. Codificación / Decodificación Base64 UTF-8 Segura
  // ===========================================================================
  function utf8ToBase64(str) {
    const text = String(str ?? '');
    if (typeof TextEncoder !== 'undefined') {
      const bytes = new TextEncoder().encode(text);
      let binary = '';
      const chunkSize = 0x8000;
      for (let i = 0; i < bytes.length; i += chunkSize) {
        binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
      }
      return global.btoa(binary);
    }
    return global.btoa(unescape(encodeURIComponent(text)));
  }

  function base64ToUtf8(b64) {
    const clean = String(b64 ?? '').replace(/\s+/g, '');
    if (!clean) return '';
    const binary = global.atob(clean);
    if (typeof TextDecoder !== 'undefined') {
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
      }
      return new TextDecoder('utf-8').decode(bytes);
    }
    return decodeURIComponent(escape(binary));
  }

  // ===========================================================================
  // 2. Gestor de Configuración Multi-Vault y Personal Access Token (PAT)
  // ===========================================================================
  const DEFAULT_REMOTE_VAULTS = [
    {
      id: 'gh:MyPersonalNotes',
      name: '☁️ MyPersonalNotes',
      owner: 'Brackets-Core',
      repo: 'MyPersonalNotes',
      branch: 'main',
      base_path: '',
      vault_type: 'personal',
      days_per_week: 7,
      description: 'Notas, hábitos y planificación personal (7 días) vía GitHub API'
    },
    {
      id: 'gh:MyJobNotes',
      name: '☁️ MyJobNotes',
      owner: 'Brackets-Core',
      repo: 'MyJobNotes',
      branch: 'master',
      base_path: '',
      vault_type: 'work',
      days_per_week: 5,
      description: 'Bitácoras y proyectos de trabajo vía GitHub API'
    }
  ];

  const GitHubConfigStore = {
    getConfig() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY_CONFIG);
        if (!raw) {
          return {
            github_token: '',
            remote_vaults: JSON.parse(JSON.stringify(DEFAULT_REMOTE_VAULTS))
          };
        }
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed.remote_vaults) || parsed.remote_vaults.length === 0) {
          parsed.remote_vaults = JSON.parse(JSON.stringify(DEFAULT_REMOTE_VAULTS));
        }
        const cleanedVaults = parsed.remote_vaults.map((rv) => ({
          ...rv,
          name: (rv.name || '').replace(/\s*\((GitHub|Local)\)\s*/gi, '').trim()
        }));
        return {
          github_token: (parsed.github_token || '').trim(),
          remote_vaults: cleanedVaults
        };
      } catch (e) {
        return {
          github_token: '',
          remote_vaults: JSON.parse(JSON.stringify(DEFAULT_REMOTE_VAULTS))
        };
      }
    },

    saveConfig(cfg) {
      const normalized = {
        github_token: (cfg.github_token || '').trim(),
        remote_vaults: Array.isArray(cfg.remote_vaults) ? cfg.remote_vaults : DEFAULT_REMOTE_VAULTS
      };
      localStorage.setItem(STORAGE_KEY_CONFIG, JSON.stringify(normalized));
      return normalized;
    },

    getToken() {
      return this.getConfig().github_token;
    },

    setToken(token) {
      const cfg = this.getConfig();
      cfg.github_token = (token || '').trim();
      return this.saveConfig(cfg);
    },

    hasToken() {
      return Boolean(this.getToken());
    },

    getRemoteVaults() {
      return this.getConfig().remote_vaults;
    },

    getVaultById(vaultId) {
      if (!vaultId) return null;
      const vaults = this.getRemoteVaults();
      return vaults.find((v) => v.id === vaultId || `gh:${v.id}` === vaultId) || null;
    },

    isGitHubVault(vaultId) {
      if (!vaultId) return false;
      return String(vaultId).startsWith('gh:') || Boolean(this.getVaultById(vaultId));
    },

    upsertRemoteVault(vaultObj) {
      const cfg = this.getConfig();
      const rawId = (vaultObj.id || `${vaultObj.repo || 'vault'}`).replace(/^gh:/, '').trim();
      const id = `gh:${rawId}`;
      const entry = {
        id,
        name: (vaultObj.name || `☁️ ${vaultObj.repo}`).trim(),
        owner: (vaultObj.owner || '').trim(),
        repo: (vaultObj.repo || '').trim(),
        branch: (vaultObj.branch || 'main').trim(),
        base_path: (vaultObj.base_path || '').replace(/^\/+|\/+$/g, '').trim(),
        vault_type: vaultObj.vault_type || 'personal',
        days_per_week: Number(vaultObj.days_per_week) || (vaultObj.vault_type === 'work' ? 5 : 7),
        description: vaultObj.description || `Repositorio ${vaultObj.owner}/${vaultObj.repo} (${vaultObj.branch || 'main'})`
      };
      const idx = cfg.remote_vaults.findIndex((v) => v.id === id);
      if (idx >= 0) {
        cfg.remote_vaults[idx] = entry;
      } else {
        cfg.remote_vaults.push(entry);
      }
      this.saveConfig(cfg);
      return entry;
    },

    removeRemoteVault(vaultId) {
      const cfg = this.getConfig();
      cfg.remote_vaults = cfg.remote_vaults.filter((v) => v.id !== vaultId);
      this.saveConfig(cfg);
    },

    getPreferredVault() {
      return localStorage.getItem(STORAGE_KEY_ACTIVE_VAULT) || null;
    },

    setPreferredVault(vaultId) {
      if (vaultId) {
        localStorage.setItem(STORAGE_KEY_ACTIVE_VAULT, vaultId);
      }
    }
  };

  // ===========================================================================
  // 3. Cliente REST API v3 de GitHub con Control de SHA y Caché
  // ===========================================================================
  const originalFetch = global.fetch.bind(global);

  const GitHubRestClient = {
    shaCache: new Map(),
    fileCache: new Map(),

    _cacheKey(vault, relPath) {
      const cleanPath = this._resolvePath(vault, relPath);
      return `${vault.owner}/${vault.repo}@${vault.branch || 'main'}:${cleanPath}`;
    },

    _resolvePath(vault, relPath) {
      const base = (vault.base_path || '').replace(/^\/+|\/+$/g, '');
      const rel = String(relPath || '').replace(/^\/+|\/+$/g, '');
      if (!base) return rel;
      if (!rel) return base;
      return `${base}/${rel}`;
    },

    _encodeUriPath(fullPath) {
      if (!fullPath) return '';
      return fullPath
        .split('/')
        .filter(Boolean)
        .map((seg) => encodeURIComponent(seg))
        .join('/');
    },

    clearCache() {
      this.fileCache.clear();
    },

    async request(path, options = {}, tokenOverride = null) {
      const token = (tokenOverride !== null ? tokenOverride : GitHubConfigStore.getToken()).trim();
      if (!token) {
        const err = new Error('No hay Personal Access Token (PAT) de GitHub configurado.');
        err.code = 'NO_GITHUB_TOKEN';
        throw err;
      }

      const url = path.startsWith('https://') ? path : `https://api.github.com${path}`;
      const headers = Object.assign(
        {
          Accept: 'application/vnd.github.v3+json',
          Authorization: `Bearer ${token}`,
          'X-GitHub-Api-Version': '2022-11-28'
        },
        options.headers || {}
      );

      if (options.body && !headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
      }

      const res = await originalFetch(url, Object.assign({}, options, { headers, cache: 'no-store' }));
      if (res.status === 404) {
        const err = new Error(`Recurso no encontrado en GitHub (404): ${path}`);
        err.status = 404;
        throw err;
      }
      if (res.status === 409) {
        const err = new Error('Conflicto de versión (SHA) en GitHub (409). El archivo cambió remotamente; sincroniza para obtener la última versión.');
        err.status = 409;
        throw err;
      }
      if (!res.ok) {
        let detail = '';
        try {
          const errJson = await res.json();
          detail = errJson.message || '';
        } catch (_) {}
        const err = new Error(`GitHub API Error (${res.status}): ${detail || res.statusText}`);
        err.status = res.status;
        throw err;
      }

      if (res.status === 204) return null;
      return await res.json();
    },

    async verifyRepoAccess(vault, tokenOverride = null) {
      const data = await this.request(
        `/repos/${encodeURIComponent(vault.owner)}/${encodeURIComponent(vault.repo)}`,
        { method: 'GET' },
        tokenOverride
      );
      return {
        full_name: data.full_name,
        private: data.private,
        default_branch: data.default_branch,
        permissions: data.permissions || {}
      };
    },

    async listContents(vault, relDir = '') {
      const fullDir = this._resolvePath(vault, relDir);
      const encodedPath = this._encodeUriPath(fullDir);
      const branch = encodeURIComponent(vault.branch || 'main');
      const endpoint = `/repos/${encodeURIComponent(vault.owner)}/${encodeURIComponent(vault.repo)}/contents/${encodedPath}?ref=${branch}`;
      try {
        const items = await this.request(endpoint, { method: 'GET' });
        return Array.isArray(items) ? items : [items];
      } catch (err) {
        if (err.status === 404) return [];
        throw err;
      }
    },

    async getFile(vault, relPath, { useCache = false } = {}) {
      const key = this._cacheKey(vault, relPath);
      if (useCache && this.fileCache.has(key)) {
        return this.fileCache.get(key);
      }

      const fullPath = this._resolvePath(vault, relPath);
      const encodedPath = this._encodeUriPath(fullPath);
      const branch = encodeURIComponent(vault.branch || 'main');
      const endpoint = `/repos/${encodeURIComponent(vault.owner)}/${encodeURIComponent(vault.repo)}/contents/${encodedPath}?ref=${branch}`;

      const data = await this.request(endpoint, { method: 'GET' });
      const content = base64ToUtf8(data.content || '');
      const result = {
        content,
        sha: data.sha,
        path: data.path,
        name: data.name
      };
      this.shaCache.set(key, data.sha);
      this.fileCache.set(key, result);
      return result;
    },

    async putFile(vault, relPath, contentStr, commitMessage = 'Update from Brackets Web Hub', explicitSha = null) {
      const key = this._cacheKey(vault, relPath);
      const fullPath = this._resolvePath(vault, relPath);
      const encodedPath = this._encodeUriPath(fullPath);
      const endpoint = `/repos/${encodeURIComponent(vault.owner)}/${encodeURIComponent(vault.repo)}/contents/${encodedPath}`;

      let sha = explicitSha || this.shaCache.get(key) || null;
      if (!sha) {
        try {
          const existing = await this.getFile(vault, relPath, { useCache: false });
          sha = existing.sha;
        } catch (err) {
          if (err.status !== 404) throw err;
        }
      }

      const payload = {
        message: commitMessage,
        content: utf8ToBase64(contentStr),
        branch: vault.branch || 'main'
      };
      if (sha) {
        payload.sha = sha;
      }

      let resData;
      try {
        resData = await this.request(endpoint, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
      } catch (err) {
        // Si hubo desajuste de SHA en caché, refrescar SHA una vez y reintentar
        if (err.status === 409) {
          const latest = await this.getFile(vault, relPath, { useCache: false });
          payload.sha = latest.sha;
          resData = await this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(payload)
          });
        } else {
          throw err;
        }
      }

      const newSha = resData && resData.content ? resData.content.sha : null;
      if (newSha) {
        this.shaCache.set(key, newSha);
        this.fileCache.set(key, {
          content: contentStr,
          sha: newSha,
          path: fullPath
        });
      }
      return {
        sha: newSha,
        commit: resData && resData.commit ? resData.commit.sha : null
      };
    }
  };

  // ===========================================================================
  // 4. Utilidades de Fecha ISO 8601 y Nombres de Archivo [YYYY][MM]WeekXX.md
  // ===========================================================================
  const WEEKDAY_LETTERS = { 1: 'L', 2: 'M', 3: 'X', 4: 'J', 5: 'V', 6: 'S', 7: 'D' };
  const WEEKDAY_NAMES = {
    1: 'Lunes',
    2: 'Martes',
    3: 'Miércoles',
    4: 'Jueves',
    5: 'Viernes',
    6: 'Sábado',
    7: 'Domingo'
  };

  function getIsoWeekInfo(dateObj = new Date()) {
    const d = new Date(Date.UTC(dateObj.getFullYear(), dateObj.getMonth(), dateObj.getDate()));
    const dayNum = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    const weekNumber = Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
    return {
      year: d.getUTCFullYear(),
      week_number: weekNumber,
      iso_weekday: dayNum
    };
  }

  function getDateFromIsoWeek(year, weekNumber, isoDay = 1) {
    const simple = new Date(Date.UTC(year, 0, 1 + (weekNumber - 1) * 7));
    const dow = simple.getUTCDay() || 7;
    const isoWeekStart = new Date(simple);
    if (dow <= 4) {
      isoWeekStart.setUTCDate(simple.getUTCDate() - dow + 1);
    } else {
      isoWeekStart.setUTCDate(simple.getUTCDate() + 8 - dow);
    }
    const target = new Date(isoWeekStart);
    target.setUTCDate(isoWeekStart.getUTCDate() + (isoDay - 1));
    return target;
  }

  function formatWeekFilename(year, month, weekNumber) {
    const mm = String(month).padStart(2, '0');
    const ww = String(weekNumber).padStart(2, '0');
    return `[${year}][${mm}]Week${ww}.md`;
  }

  function parseWeekFilename(filename) {
    const m = String(filename || '').match(/^\[(\d{4})\]\[(\d{2})\]Week(\d{1,2})\.md$/i);
    if (!m) return null;
    const year = parseInt(m[1], 10);
    const month = parseInt(m[2], 10);
    const week_number = parseInt(m[3], 10);
    return {
      year,
      month,
      week_number,
      key: `${year}-W${String(week_number).padStart(2, '0')}`,
      file: filename
    };
  }

  function syncTaskFlags(task) {
    task.is_done = task.status === 'done';
    task.is_cancelled = task.status === 'cancelled';
    return task;
  }


  // ===========================================================================
  // 4b. Soporte para work_calendar.yaml y Resolución de Ubicación Diaria
  // ===========================================================================
  function getDefaultWorkCalendar(vaultType) {
    return {
      locations: { home: '🏠', office: '🚗', remote: '💻', off: '🏖️' },
      work_pattern: {
        alternating_day: 'friday',
        even_week: 'office',
        odd_week: 'home',
        defaults: {
          monday: 'office',
          tuesday: 'office',
          wednesday: 'home',
          thursday: 'home',
          friday: 'alternating',
          saturday: 'off',
          sunday: 'off'
        }
      },
      calendar: {
        holidays: [],
        closures: [],
        intensive_workdays: [],
        vacations: []
      }
    };
  }

  function parseWorkCalendarYaml(yamlText) {
    if (!yamlText) return null;
    const config = getDefaultWorkCalendar('work');
    const lines = yamlText.split(/\r?\n/);
    let section = null;
    let subSection = null;
    let currentItem = null;

    for (let rawLine of lines) {
      if (!rawLine.trim() || rawLine.trim().startsWith('#')) continue;
      const indent = rawLine.search(/\S/);
      const line = rawLine.trim();

      if (indent === 0 && line.includes(':')) {
        section = line.split(':')[0].trim().replace(/^['"]|['"]$/g, '');
        subSection = null;
        currentItem = null;
        continue;
      }

      if (section === 'locations' && indent >= 2 && line.includes(':')) {
        const idx = line.indexOf(':');
        const k = line.slice(0, idx).trim().replace(/^['"]|['"]$/g, '');
        const v = line.slice(idx + 1).trim().replace(/^['"]|['"]$/g, '');
        if (k && v) config.locations[k] = v;
        continue;
      }

      if (section === 'work_pattern') {
        if (indent === 2 && line.startsWith('defaults:')) {
          subSection = 'defaults';
          continue;
        }
        if (indent === 2 && line.includes(':')) {
          const idx = line.indexOf(':');
          const k = line.slice(0, idx).trim().replace(/^['"]|['"]$/g, '');
          const v = line.slice(idx + 1).trim().replace(/^['"]|['"]$/g, '');
          config.work_pattern[k] = v;
          continue;
        }
        if (subSection === 'defaults' && indent >= 4 && line.includes(':')) {
          const idx = line.indexOf(':');
          const k = line.slice(0, idx).trim().replace(/^['"]|['"]$/g, '');
          const v = line.slice(idx + 1).trim().replace(/^['"]|['"]$/g, '');
          config.work_pattern.defaults[k] = v;
          continue;
        }
      }

      if (section === 'calendar') {
        if (indent === 2 && !line.startsWith('- ') && line.includes(':')) {
          subSection = line.split(':')[0].trim().replace(/^['"]|['"]$/g, '');
          currentItem = null;
          if (!config.calendar[subSection]) config.calendar[subSection] = [];
          continue;
        }
        if (subSection) {
          if (line.startsWith('- ')) {
            currentItem = {};
            config.calendar[subSection].push(currentItem);
            const rest = line.slice(2).trim();
            if (rest.includes(':')) {
              const idx = rest.indexOf(':');
              const k = rest.slice(0, idx).trim().replace(/^['"]|['"]$/g, '');
              const v = rest.slice(idx + 1).trim().replace(/^['"]|['"]$/g, '');
              currentItem[k] = v;
            }
          } else if (currentItem && line.includes(':')) {
            const idx = line.indexOf(':');
            const k = line.slice(0, idx).trim().replace(/^['"]|['"]$/g, '');
            const v = line.slice(idx + 1).trim().replace(/^['"]|['"]$/g, '');
            currentItem[k] = v;
          }
        }
      }
    }
    return config;
  }

  function resolveDayLocation(dateObj, weekNumber, calendar, vaultType) {
    if (vaultType === 'personal') {
      return { emoji: '🌱', note: null };
    }
    const cal = calendar || getDefaultWorkCalendar('work');
    const locations = cal.locations || { home: '🏠', office: '🚗', remote: '💻', off: '🏖️' };
    const offEmoji = locations['off'] || locations.off || '🏖️';

    // Formatear YYYY-MM-DD
    const y = dateObj.getUTCFullYear();
    const m = String(dateObj.getUTCMonth() + 1).padStart(2, '0');
    const d = String(dateObj.getUTCDate()).padStart(2, '0');
    const dateStr = `${y}-${m}-${d}`;

    // 1. Festivos
    const holidays = (cal.calendar && cal.calendar.holidays) || [];
    const holiday = holidays.find((h) => h.date === dateStr);
    if (holiday) return { emoji: offEmoji, note: holiday.name };

    // 2. Cierres de sede central
    const closures = (cal.calendar && cal.calendar.closures) || [];
    const closure = closures.find((c) => c.date === dateStr);
    if (closure) return { emoji: offEmoji, note: closure.name };

    // 3. Vacaciones
    const vacations = (cal.calendar && cal.calendar.vacations) || [];
    const vacation = vacations.find((v) => v.start <= dateStr && dateStr <= v.end);
    if (vacation) return { emoji: offEmoji, note: vacation.name };

    // 4. Patrón laboral habitual
    const jsDay = dateObj.getUTCDay();
    const isoIdx = jsDay === 0 ? 6 : jsDay - 1; // 0=Lunes ... 6=Domingo
    const dayKey = WEEKDAY_KEYS[isoIdx] || 'monday';

    const wp = cal.work_pattern || {};
    const defaults = wp.defaults || {
      monday: 'office',
      tuesday: 'office',
      wednesday: 'home',
      thursday: 'home',
      friday: 'alternating',
      saturday: 'off',
      sunday: 'off'
    };

    let locKey = defaults[dayKey] || 'office';
    if (locKey === 'alternating' && dayKey === (wp.alternating_day || 'friday')) {
      const isEven = (weekNumber % 2 === 0);
      locKey = isEven ? (wp.even_week || 'office') : (wp.odd_week || 'home');
    }

    const emoji = locations[locKey] || (locKey === 'home' ? '🏠' : '🚗');

    // 5. Jornada Intensiva (agrega nota)
    const intensives = (cal.calendar && cal.calendar.intensive_workdays) || [];
    const intensive = intensives.find((i) => i.date === dateStr);
    const note = intensive ? intensive.name : null;

    return { emoji, note };
  }

  // ===========================================================================
  // 5. Codec Markdown + Frontmatter YAML de Bitácoras (Compatible 100% con Motor)
  // ===========================================================================
  const BitacoraMarkdownCodec = {
    detectTaskTypeAndCleanTitle(rawText) {
      let text = String(rawText || '').trim();
      let detectedType = 'task';
      let premoji = '';

      for (const t of DEFAULT_TASK_TYPES) {
        for (const emoji of t.aliases) {
          if (text.startsWith(emoji)) {
            detectedType = t.key;
            premoji = t.premoji;
            text = text.slice(emoji.length).trim();
            break;
          }
        }
        if (detectedType !== 'task') break;

        const lower = text.toLowerCase();
        for (const pref of t.prefixes) {
          if (lower.startsWith(pref)) {
            detectedType = t.key;
            premoji = t.premoji;
            text = text.slice(pref.length).trim();
            break;
          }
        }
        if (detectedType !== 'task') break;
      }

      return { task_type: detectedType, premoji, clean_title: text };
    },

    parseProjectTag(rawText) {
      let clean = String(rawText || '').trim();
      const mHash = clean.match(/#\[([A-Za-z0-9_-]+)\]/);
      if (mHash) {
        const projId = mHash[1].trim();
        clean = (clean.slice(0, mHash.index) + clean.slice(mHash.index + mHash[0].length)).replace(/\s{2,}/g, ' ').trim();
        return { project_id: projId, clean_title: clean };
      }
      const mLead = clean.match(/^\[([A-Za-z0-9_-]+)\]\s*(.*)$/);
      if (mLead && mLead[1].length > 1 && !/[🎫🦒🤖📺📂📁🔗📊🛠️]/.test(mLead[1])) {
        return { project_id: mLead[1].trim(), clean_title: mLead[2].trim() };
      }
      return { project_id: null, clean_title: clean };
    },

    extractFrontmatter(markdown) {
      const text = String(markdown || '');
      const m = text.match(/^(---\r?\n[\s\S]*?\r?\n---\r?\n?)/);
      if (m) {
        return {
          frontmatter: m[1],
          body: text.slice(m[1].length)
        };
      }
      return { frontmatter: '', body: text };
    },

    parseWeekMarkdown(markdown, year, weekNumber, vault) {
      const { frontmatter, body } = this.extractFrontmatter(markdown);
      const lines = body.split(/\r?\n/);

      let weight = null;
      let currentSection = null;
      let currentDayNum = null;

      const topics = [];
      const weekTasks = [];
      const notes = [];
      const daysMap = new Map();
      const daysOrder = [];
      const definitions = [];

      let currentNote = null;
      let lastTaskObj = null;
      let taskCounter = 1;

      const makeTask = (rawLineText, isDoneCheckbox) => {
        let text = rawLineText.trim();
        let status = isDoneCheckbox ? 'done' : 'pending';
        if (text.includes('~~')) {
          const stripped = text.replace(/~~/g, '').replace(/^\s*\[[ xX]?\]\s*/, '').trim();
          if (stripped) {
            status = 'cancelled';
            text = stripped;
          }
        }
        const { task_type, premoji, clean_title: afterType } = this.detectTaskTypeAndCleanTitle(text);
        const { project_id, clean_title } = this.parseProjectTag(afterType);
        const id = `TSK-GH-${String(taskCounter++).padStart(4, '0')}`;
        return syncTaskFlags({
          id,
          title: clean_title,
          status,
          task_type,
          premoji,
          project_id,
          description: null
        });
      };

      const flushNote = () => {
        if (currentNote && (currentNote.title || currentNote.content.length > 0)) {
          notes.push(currentNote);
        }
        currentNote = null;
      };

      for (const line of lines) {
        const stripped = line.trim();

        // Encabezado H1 (# 🗓️Week 40 75.5)
        if (stripped.startsWith('# ')) {
          const wMatch = stripped.match(/Week\s+\d+\s+([0-9]+(?:[.,][0-9]+)?)/i);
          if (wMatch) {
            weight = parseFloat(wMatch[1].replace(',', '.'));
          }
          continue;
        }

        // Encabezado H2
        if (stripped.startsWith('## ')) {
          flushNote();
          lastTaskObj = null;
          const header = stripped.slice(3).trim();
          if (header.includes('Topics') || header.includes('🎯')) {
            currentSection = 'topics';
            currentDayNum = null;
          } else if (header.includes('Week Tasks') || header.includes('Weekly Tasks') || header.includes('📋') || header.includes('Tareas')) {
            currentSection = 'week_tasks';
            currentDayNum = null;
          } else if (header.includes('Notes') || header.includes('📝')) {
            currentSection = 'notes';
            currentDayNum = null;
          } else if (header.includes('Definicion') || header.includes('🔗')) {
            currentSection = 'definitions';
            currentDayNum = null;
          } else {
            const dMatch = header.match(/\b(\d{1,2})\b/);
            if (dMatch) {
              currentSection = 'day';
              currentDayNum = parseInt(dMatch[1], 10);
              const emojiMatch = header.match(/^([^\w\s\d()]+?)\s*\b\d{1,2}\b/);
              const emoji = emojiMatch ? emojiMatch[1].trim() : '🏠';
              const noteMatch = header.match(/\(([^)]+)\)/);
              const locNote = noteMatch ? noteMatch[1].trim() : null;
              if (!daysMap.has(currentDayNum)) {
                daysOrder.push(currentDayNum);
                daysMap.set(currentDayNum, {
                  day_number: currentDayNum,
                  location_emoji: emoji,
                  location_note: locNote,
                  tasks: []
                });
              }
            } else {
              currentSection = null;
              currentDayNum = null;
            }
          }
          continue;
        }

        if (!stripped || stripped.startsWith('---') || stripped.startsWith('<!--')) {
          continue;
        }

        // Definiciones [🎫ID]: url
        const defMatch = line.match(/^\s*(\[[^\]\n]+\]):\s*(\S.*)$/);
        if (defMatch) {
          definitions.push({
            id: defMatch[1].trim(),
            url: defMatch[2].trim()
          });
          continue;
        }

        if (currentSection === 'topics') {
          const mItem = line.match(/^\s*-\s*(?:\[[ xX]\]\s*)?(.*)$/);
          if (mItem) {
            const rawTopic = mItem[1].trim();
            if (rawTopic && !rawTopic.startsWith('---')) {
              const { project_id, clean_title } = this.parseProjectTag(rawTopic);
              topics.push({
                id: `TOP-GH-${String(topics.length + 1).padStart(4, '0')}`,
                title: clean_title,
                project_id,
                status: 'active'
              });
            }
          }
        } else if (currentSection === 'week_tasks' || (currentSection === 'day' && currentDayNum !== null)) {
          const targetList = currentSection === 'week_tasks' ? weekTasks : daysMap.get(currentDayNum).tasks;
          const mChk = line.match(/^(\s*)-\s*\[([ xX])\]\s*(.*)$/);
          if (mChk) {
            const tText = mChk[3].trim();
            if (tText) {
              const tObj = makeTask(tText, mChk[2].toLowerCase() === 'x');
              targetList.push(tObj);
              lastTaskObj = { task: tObj, indent: mChk[1].length };
            }
          } else if (
            lastTaskObj &&
            line.search(/\S/) >= Math.max(4, lastTaskObj.indent + 2) &&
            /^[-*]\s+/.test(stripped) &&
            !/^[-*]\s*\[[ xX]\]/.test(stripped)
          ) {
            const subText = stripped.replace(/^[-*]\s+/, '').trim();
            if (subText) {
              lastTaskObj.task.description = lastTaskObj.task.description
                ? `${lastTaskObj.task.description}\n${subText}`
                : subText;
            }
          }
        } else if (currentSection === 'notes') {
          if (stripped.startsWith('### ') || stripped.startsWith('- ### ')) {
            flushNote();
            const rawH = stripped.startsWith('- ### ') ? stripped.slice(6).trim() : stripped.slice(4).trim();
            const { project_id, clean_title } = this.parseProjectTag(rawH);
            currentNote = {
              id: `NOTE-GH-${String(notes.length + 1).padStart(4, '0')}`,
              title: clean_title || 'Nota',
              project_id,
              content: []
            };
          } else if (stripped.startsWith('- ')) {
            const bullet = stripped.slice(2).trim();
            if (bullet) {
              if (!currentNote) {
                currentNote = {
                  id: `NOTE-GH-${String(notes.length + 1).padStart(4, '0')}`,
                  title: 'Notas Generales',
                  project_id: null,
                  content: []
                };
              }
              currentNote.content.push(bullet);
            }
          }
        }
      }
      flushNote();

      // Enriquecer días con letras L,M,X,J,V,S,D
      const isoDayMap = {};
      for (let isoD = 1; isoD <= 7; isoD++) {
        const dt = getDateFromIsoWeek(year, weekNumber, isoD);
        isoDayMap[dt.getUTCDate()] = isoD;
      }

      const firstDayDate = getDateFromIsoWeek(year, weekNumber, 1);
      const days = daysOrder.map((dNum, idx) => {
        const dObj = daysMap.get(dNum);
        const isoIdx = isoDayMap[dNum] || ((idx % 7) + 1);
        return {
          day_number: dObj.day_number,
          weekday_letter: WEEKDAY_LETTERS[isoIdx] || 'L',
          weekday_name: WEEKDAY_NAMES[isoIdx] || 'Día',
          location_emoji: dObj.location_emoji || '🏠',
          location_note: dObj.location_note || null,
          task_count: dObj.tasks.length,
          tasks: dObj.tasks
        };
      });

      return {
        frontmatter,
        year,
        week_number: weekNumber,
        month: firstDayDate.getUTCMonth() + 1,
        weight,
        days,
        week_tasks: weekTasks,
        topics,
        notes,
        definitions
      };
    },

    renderWeekMarkdown(stateObj) {
      const lines = [];
      const weightSuffix = stateObj.weight ? ` ${stateObj.weight}` : '';
      lines.push(`# 🗓️Week ${stateObj.week_number}${weightSuffix}\n`);

      // 1. Topics
      lines.push('## 🎯Topics');
      if (stateObj.topics && stateObj.topics.length > 0) {
        for (const top of stateObj.topics) {
          const projPrefix = top.project_id ? `[${top.project_id}] ` : '';
          lines.push(`  - ${projPrefix}${top.title}`);
        }
      } else {
        lines.push('  - ');
      }
      lines.push('  ---\n');

      const formatTask = (task) => {
        const premojiPart = task.premoji ? `${task.premoji} ` : '';
        const projPart = task.project_id ? ` #[${task.project_id}]` : '';
        const fullTitle = `${premojiPart}${task.title}${projPart}`.trim();
        let line = `  - [ ] ${fullTitle}`;
        if (task.status === 'done' || task.is_done) {
          line = `  - [x] ${fullTitle}`;
        } else if (task.status === 'cancelled' || task.is_cancelled) {
          line = `  - [ ] ~~${fullTitle}~~`;
        }
        if (task.description) {
          const descLines = String(task.description)
            .split(/\r?\n/)
            .map((d) => d.trim())
            .filter(Boolean)
            .map((d) => `    - ${d}`);
          if (descLines.length > 0) {
            return `${line}\n${descLines.join('\n')}`;
          }
        }
        return line;
      };

      // 2. Week Tasks
      lines.push('## 📋Week Tasks');
      if (stateObj.week_tasks && stateObj.week_tasks.length > 0) {
        for (const t of stateObj.week_tasks) {
          lines.push(formatTask(t));
        }
      } else {
        lines.push('  - [ ] ');
      }
      lines.push('  ---\n');

      // 3. Notes
      lines.push('## 📝Notes');
      if (stateObj.notes && stateObj.notes.length > 0) {
        for (const n of stateObj.notes) {
          const projPrefix = n.project_id ? `[${n.project_id}] ` : '';
          lines.push(`- ### ${projPrefix}${n.title || 'Nota'}`);
          for (const b of n.content || []) {
            lines.push(`  - ${b}`);
          }
        }
      } else {
        lines.push('  - ');
      }
      lines.push('  ---\n');

      // 4. Days
      for (const day of stateObj.days || []) {
        const noteSuffix = day.location_note ? ` (${day.location_note})` : '';
        lines.push(`## ${day.location_emoji || '🏠'}${day.day_number}${noteSuffix}`);
        if (day.tasks && day.tasks.length > 0) {
          for (const t of day.tasks) {
            lines.push(formatTask(t));
          }
        } else {
          lines.push('  - ');
        }
        lines.push('');
      }

      // 5. Definiciones
      lines.push('## Definiciones');
      lines.push('<!-- Definiciones -->');
      for (const d of stateObj.definitions || []) {
        const idFormatted = d.id.startsWith('[') ? d.id : `[${d.id}]`;
        lines.push(`${idFormatted}: ${d.url}`);
      }

      const body = lines.join('\n').trim() + '\n';
      return (stateObj.frontmatter || '') + body;
    },

    createEmptyWeekState(year, weekNumber, vault, calendarConfig) {
      const daysCount = Number(vault.days_per_week) || (vault.vault_type === 'personal' ? 7 : 5);
      const firstDay = getDateFromIsoWeek(year, weekNumber, 1);
      const days = [];
      for (let i = 0; i < daysCount; i++) {
        const dt = getDateFromIsoWeek(year, weekNumber, i + 1);
        const { emoji, note } = resolveDayLocation(dt, weekNumber, calendarConfig, vault.vault_type);
        days.push({
          day_number: dt.getUTCDate(),
          weekday_letter: WEEKDAY_LETTERS[i + 1] || 'L',
          weekday_name: WEEKDAY_NAMES[i + 1] || 'Día',
          location_emoji: emoji || (vault.vault_type === 'personal' ? '🌱' : '🏠'),
          location_note: note || null,
          task_count: 0,
          tasks: []
        });
      }
      return {
        frontmatter: '',
        year,
        week_number: weekNumber,
        month: firstDay.getUTCMonth() + 1,
        weight: null,
        days,
        week_tasks: [],
        topics: [],
        notes: [],
        definitions: []
      };
    }
  };

  // ===========================================================================
  // 6. Motor de Operaciones de Vault sobre GitHub API (GitHubVaultEngine)
  // ===========================================================================
  const GitHubVaultEngine = {
    activeWeekCache: new Map(),
    calendarCache: new Map(),

    async getWorkCalendar(vault) {
      if (this.calendarCache.has(vault.id)) {
        return this.calendarCache.get(vault.id);
      }
      let cal = null;
      try {
        const fileData = await GitHubRestClient.getFile(vault, 'data/work_calendar.yaml');
        if (fileData && fileData.content) {
          cal = parseWorkCalendarYaml(fileData.content);
        }
      } catch (_) {}
      if (!cal) {
        cal = getDefaultWorkCalendar(vault.vault_type);
      }
      this.calendarCache.set(vault.id, cal);
      return cal;
    },

    async listAvailableWeeks(vault) {
      const items = await GitHubRestClient.listContents(vault, '');
      const weeks = [];
      for (const item of items) {
        if (item.type === 'file') {
          const parsed = parseWeekFilename(item.name);
          if (parsed) {
            GitHubRestClient.shaCache.set(GitHubRestClient._cacheKey(vault, item.name), item.sha);
            weeks.push(parsed);
          }
        }
      }
      weeks.sort((a, b) => (b.year !== a.year ? b.year - a.year : b.week_number - a.week_number));
      return weeks;
    },

    async loadOrCreateWeek(vault, year = null, weekNumber = null) {
      const weeks = await this.listAvailableWeeks(vault);
      const nowIso = getIsoWeekInfo(new Date());

      let targetYear = year ? Number(year) : null;
      let targetWeek = weekNumber ? Number(weekNumber) : null;
      let targetFile = null;

      if (targetYear && targetWeek) {
        const found = weeks.find((w) => w.year === targetYear && w.week_number === targetWeek);
        if (found) targetFile = found.file;
      } else if (weeks.length > 0) {
        targetYear = weeks[0].year;
        targetWeek = weeks[0].week_number;
        targetFile = weeks[0].file;
      } else {
        targetYear = nowIso.year;
        targetWeek = nowIso.week_number;
      }

      if (!targetFile) {
        const firstDay = getDateFromIsoWeek(targetYear, targetWeek, 1);
        targetFile = formatWeekFilename(targetYear, firstDay.getUTCMonth() + 1, targetWeek);
      }

      let parsedWeek;
      try {
        const fileData = await GitHubRestClient.getFile(vault, targetFile, { useCache: true });
        parsedWeek = BitacoraMarkdownCodec.parseWeekMarkdown(fileData.content, targetYear, targetWeek, vault);
      } catch (err) {
        if (err.status === 404) {
          const calConfig = await this.getWorkCalendar(vault);
          parsedWeek = BitacoraMarkdownCodec.createEmptyWeekState(targetYear, targetWeek, vault, calConfig);
          const initialMd = BitacoraMarkdownCodec.renderWeekMarkdown(parsedWeek);
          await GitHubRestClient.putFile(vault, targetFile, initialMd, `chore: create bitacora ${targetFile}`);
          const existsInList = weeks.some((w) => w.year === targetYear && w.week_number === targetWeek);
          if (!existsInList) {
            weeks.unshift({
              year: targetYear,
              month: parsedWeek.month,
              week_number: targetWeek,
              key: `${targetYear}-W${String(targetWeek).padStart(2, '0')}`,
              file: targetFile
            });
          }
        } else {
          throw err;
        }
      }

      parsedWeek.file = targetFile;
      parsedWeek.available_weeks = weeks;
      this.activeWeekCache.set(vault.id, parsedWeek);
      return parsedWeek;
    },

    async saveWeekState(vault, weekState, commitMsg) {
      const md = BitacoraMarkdownCodec.renderWeekMarkdown(weekState);
      await GitHubRestClient.putFile(vault, weekState.file, md, commitMsg);
      this.activeWeekCache.set(vault.id, weekState);
    },

    async getHubData(vault, { dayNumber = null, year = null, weekNumber = null } = {}) {
      const weekState = await this.loadOrCreateWeek(vault, year, weekNumber);
      const todayDate = new Date().getDate();

      let activeDay = null;
      if (dayNumber !== null && !Number.isNaN(Number(dayNumber))) {
        activeDay = weekState.days.find((d) => d.day_number === Number(dayNumber)) || null;
      }
      if (!activeDay) {
        activeDay = weekState.days.find((d) => d.day_number === todayDate) || weekState.days[0] || null;
      }

      const daysData = weekState.days.map((d) => ({
        day_number: d.day_number,
        weekday_letter: d.weekday_letter,
        weekday_name: d.weekday_name,
        location_emoji: d.location_emoji,
        location_note: d.location_note,
        is_active: Boolean(activeDay && d.day_number === activeDay.day_number),
        is_today: d.day_number === todayDate,
        task_count: d.tasks.length,
        tasks: d.tasks
      }));

      const projSet = new Set(['GENERAL']);
      weekState.topics.forEach((t) => t.project_id && projSet.add(t.project_id));
      weekState.week_tasks.forEach((t) => t.project_id && projSet.add(t.project_id));
      weekState.days.forEach((d) => d.tasks.forEach((t) => t.project_id && projSet.add(t.project_id)));

      return {
        vault: {
          name: vault.name,
          path: `${vault.owner}/${vault.repo} (${vault.branch})`,
          storage_mode: 'github',
          id: vault.id
        },
        week: {
          year: weekState.year,
          week_number: weekState.week_number,
          month: weekState.month,
          weight: weekState.weight,
          file: weekState.file
        },
        active_day: activeDay
          ? {
              day_number: activeDay.day_number,
              location_emoji: activeDay.location_emoji,
              location_note: activeDay.location_note
            }
          : null,
        days: daysData,
        today_tasks: activeDay ? activeDay.tasks : [],
        week_tasks: weekState.week_tasks,
        notes: weekState.notes,
        topics: weekState.topics,
        definitions: weekState.definitions,
        available_weeks: weekState.available_weeks || [],
        projects: Array.from(projSet).map((code) => ({ id: code, name: code })),
        top_menu: DEFAULT_WEB_TOP_MENU
      };
    },

    findTaskInWeek(weekState, taskId) {
      const wIdx = weekState.week_tasks.findIndex((t) => t.id === taskId);
      if (wIdx >= 0) {
        return { list: weekState.week_tasks, index: wIdx, task: weekState.week_tasks[wIdx], day: null };
      }
      for (const d of weekState.days) {
        const dIdx = d.tasks.findIndex((t) => t.id === taskId);
        if (dIdx >= 0) {
          return { list: d.tasks, index: dIdx, task: d.tasks[dIdx], day: d };
        }
      }
      return null;
    },

    async handleApiRequest(vault, method, pathname, searchParams, bodyObj) {
      // 1. GET /api/hub
      if (method === 'GET' && pathname === '/api/hub') {
        const dayParam = searchParams.get('day');
        const yearParam = searchParams.get('year');
        const weekParam = searchParams.get('week');
        return await this.getHubData(vault, {
          dayNumber: dayParam ? Number(dayParam) : null,
          year: yearParam ? Number(yearParam) : null,
          weekNumber: weekParam ? Number(weekParam) : null
        });
      }

      // 2. POST /api/sync o /api/sync/all
      if (method === 'POST' && (pathname === '/api/sync' || pathname === '/api/sync/all')) {
        GitHubRestClient.clearCache();
        const yearParam = bodyObj && bodyObj.year ? Number(bodyObj.year) : null;
        const weekParam = bodyObj && bodyObj.week ? Number(bodyObj.week) : null;
        const refreshed = await this.loadOrCreateWeek(vault, yearParam, weekParam);
        return { status: 'ok', success: true, synced: 1, file: refreshed.file, mode: 'github' };
      }

      // Obtener semana activa en memoria o cargarla
      let weekState = this.activeWeekCache.get(vault.id);
      if (!weekState) {
        weekState = await this.loadOrCreateWeek(
          vault,
          bodyObj && bodyObj.year ? Number(bodyObj.year) : null,
          bodyObj && bodyObj.week ? Number(bodyObj.week) : null
        );
      }

      // 3. POST /api/tasks (Crear tarea)
      if (method === 'POST' && pathname === '/api/tasks') {
        const rawTitle = (bodyObj.title || '').trim();
        if (!rawTitle) throw new Error('El título de la tarea es obligatorio.');
        const { task_type, premoji, clean_title: afterType } = BitacoraMarkdownCodec.detectTaskTypeAndCleanTitle(rawTitle);
        const { project_id, clean_title } = BitacoraMarkdownCodec.parseProjectTag(afterType);
        const initialStatus = bodyObj.is_done === true ? 'done' : (bodyObj.status || 'pending');
        const newTask = syncTaskFlags({
          id: `TSK-GH-${Date.now().toString().slice(-4)}`,
          title: clean_title,
          status: initialStatus,
          task_type: bodyObj.task_type || task_type,
          premoji,
          project_id: bodyObj.project_id || project_id || null,
          description: (bodyObj.description || '').trim() || null
        });

        const rawTarget = String(bodyObj.target || '');
        if (rawTarget === 'week') {
          weekState.week_tasks.push(newTask);
        } else {
          let targetDayNum = bodyObj.day_number ?? bodyObj.day ?? null;
          if (rawTarget.startsWith('day:')) {
            targetDayNum = Number(rawTarget.slice(4));
          } else if (/^\d+$/.test(rawTarget)) {
            targetDayNum = Number(rawTarget);
          }
          const targetDay =
            (targetDayNum !== null && weekState.days.find((d) => d.day_number === Number(targetDayNum))) ||
            weekState.days.find((d) => d.day_number === new Date().getDate()) ||
            weekState.days[0];
          if (targetDay) targetDay.tasks.push(newTask);
          else weekState.week_tasks.push(newTask);
        }

        await this.saveWeekState(vault, weekState, `feat(task): add "${clean_title}"`);
        return { success: true, task: newTask };
      }

      // 4. Toggle Task: POST/PATCH /api/tasks/:id/toggle
      const mToggle = pathname.match(/^\/api\/tasks\/([^/]+)\/toggle$/);
      if (mToggle && (method === 'POST' || method === 'PATCH')) {
        const taskId = decodeURIComponent(mToggle[1]);
        const found = this.findTaskInWeek(weekState, taskId);
        if (!found) throw new Error(`Tarea ${taskId} no encontrada.`);
        found.task.status = found.task.status === 'done' ? 'pending' : 'done';
        syncTaskFlags(found.task);

        // Si era una tarea de la semana (sin día fijo) y se marca como resuelta, trasladarla automáticamente a hoy
        if (found.day === null && found.task.status === 'done') {
          found.list.splice(found.index, 1);
          found.task.is_week_task = false;
          const todayDate = new Date().getUTCDate();
          let targetDay = weekState.days.find((d) => d.day_number === todayDate);
          if (!targetDay && weekState.days.length > 0) {
            targetDay = weekState.days[0];
          }
          if (targetDay) {
            found.task.day_number = targetDay.day_number;
            targetDay.tasks.push(found.task);
          } else {
            weekState.week_tasks.push(found.task);
          }
        }

        await this.saveWeekState(vault, weekState, `chore(task): toggle "${found.task.title}" -> ${found.task.status}`);
        return { success: true, new_status: found.task.status, task: found.task };
      }

      // 5. Edit / Delete Task: PATCH/DELETE /api/tasks/:id
      const mTask = pathname.match(/^\/api\/tasks\/([^/]+)$/);
      if (mTask) {
        const taskId = decodeURIComponent(mTask[1]);
        const found = this.findTaskInWeek(weekState, taskId);
        if (!found) throw new Error(`Tarea ${taskId} no encontrada.`);

        if (method === 'DELETE') {
          found.list.splice(found.index, 1);
          await this.saveWeekState(vault, weekState, `chore(task): delete "${found.task.title}"`);
          return { success: true, deleted_id: taskId };
        }

        if (method === 'PATCH') {
          if (bodyObj.title !== undefined) {
            const { task_type, premoji, clean_title: afterType } = BitacoraMarkdownCodec.detectTaskTypeAndCleanTitle(bodyObj.title);
            const { project_id, clean_title } = BitacoraMarkdownCodec.parseProjectTag(afterType);
            found.task.title = clean_title;
            if (task_type !== 'task') {
              found.task.task_type = task_type;
              found.task.premoji = premoji;
            }
            if (project_id) found.task.project_id = project_id;
          }
          if (bodyObj.status !== undefined) {
            found.task.status = bodyObj.status;
            syncTaskFlags(found.task);
          }
          if (bodyObj.description !== undefined) found.task.description = (bodyObj.description || '').trim() || null;

          const target = bodyObj.target;
          if (target !== undefined || bodyObj.day_number !== undefined) {
            found.list.splice(found.index, 1);
            if (target === 'week' || bodyObj.day_number === 'week' || bodyObj.day_number === null) {
              found.task.is_week_task = true;
              found.task.day_number = null;
              weekState.week_tasks.push(found.task);
            } else if (target === 'today') {
              found.task.is_week_task = false;
              const todayDate = new Date().getUTCDate();
              let destDay = weekState.days.find((d) => d.day_number === todayDate) || weekState.days[0];
              if (destDay) {
                found.task.day_number = destDay.day_number;
                destDay.tasks.push(found.task);
              } else {
                weekState.week_tasks.push(found.task);
              }
            } else {
              const dNum = target && String(target).startsWith('day:') ? Number(target.replace('day:', '')) : Number(bodyObj.day_number);
              const destDay = weekState.days.find((d) => d.day_number === dNum);
              if (destDay) {
                found.task.is_week_task = false;
                found.task.day_number = dNum;
                destDay.tasks.push(found.task);
              } else {
                weekState.week_tasks.push(found.task);
              }
            }
          }

          await this.saveWeekState(vault, weekState, `chore(task): update "${found.task.title}"`);
          return { success: true, task: found.task };
        }
      }

      // 6. Cambiar ubicación del día: POST/PATCH /api/days/:day/location
      const mLoc = pathname.match(/^\/api\/days\/(\d+)\/location$/);
      if (mLoc && (method === 'POST' || method === 'PATCH')) {
        const dayNum = Number(mLoc[1]);
        const dayObj = weekState.days.find((d) => d.day_number === dayNum);
        if (!dayObj) throw new Error(`Día ${dayNum} no encontrado.`);
        dayObj.location_emoji = bodyObj.emoji || bodyObj.location_emoji || '🏠';
        if (bodyObj.location_note !== undefined) {
          dayObj.location_note = bodyObj.location_note || null;
        }
        await this.saveWeekState(vault, weekState, `chore(day): update location for day ${dayNum}`);
        return { success: true, day_number: dayNum, location_emoji: dayObj.location_emoji };
      }

      // 7. Topics CRUD: /api/topics
      if (pathname === '/api/topics' && method === 'POST') {
        const rawTitle = (bodyObj.title || '').trim();
        const { project_id, clean_title } = BitacoraMarkdownCodec.parseProjectTag(rawTitle);
        const newTop = {
          id: `TOP-GH-${Date.now().toString().slice(-4)}`,
          title: clean_title,
          project_id: bodyObj.project_id || project_id || null,
          status: 'active'
        };
        weekState.topics.push(newTop);
        await this.saveWeekState(vault, weekState, `feat(topic): add "${clean_title}"`);
        return { success: true, topic: newTop };
      }
      const mTopic = pathname.match(/^\/api\/topics\/([^/]+)$/);
      if (mTopic) {
        const topId = decodeURIComponent(mTopic[1]);
        const idx = weekState.topics.findIndex((t) => t.id === topId);
        if (idx < 0) throw new Error(`Topic ${topId} no encontrado.`);
        if (method === 'DELETE') {
          weekState.topics.splice(idx, 1);
          await this.saveWeekState(vault, weekState, `chore(topic): remove topic`);
          return { success: true };
        }
        if (method === 'PATCH') {
          const { project_id, clean_title } = BitacoraMarkdownCodec.parseProjectTag(bodyObj.title || weekState.topics[idx].title);
          weekState.topics[idx].title = clean_title;
          if (project_id || bodyObj.project_id) weekState.topics[idx].project_id = bodyObj.project_id || project_id;
          await this.saveWeekState(vault, weekState, `chore(topic): update "${clean_title}"`);
          return { success: true, topic: weekState.topics[idx] };
        }
      }

      // 8. Notes CRUD: /api/notes
      if (pathname === '/api/notes' && method === 'POST') {
        const { project_id, clean_title } = BitacoraMarkdownCodec.parseProjectTag(bodyObj.title || 'Nota');
        const bullets = Array.isArray(bodyObj.content)
          ? bodyObj.content
          : String(bodyObj.content || '')
              .split(/\r?\n/)
              .map((l) => l.trim().replace(/^[-*•]\s*/, ''))
              .filter(Boolean);
        const newNote = {
          id: `NOTE-GH-${Date.now().toString().slice(-4)}`,
          title: clean_title,
          project_id: bodyObj.project_id || project_id || null,
          content: bullets
        };
        weekState.notes.push(newNote);
        await this.saveWeekState(vault, weekState, `feat(note): add "${clean_title}"`);
        return { success: true, note: newNote };
      }
      const mNote = pathname.match(/^\/api\/notes\/([^/]+)$/);
      if (mNote) {
        const noteId = decodeURIComponent(mNote[1]);
        const idx = weekState.notes.findIndex((n) => n.id === noteId);
        if (idx < 0) throw new Error(`Nota ${noteId} no encontrada.`);
        if (method === 'DELETE') {
          weekState.notes.splice(idx, 1);
          await this.saveWeekState(vault, weekState, `chore(note): delete note`);
          return { success: true };
        }
        if (method === 'PATCH') {
          if (bodyObj.title !== undefined) {
            const { project_id, clean_title } = BitacoraMarkdownCodec.parseProjectTag(bodyObj.title);
            weekState.notes[idx].title = clean_title;
            if (project_id) weekState.notes[idx].project_id = project_id;
          }
          if (bodyObj.content !== undefined) {
            weekState.notes[idx].content = Array.isArray(bodyObj.content)
              ? bodyObj.content
              : String(bodyObj.content || '')
                  .split(/\r?\n/)
                  .map((l) => l.trim().replace(/^[-*•]\s*/, ''))
                  .filter(Boolean);
          }
          await this.saveWeekState(vault, weekState, `chore(note): update "${weekState.notes[idx].title}"`);
          return { success: true, note: weekState.notes[idx] };
        }
      }

      // 9. Definitions CRUD: /api/definitions
      if (pathname === '/api/definitions' && method === 'POST') {
        let code = (bodyObj.id || bodyObj.code || '').trim();
        let url = (bodyObj.url || '').trim();

        // Auto-extract Jira ticket si code está vacío o si code es una URL
        if (!code && url) {
          const m = url.match(/(?:browse\/|issues?\/|selectedIssue=|key=|^|[\/?#&])([A-Za-z][A-Za-z0-9_]*-\d+)(?:[/&#? ]|$)/i);
          if (m) code = m[1].toUpperCase();
        } else if (code.startsWith('http://') || code.startsWith('https://')) {
          const m = code.match(/(?:browse\/|issues?\/|selectedIssue=|key=|^|[\/?#&])([A-Za-z][A-Za-z0-9_]*-\d+)(?:[/&#? ]|$)/i);
          if (m) {
            if (!url) url = code;
            code = m[1].toUpperCase();
          }
        }

        const cleanTicket = code.replace(/[\[\]🎫]/g, '').trim();
        if (/^[A-Za-z][A-Za-z0-9_]*-\d+$/i.test(cleanTicket)) {
          code = `[🎫${cleanTicket.toUpperCase()}]`;
          if (!url) url = `https://jira.example.com/browse/${cleanTicket.toUpperCase()}`;
        } else if (!code.startsWith('[')) {
          code = `[${code}]`;
        }

        const existingIdx = weekState.definitions.findIndex((d) => d.id === code);
        if (existingIdx >= 0) weekState.definitions[existingIdx].url = url;
        else weekState.definitions.push({ id: code, url });
        await this.saveWeekState(vault, weekState, `feat(def): save definition ${code}`);
        return { success: true, definition: { id: code, url } };
      }
      const mDef = pathname.match(/^\/api\/definitions\/(.+)$/);
      if (mDef) {
        const defId = decodeURIComponent(mDef[1]);
        const idx = weekState.definitions.findIndex((d) => d.id === defId || d.id === `[${defId}]`);
        if (idx < 0) throw new Error(`Definición ${defId} no encontrada.`);
        if (method === 'DELETE') {
          weekState.definitions.splice(idx, 1);
          await this.saveWeekState(vault, weekState, `chore(def): remove ${defId}`);
          return { success: true };
        }
        if (method === 'PATCH') {
          if (bodyObj.id) weekState.definitions[idx].id = bodyObj.id.startsWith('[') ? bodyObj.id : `[${bodyObj.id}]`;
          if (bodyObj.url) weekState.definitions[idx].url = bodyObj.url;
          await this.saveWeekState(vault, weekState, `chore(def): update ${defId}`);
          return { success: true, definition: weekState.definitions[idx] };
        }
      }

      // 10. Reordenar elementos: POST /api/reorder
      if (pathname === '/api/reorder' && method === 'POST') {
        const ids = Array.isArray(bodyObj.ids) ? bodyObj.ids : (Array.isArray(bodyObj.ordered_ids) ? bodyObj.ordered_ids : []);
        const rType = bodyObj.type;
        const reorderArray = (arr) => {
          const map = new Map(arr.map((item) => [item.id, item]));
          const reordered = ids.map((id) => map.get(id)).filter(Boolean);
          arr.forEach((item) => {
            if (!ids.includes(item.id)) reordered.push(item);
          });
          return reordered;
        };
        if ((rType === 'today_tasks' || rType === 'day_tasks') && bodyObj.day_number !== undefined) {
          const d = weekState.days.find((day) => day.day_number === Number(bodyObj.day_number));
          if (d) d.tasks = reorderArray(d.tasks);
        } else if (rType === 'week_tasks') {
          weekState.week_tasks = reorderArray(weekState.week_tasks);
        } else if (rType === 'topics') {
          weekState.topics = reorderArray(weekState.topics);
        } else if (rType === 'notes') {
          weekState.notes = reorderArray(weekState.notes);
        } else if (rType === 'definitions') {
          weekState.definitions = reorderArray(weekState.definitions);
        }
        await this.saveWeekState(vault, weekState, `chore: reorder ${rType}`);
        return { success: true };
      }

      // 11. Semanas: GET /api/weeks, POST /api/weeks/next, POST /api/weeks/extra-day
      if (pathname === '/api/weeks' && method === 'GET') {
        const weeks = await this.listAvailableWeeks(vault);
        return { weeks };
      }
      if (pathname === '/api/weeks/next' && method === 'POST') {
        const nextWeekNum = weekState.week_number >= 52 ? 1 : weekState.week_number + 1;
        const nextYear = weekState.week_number >= 52 ? weekState.year + 1 : weekState.year;
        const calConfig = await this.getWorkCalendar(vault);
        const nextState = BitacoraMarkdownCodec.createEmptyWeekState(nextYear, nextWeekNum, vault, calConfig);
        nextState.topics = [...weekState.topics];
        const pendingTasks = [
          ...weekState.week_tasks.filter((t) => t.status === 'pending'),
          ...weekState.days.flatMap((d) => d.tasks.filter((t) => t.status === 'pending'))
        ];
        nextState.week_tasks = pendingTasks;
        const nextFile = formatWeekFilename(nextYear, nextState.month, nextWeekNum);
        nextState.file = nextFile;
        await this.saveWeekState(vault, nextState, `feat(week): create ${nextFile} with rollover`);
        return {
          success: true,
          year: nextYear,
          week_number: nextWeekNum,
          file: nextFile,
          rolled_over_tasks: pendingTasks.length,
          injected_recurring: 0
        };
      }
      if (pathname === '/api/weeks/extra-day' && method === 'POST') {
        const dNum = Number(bodyObj.day_number);
        const existing = weekState.days.find((d) => d.day_number === dNum);
        if (!existing) {
          weekState.days.push({
            day_number: dNum,
            weekday_letter: 'S',
            weekday_name: 'Día Extra',
            location_emoji: bodyObj.location_emoji || '🛠️',
            location_note: bodyObj.location_note || null,
            task_count: 0,
            tasks: []
          });
        }
        await this.saveWeekState(vault, weekState, `feat(day): add extra day ${dNum}`);
        return { success: true, day_number: dNum };
      }

      // 12. Ideas: GET/POST /api/ideas
      if (pathname === '/api/ideas') {
        const ideasFile = '[🧩GENERAL]🧠Ideas.md';
        if (method === 'GET') {
          try {
            const f = await GitHubRestClient.getFile(vault, ideasFile);
            const ideas = [];
            let curProj = 'GENERAL';
            f.content.split(/\r?\n/).forEach((l) => {
              const s = l.trim();
              if (s.startsWith('## ')) curProj = s.replace(/^##\s*📁?\s*/, '').trim() || 'GENERAL';
              const m = s.match(/^-\s*\[([ xX])\]\s*(.*)$/);
              if (m && m[2].trim()) {
                ideas.push({
                  id: `IDEA-${ideas.length + 1}`,
                  title: m[2].trim(),
                  status: m[1].toLowerCase() === 'x' ? 'accepted' : 'evaluating',
                  project_id: curProj,
                  content: []
                });
              }
            });
            return { ideas };
          } catch (e) {
            return { ideas: [] };
          }
        }
        if (method === 'POST') {
          let currentMd = '# 🧠Ideas\n\n## 📁 GENERAL\n';
          try {
            const f = await GitHubRestClient.getFile(vault, ideasFile);
            currentMd = f.content;
          } catch (_) {}
          const newLine = `- [ ] ${(bodyObj.title || '').trim()}\n`;
          const updatedMd = currentMd.trimEnd() + '\n' + newLine;
          await GitHubRestClient.putFile(vault, ideasFile, updatedMd, `feat(idea): add idea`);
          return { success: true, idea: { id: `IDEA-${Date.now()}`, title: bodyObj.title, status: 'evaluating' } };
        }
      }

      // 13. Proyectos Resumen: GET /api/projects
      if (pathname === '/api/projects' && method === 'GET') {
        const map = new Map();
        const allTasks = [...weekState.week_tasks, ...weekState.days.flatMap((d) => d.tasks)];
        for (const t of allTasks) {
          const pid = t.project_id || 'GENERAL';
          if (!map.has(pid)) {
            map.set(pid, { id: pid, name: pid, total_tasks: 0, done_tasks: 0, pending_tasks: 0, backlog_count: 0, notes_count: 0, progress_pct: 0 });
          }
          const entry = map.get(pid);
          entry.total_tasks++;
          if (t.status === 'done') entry.done_tasks++;
          else if (t.status === 'pending') entry.pending_tasks++;
        }
        map.forEach((v) => {
          v.progress_pct = v.total_tasks > 0 ? Math.round((v.done_tasks / v.total_tasks) * 100) : 0;
        });
        return { projects: Array.from(map.values()) };
      }

      return { success: true };
    }
  };

  // ===========================================================================
  // 7. Interceptor Híbrido de Fetch (Local Server + GitHub REST API v3)
  // ===========================================================================
  function makeJsonResponse(data, status = 200) {
    return new Response(JSON.stringify(data), {
      status,
      headers: { 'Content-Type': 'application/json; charset=utf-8' }
    });
  }

  function installGitHubFetchInterceptor() {
    global.fetch = async function (input, init = {}) {
      const rawUrl = typeof input === 'string' ? input : input.url;
      let parsedUrl;
      try {
        parsedUrl = new URL(rawUrl, global.location.origin);
      } catch (_) {
        return originalFetch(input, init);
      }

      // Solo interceptar llamadas dirigidas a la API interna /api/*
      if (!parsedUrl.pathname.startsWith('/api/')) {
        return originalFetch(input, init);
      }

      const method = (init.method || 'GET').toUpperCase();
      let bodyObj = {};
      if (init.body && typeof init.body === 'string') {
        try {
          bodyObj = JSON.parse(init.body);
        } catch (_) {}
      }

      // 1. Interceptar GET /api/vaults para fusionar Vaults Locales + Vaults de GitHub
      if (method === 'GET' && parsedUrl.pathname === '/api/vaults') {
        let localVaults = [];
        let defaultVault = null;
        let localReachable = false;

        try {
          const localRes = await originalFetch(input, init);
          if (localRes.ok) {
            const localData = await localRes.json();
            localReachable = true;
            localVaults = (localData.vaults || []).map((v) =>
              Object.assign({}, v, { storage_mode: 'local', label: `${v.vault_type === 'personal' ? '🌱' : '💼'} ${v.name}` })
            );
            defaultVault = localData.default_vault;
          }
        } catch (_) {
          localReachable = false;
        }

        const remoteVaults = GitHubConfigStore.getRemoteVaults().map((rv) => ({
          name: rv.id,
          label: rv.name,
          path: `${rv.owner}/${rv.repo}@${rv.branch}`,
          description: rv.description,
          exists: true,
          storage_mode: 'github',
          is_default: false
        }));

        const allVaults = [...localVaults, ...remoteVaults];
        const preferred = GitHubConfigStore.getPreferredVault();
        const validPreferred = allVaults.find((v) => v.name === preferred);

        let chosenDefault = defaultVault;
        if (validPreferred) {
          chosenDefault = validPreferred.name;
        } else if (!localReachable && remoteVaults.length > 0) {
          chosenDefault = remoteVaults[0].name;
        }

        return makeJsonResponse({
          default_vault: chosenDefault,
          local_reachable: localReachable,
          vaults: allVaults
        });
      }

      // Determinar el vault objetivo de la petición
      const vaultIdentifier =
        parsedUrl.searchParams.get('vault') ||
        bodyObj.vault ||
        GitHubConfigStore.getPreferredVault() ||
        '';

      if (vaultIdentifier) {
        GitHubConfigStore.setPreferredVault(vaultIdentifier);
      }

      // Si el vault NO es de GitHub, enviar al servidor Python local normalmente
      if (!GitHubConfigStore.isGitHubVault(vaultIdentifier)) {
        return originalFetch(input, init);
      }

      // Resolver configuración del repositorio remoto de GitHub
      const vaultCfg = GitHubConfigStore.getVaultById(vaultIdentifier);
      if (!vaultCfg) {
        return makeJsonResponse({ error: `Vault remoto de GitHub '${vaultIdentifier}' no encontrado.` }, 404);
      }

      if (!GitHubConfigStore.hasToken()) {
        if (typeof global.openGitHubSettingsModal === 'function') {
          setTimeout(() => global.openGitHubSettingsModal(), 100);
        }
        return makeJsonResponse({
          vault: { name: vaultCfg.name, path: `${vaultCfg.owner}/${vaultCfg.repo}`, storage_mode: 'github' },
          week: null,
          days: [],
          today_tasks: [],
          week_tasks: [],
          notes: [],
          topics: [],
          definitions: [],
          top_menu: DEFAULT_WEB_TOP_MENU,
          message: '🔑 Configura tu Personal Access Token (PAT) de GitHub para leer y escribir en este repositorio privado.'
        });
      }

      try {
        const result = await GitHubVaultEngine.handleApiRequest(
          vaultCfg,
          method,
          parsedUrl.pathname,
          parsedUrl.searchParams,
          bodyObj
        );
        return makeJsonResponse(result, method === 'POST' ? 201 : 200);
      } catch (err) {
        console.error('[GitHubAdapter Error]', err);
        return makeJsonResponse({ error: err.message || 'Error en comunicación con GitHub API' }, err.status || 500);
      }
    };
  }

  installGitHubFetchInterceptor();

  // Exportar en el objeto global para acceso desde la UI
  global.BracketsGitHub = {
    utf8ToBase64,
    base64ToUtf8,
    ConfigStore: GitHubConfigStore,
    RestClient: GitHubRestClient,
    MarkdownCodec: BitacoraMarkdownCodec,
    VaultEngine: GitHubVaultEngine
  };
})(window);
