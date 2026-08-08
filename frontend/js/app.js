/* ==========================================================================
   App initialization — wire up UI, tabs, tooltips, ticker, and scenarios.
   ========================================================================== */

const App = {
  tooltips: {},
  scenarios: {},
  activeView: 'dashboard',

  async init() {
    // Initialize core modules
    Charts.init();
    Household.init();
    Game.init();

    // Wire up lever sliders
    this._initLevers();

    // Wire up buttons
    document.getElementById('btn-run')?.addEventListener('click', () => Simulation.run());
    document.getElementById('btn-reroll')?.addEventListener('click', () => {
      Simulation.rerollSeed();
      Simulation.run();
    });
    document.getElementById('btn-reset')?.addEventListener('click', () => {
      Simulation.resetToDefaults();
    });

    // Tabs
    document.querySelectorAll('.tab').forEach(tab => {
      tab.addEventListener('click', () => this._switchView(tab.dataset.view));
    });

    // Chart group tabs
    document.querySelectorAll('.chart-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.chart-tab').forEach(t => t.classList.remove('is-active'));
        tab.classList.add('is-active');
        Charts.showGroup(tab.dataset.chartGroup);
      });
    });

    // Load reference data
    await this._loadTooltips();
    await this._loadScenarios();

    // Initialize tooltips
    this._initTooltips();

    // Subscribe to simulation for ticker + insights
    Simulation.subscribe((result) => {
      this._updateTicker(result);
      this._updateInsights(result);
      this._updateTickerMeta(result);
    });

    // Initial lever display sync
    Simulation.updateLeverDisplays();

    // Auto-run on load
    Simulation.rerollSeed();
    Simulation.run();
  },

  _initLevers() {
    Simulation.leverIds.forEach(id => {
      const rng = document.getElementById(`rng-${id}`);
      if (rng) {
        rng.addEventListener('input', () => {
          Simulation.updateLeverDisplays();
        });
        rng.addEventListener('change', () => {
          // Explain the change via Edu-Engine
          const oldVal = this._lastLeverValues?.[id];
          const newVal = Simulation.getLevers()[id];
          if (oldVal !== undefined && Math.abs(oldVal - newVal) > 0.0001) {
            Api.explainLever(id, oldVal, newVal).then(exp => {
              this._showLeverExplanation(exp);
            }).catch(() => {});
          }
          this._lastLeverValues = Simulation.getLevers();
        });
      }
    });
    this._lastLeverValues = Simulation.getLevers();

    // Horizon / volatility
    ['horizon', 'volatility'].forEach(id => {
      const rng = document.getElementById(`rng-${id}`);
      if (rng) rng.addEventListener('input', () => Simulation.updateLeverDisplays());
    });
  },

  async _loadTooltips() {
    try {
      this.tooltips = await Api.tooltips();
    } catch {
      // Fallback: static tooltips
      this.tooltips = {};
    }
  },

  async _loadScenarios() {
    try {
      this.scenarios = await Api.scenarios();
      this._renderScenarios();
    } catch (err) {
      console.error('Failed to load scenarios:', err);
    }
  },

  _renderScenarios() {
    const grid = document.getElementById('scenario-grid');
    if (!grid) return;

    grid.innerHTML = Object.entries(this.scenarios).map(([key, s]) => {
      const L = s.levers;
      return `
        <div class="scenario-card" data-scenario="${key}">
          <div class="scenario-card__era">${s.name.split(' ')[0] || 'Scenario'}</div>
          <div class="scenario-card__title">${s.name}</div>
          <div class="scenario-card__desc">${s.description}</div>
          <div class="scenario-card__stats">
            <div class="scenario-stat">
              <span class="scenario-stat__label">Fed Funds</span>
              <span class="scenario-stat__val">${(L.interest_rate * 100).toFixed(1)}%</span>
            </div>
            <div class="scenario-stat">
              <span class="scenario-stat__label">M2 Growth</span>
              <span class="scenario-stat__val">${(L.money_supply_growth * 100).toFixed(1)}%</span>
            </div>
            <div class="scenario-stat">
              <span class="scenario-stat__label">Tax Rate</span>
              <span class="scenario-stat__val">${(L.tax_rate * 100).toFixed(0)}%</span>
            </div>
            <div class="scenario-stat">
              <span class="scenario-stat__label">Supply Friction</span>
              <span class="scenario-stat__val">${(L.supply_chain_friction * 100).toFixed(0)}%</span>
            </div>
          </div>
        </div>
      `;
    }).join('');

    // Click handlers
    grid.querySelectorAll('.scenario-card').forEach(card => {
      card.addEventListener('click', () => {
        const key = card.dataset.scenario;
        const scenario = this.scenarios[key];
        if (scenario) {
          Simulation.setLevers(scenario.levers);
          this._switchView('dashboard');
          // Auto-run
          Simulation.rerollSeed();
          Simulation.run();
        }
      });
    });
  },

  _switchView(view) {
    this.activeView = view;

    // Update tab states
    document.querySelectorAll('.tab').forEach(t => {
      t.classList.toggle('is-active', t.dataset.view === view);
    });

    // Show/hide main layout vs views
    const layout = document.querySelector('.layout');
    const views = ['scenarios', 'household', 'game'];

    if (view === 'dashboard') {
      layout.style.display = '';
      views.forEach(v => {
        const el = document.getElementById(`view-${v}`);
        if (el) el.hidden = true;
      });
    } else {
      layout.style.display = 'none';
      views.forEach(v => {
        const el = document.getElementById(`view-${v}`);
        if (el) el.hidden = v !== view;
      });
    }

    // If household or game, trigger a render if data exists
    if (view === 'household' && Simulation.current) {
      Household.calculate();
    }

    // Charts that were hidden need a resize after becoming visible.
    requestAnimationFrame(() => {
      Charts.resizeAll();
      if (Household.chart) Household.chart.resize();
      if (Household.mortgageChart) Household.mortgageChart.resize();
      if (Game.chart) Game.chart.resize();
    });
  },

  _initTooltips() {
    const tooltipEl = document.getElementById('tooltip');

    document.querySelectorAll('[data-tooltip]').forEach(el => {
      const key = el.dataset.tooltip;
      const tip = this.tooltips[key];
      if (!tip) return;

      el.addEventListener('mouseenter', (e) => {
        tooltipEl.innerHTML = `
          <div class="tooltip__title">${tip.label}</div>
          <div class="tooltip__short">${tip.short}</div>
          <div class="tooltip__formula">${tip.formula}</div>
          <div class="tooltip__theory">${tip.theory}</div>
        `;
        tooltipEl.hidden = false;
      });

      el.addEventListener('mousemove', (e) => {
        const pad = 14;
        let x = e.clientX + pad;
        let y = e.clientY + pad;
        const rect = tooltipEl.getBoundingClientRect();
        if (x + rect.width > window.innerWidth) x = e.clientX - rect.width - pad;
        if (y + rect.height > window.innerHeight) y = e.clientY - rect.height - pad;
        tooltipEl.style.left = `${x}px`;
        tooltipEl.style.top = `${y}px`;
      });

      el.addEventListener('mouseleave', () => {
        tooltipEl.hidden = true;
      });
    });
  },

  _showLeverExplanation(exp) {
    const list = document.getElementById('insights-list');
    if (!list) return;
    const channelsHtml = (exp.channels || []).map(c =>
      `<span class="insight__channel">${c}</span>`
    ).join('');
    const html = `
      <div class="insight info flash">
        <div class="insight__head">
          <span class="insight__title">${exp.title}</span>
          <span class="insight__cat">Policy</span>
        </div>
        <div class="insight__body">${exp.body}</div>
        <div class="insight__channels">${channelsHtml}</div>
      </div>`;
    list.insertAdjacentHTML('afterbegin', html);
    // Keep list bounded
    while (list.children.length > 12) list.removeChild(list.lastChild);
  },

  _updateTicker(result) {
    const track = document.getElementById('ticker-track');
    if (!track || !result.shocks) return;

    // Duplicate shocks for seamless scroll
    const items = result.shocks.map(s => `
      <span class="ticker__item ${s.label}">
        <span class="tag">${s.kind}</span>
        ${s.headline}
      </span>
    `).join('');

    track.innerHTML = items + items;
  },

  _updateTickerMeta(result) {
    const monthEl = document.getElementById('ticker-month');
    if (monthEl && result.history) {
      const last = result.history[result.history.length - 1];
      monthEl.textContent = `Month ${last.month} · Y${(last.month / 12).toFixed(1)}`;
    }
    if (Simulation.seed != null) {
      document.getElementById('ticker-seed').textContent = `seed ${Simulation.seed}`;
    }
  },

  _updateInsights(result) {
    const list = document.getElementById('insights-list');
    const countEl = document.getElementById('insight-count');
    if (!list || !result.insights) return;

    list.innerHTML = result.insights.map(ins => `
      <div class="insight ${ins.severity}">
        <div class="insight__head">
          <span class="insight__title">${ins.title}</span>
          <span class="insight__cat">${ins.category}</span>
        </div>
        <div class="insight__body">${ins.body}</div>
      </div>
    `).join('');

    if (countEl) countEl.textContent = `${result.insights.length} insights`;
  },
};

// Boot
document.addEventListener('DOMContentLoaded', () => App.init());
