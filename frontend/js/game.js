/* ==========================================================================
   Central Banker Game Mode
   User adjusts policy rate each "year" to keep inflation near 2% and
   unemployment below 6% over a 5-year tenure.
   ========================================================================== */

const Game = {
  state: null,
  chart: null,
  tenureHistory: [],
  leverHistory: [],

  init() {
    document.getElementById('btn-game-advance')?.addEventListener('click', () => this.advance());
    document.getElementById('btn-game-restart')?.addEventListener('click', () => this.restart());

    // Game sliders
    const rateRng = document.getElementById('rng-game_rate');
    const m2Rng = document.getElementById('rng-game_m2');
    rateRng?.addEventListener('input', () => {
      document.getElementById('val-game_rate').textContent = `${parseFloat(rateRng.value).toFixed(2)}%`;
    });
    m2Rng?.addEventListener('input', () => {
      document.getElementById('val-game_m2').textContent = `${parseFloat(m2Rng.value).toFixed(1)}%`;
    });

    this.restart();
  },

  restart() {
    this.tenureHistory = [];
    this.leverHistory = [];
    this.state = {
      year: 0,
      interest_rate: 0.045,
      money_supply_growth: 0.05,
      // Start from a baseline snapshot (month 0)
      snapshot: null,
    };
    this._createChart();
    this._updateUI();
    document.getElementById('game-result').hidden = true;
    document.getElementById('btn-game-advance').disabled = false;
  },

  _createChart() {
    if (this.chart) this.chart.destroy();

    this.chart = createLineChart('chart-game', [
      makeDataset('Inflation (%)', [], CHART_COLORS.inflation, { fill: true, borderWidth: 2.5 }),
      makeDataset('Unemployment (%)', [], CHART_COLORS.unemployment, { fill: false, borderWidth: 2 }),
      makeDataset('GDP Growth (%)', [], CHART_COLORS.gdp, { fill: false, borderWidth: 2, borderDash: [5, 3] }),
    ], {
      labels: [],
      tooltipCallbacks: {
        label: (ctx) => ` ${ctx.dataset.label}: ${formatNum(ctx.parsed.y, '.2f')}%`,
        title: (items) => items.length ? `Year ${items[0].dataIndex}` : '',
      },
    });
  },

  async advance() {
    if (this.state.year >= 5) return;
    const btn = document.getElementById('btn-game-advance');
    btn.disabled = true;

    const rate = parseFloat(document.getElementById('rng-game_rate').value) / 100;
    const m2 = parseFloat(document.getElementById('rng-game_m2').value) / 100;

    this.state.interest_rate = rate;
    this.state.money_supply_growth = m2;

    // Record lever choice for volatility scoring
    this.leverHistory.push({
      interest_rate: rate,
      money_supply_growth: m2,
    });

    try {
      // Run a 12-month segment with current policy + a fixed game seed for
      // continuity but enough stochasticity to feel alive.
      const seed = 42 + this.state.year * 7;  // deterministic per-year but varies
      const levers = {
        interest_rate: rate,
        inflation_target: 0.02,
        money_supply_growth: m2,
        tax_rate: 0.22,
        government_spending: 0.20,
        supply_chain_friction: 0.12,
        sentiment: 0.5,
      };

      const result = await Api.simulate(levers, {
        seed,
        months: 12,
        shockVolatility: 1.2, // a bit more volatile to force decisions
      });

      // Take final month as end-of-year state
      const end = result.history[result.history.length - 1];

      // For year 0, record starting point
      if (this.state.year === 0) {
        const start = result.history[0];
        this.tenureHistory.push({
          year: 0,
          inflation: start.inflation,
          unemployment: start.unemployment,
          gdpGrowth: start.gdpGrowth,
          sp500: start.sp500,
        });
      }

      this.tenureHistory.push({
        year: this.state.year + 1,
        inflation: end.inflation,
        unemployment: end.unemployment,
        gdpGrowth: end.gdpGrowth,
        sp500: end.sp500,
      });

      this.state.year++;
      this._updateChart();
      this._updateUI(end);

      if (this.state.year >= 5) {
        this._finish();
      }
    } catch (err) {
      console.error(err);
    } finally {
      btn.disabled = false;
    }
  },

  _updateChart() {
    if (!this.chart) return;
    const labels = this.tenureHistory.map(r => `Y${r.year}`);
    this.chart.data.labels = labels;
    this.chart.data.datasets[0].data = this.tenureHistory.map(r => r.inflation);
    this.chart.data.datasets[1].data = this.tenureHistory.map(r => r.unemployment);
    this.chart.data.datasets[2].data = this.tenureHistory.map(r => r.gdpGrowth);

    // Add 2% target annotation line
    const area = this.chart.chartArea;
    if (area) {
      this.chart.data.datasets[0].backgroundColor = makeGradient(this.chart.ctx, area, CHART_COLORS.inflation);
    }
    this.chart.update();
  },

  _updateUI(end) {
    document.getElementById('game-year').textContent = this.state.year;

    if (end) {
      const inflEl = document.getElementById('game-inflation');
      const unempEl = document.getElementById('game-unemployment');
      const gdpEl = document.getElementById('game-gdp');

      inflEl.textContent = `${end.inflation.toFixed(2)}%`;
      unempEl.textContent = `${end.unemployment.toFixed(2)}%`;
      gdpEl.textContent = `${end.gdpGrowth.toFixed(2)}%`;

      // Color-code based on targets
      inflEl.style.color = Math.abs(end.inflation - 2) < 1 ? 'var(--emerald)' : 'var(--crimson)';
      unempEl.style.color = end.unemployment < 6 ? 'var(--emerald)' : 'var(--crimson)';
      gdpEl.style.color = end.gdpGrowth > 0 ? 'var(--emerald)' : 'var(--crimson)';
    } else {
      document.getElementById('game-inflation').textContent = '2.00%';
      document.getElementById('game-unemployment').textContent = '4.50%';
      document.getElementById('game-gdp').textContent = '2.00%';
    }
  },

  async _finish() {
    const btn = document.getElementById('btn-game-advance');
    btn.disabled = true;

    // Build a simulation-shaped object for scoring
    const fullHistory = this.tenureHistory.map(r => ({
      inflation: r.inflation,
      unemployment: r.unemployment,
      gdpGrowth: r.gdpGrowth,
    }));

    const simulation = {
      history: fullHistory,
      leverHistory: this.leverHistory,
    };

    try {
      const score = await Api.scoreGame(simulation, {});
      this._showResult(score);
    } catch (err) {
      console.error('Scoring failed:', err);
    }
  },

  _showResult(score) {
    const el = document.getElementById('game-result');
    el.hidden = false;
    el.innerHTML = `
      <div class="game-result__grade">${score.grade}</div>
      <div class="game-result__score">${score.score} / 100</div>
      <div class="game-result__title">${score.title}</div>
      <div class="game-result__breakdown">
        <div><span>Final Inflation</span><span>${score.finalInflation.toFixed(2)}%</span></div>
        <div><span>Final Unemployment</span><span>${score.finalUnemployment.toFixed(2)}%</span></div>
        <div><span>Final GDP Growth</span><span>${score.finalGdpGrowth.toFixed(2)}%</span></div>
        <div><span>Recession Years</span><span>${score.recessionMonths}</span></div>
        <div><span>Inflation Penalty</span><span>${score.avgInflationLoss}</span></div>
        <div><span>Unemployment Penalty</span><span>${score.avgUnemploymentLoss}</span></div>
      </div>
    `;
  },
};
