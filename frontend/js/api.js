/* ==========================================================================
   API client — thin wrapper over fetch for the backend endpoints.
   In production the same origin serves both API + frontend.
   ========================================================================== */

const API_BASE = '';  // same origin

const Api = {
  async _post(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || `API error: ${res.status}`);
    }
    return res.json();
  },

  async _get(path) {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  simulate(levers, opts = {}) {
    return this._post('/api/simulate', {
      ...levers,
      seed: opts.seed,
      months: opts.months || 60,
      shock_volatility: opts.shockVolatility || 1.0,
    });
  },

  household(profile, history) {
    return this._post('/api/household', { profile, history });
  },

  scoreGame(simulation, config) {
    return this._post('/api/game/score', { simulation, config });
  },

  explainLever(lever, oldVal, newVal) {
    return this._post('/api/insights/explain', { lever, old: oldVal, new: newVal });
  },

  scenarios() {
    return this._get('/api/scenarios');
  },

  tooltips() {
    return this._get('/api/tooltips');
  },

  health() {
    return this._get('/api/health');
  },
};
