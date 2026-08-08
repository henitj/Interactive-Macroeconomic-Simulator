/* ==========================================================================
   Simulation state — levers, runs, and state management
   ========================================================================== */

const Simulation = {
  current: null,        // last API result
  seed: null,
  isRunning: false,
  listeners: [],

  leverIds: [
    'interest_rate', 'inflation_target', 'money_supply_growth',
    'tax_rate', 'government_spending', 'supply_chain_friction',
    'sentiment',
  ],

  // Default lever values
  defaults: {
    interest_rate: 0.045,
    inflation_target: 0.02,
    money_supply_growth: 0.05,
    tax_rate: 0.22,
    government_spending: 0.20,
    supply_chain_friction: 0.10,
    sentiment: 0.55,
  },

  /**
   * Read levers from the sliders.
   * Sliders use percentage / 0-100 units; we convert to decimals for the API.
   */
  getLevers() {
    const get = (id) => {
      const el = document.getElementById(`rng-${id}`);
      return el ? parseFloat(el.value) : 0;
    };

    // interest_rate slider is in percent (-1 to 20)
    return {
      interest_rate: get('interest_rate') / 100,
      inflation_target: get('inflation_target') / 100,
      money_supply_growth: get('money_supply_growth') / 100,
      tax_rate: get('tax_rate') / 100,
      government_spending: get('government_spending') / 100,
      supply_chain_friction: get('supply_chain_friction') / 100,
      sentiment: get('sentiment') / 100,
    };
  },

  getHorizon() {
    return parseInt(document.getElementById('rng-horizon').value) || 5;
  },

  getVolatility() {
    return (parseInt(document.getElementById('rng-volatility').value) || 10) / 10;
  },

  /**
   * Apply a levers object (decimal) back to the sliders.
   */
  setLevers(levers) {
    const set = (id, val, scale = 100) => {
      const el = document.getElementById(`rng-${id}`);
      if (el) el.value = (val * scale).toFixed(2);
    };
    set('interest_rate', levers.interest_rate);
    set('inflation_target', levers.inflation_target);
    set('money_supply_growth', levers.money_supply_growth);
    set('tax_rate', levers.tax_rate);
    set('government_spending', levers.government_spending);
    set('supply_chain_friction', levers.supply_chain_friction);
    set('sentiment', levers.sentiment);
    this.updateLeverDisplays();
  },

  resetToDefaults() {
    this.setLevers(this.defaults);
    document.getElementById('rng-horizon').value = 5;
    document.getElementById('rng-volatility').value = 10;
    this.updateLeverDisplays();
  },

  /**
   * Update the numeric readouts next to each slider.
   */
  updateLeverDisplays() {
    const fmt = (id, val) => {
      const el = document.getElementById(`val-${id}`);
      if (!el) return;
      const map = {
        interest_rate: `${parseFloat(val).toFixed(2)}%`,
        inflation_target: `${parseFloat(val).toFixed(2)}%`,
        money_supply_growth: `${parseFloat(val).toFixed(2)}%`,
        tax_rate: `${parseFloat(val).toFixed(2)}%`,
        government_spending: `${parseFloat(val).toFixed(2)}%`,
        supply_chain_friction: `${Math.round(parseFloat(val))}%`,
        sentiment: `${Math.round(parseFloat(val))} / 100`,
      };
      el.textContent = map[id] || val;
    };

    this.leverIds.forEach(id => {
      const rng = document.getElementById(`rng-${id}`);
      if (rng) fmt(id, rng.value);
    });

    const horizon = document.getElementById('rng-horizon');
    const horizonVal = document.getElementById('val-horizon');
    if (horizon && horizonVal) {
      const y = parseInt(horizon.value);
      horizonVal.textContent = `${y} year${y > 1 ? 's' : ''}`;
    }

    const vol = document.getElementById('rng-volatility');
    const volVal = document.getElementById('val-volatility');
    if (vol && volVal) {
      volVal.textContent = `${(parseInt(vol.value) / 10).toFixed(1)}×`;
    }
  },

  /**
   * Run a simulation and store result.
   */
  async run() {
    if (this.isRunning) return;
    this.isRunning = true;
    this._setRunButton(true);

    try {
      const levers = this.getLevers();
      const months = this.getHorizon() * 12;
      const shockVol = this.getVolatility();

      // If no seed chosen, let backend pick (null). New Seed button sets one.
      const result = await Api.simulate(levers, {
        seed: this.seed,
        months,
        shockVolatility: shockVol,
      });

      this.current = result;
      this._notify(result);
      return result;
    } catch (err) {
      console.error('Simulation failed:', err);
      this._showError(err.message);
      throw err;
    } finally {
      this.isRunning = false;
      this._setRunButton(false);
    }
  },

  rerollSeed() {
    this.seed = Math.floor(Math.random() * 1_000_000);
    document.getElementById('ticker-seed').textContent = `seed ${this.seed}`;
  },

  subscribe(fn) { this.listeners.push(fn); },
  _notify(result) { this.listeners.forEach(fn => fn(result)); },

  _setRunButton(loading) {
    const btn = document.getElementById('btn-run');
    if (loading) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> Simulating...';
    } else {
      btn.disabled = false;
      btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg> Run Simulation';
    }
  },

  _showError(msg) {
    // Simple error display via insights panel
    const list = document.getElementById('insights-list');
    if (list) {
      list.innerHTML = `<div class="insight danger"><div class="insight__head"><span class="insight__title">Simulation Error</span></div><div class="insight__body">${msg}</div></div>`;
    }
  },
};
