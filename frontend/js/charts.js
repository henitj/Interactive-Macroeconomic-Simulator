/* ==========================================================================
   Charts module — renders all Chart.js visualisations from simulation data.
   ========================================================================== */

const Charts = {
  instances: {},

  chartDefs: {
    sp500: { key: 'sp500', color: CHART_COLORS.stock, label: 'S&P 500 Index', format: ',.1f', fill: true },
    bondYield: { key: 'bondYield', color: CHART_COLORS.bond, label: '10Y Yield (%)', format: '.2f', suffix: '%' },
    housePrice: { key: 'housePrice', color: CHART_COLORS.house, label: 'House Price Index', format: ',.1f', fill: true },
    commodity: { key: 'commodity', color: CHART_COLORS.commodity, label: 'Commodity Index', format: ',.1f', fill: true },
    gdp: { key: 'gdp', color: CHART_COLORS.gdp, label: 'Real GDP Index', format: ',.1f', fill: true },
    inflation: { key: 'inflation', color: CHART_COLORS.inflation, label: 'CPI Inflation (%)', format: '.2f', suffix: '%', fill: true },
    unemployment: { key: 'unemployment', color: CHART_COLORS.unemployment, label: 'Unemployment (%)', format: '.2f', suffix: '%', fill: true },
    moneySupply: { key: 'moneySupply', color: CHART_COLORS.m2, label: 'M2 Money Supply', format: ',.1f', fill: true },
  },

  init() {
    // Create the 4 default market charts
    this._create('sp500');
    this._create('bondYield');
    this._create('housePrice');
    this._create('commodity');
    // Hidden macro charts
    this._create('gdp');
    this._create('inflation');
    this._create('unemployment');
    this._create('moneySupply');
    // Household charts (dual axis)
    this._createWageChart();
    this._createPurchasingPowerChart();

    // Subscribe to simulation updates
    Simulation.subscribe((result) => this.update(result));
  },

  _create(chartName) {
    const def = this.chartDefs[chartName];
    const canvasId = `chart-${chartName}`;
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const dataset = makeDataset(def.label, [], def.color, { fill: def.fill, tension: 0.3 });
    const chart = createLineChart(canvasId, [dataset], {
      labels: [],
      tooltipCallbacks: {
        label: (ctx) => {
          const v = ctx.parsed.y;
          return ` ${def.label}: ${formatNum(v, def.format)}${def.suffix || ''}`;
        },
        title: (items) => {
          if (!items.length) return '';
          const m = items[0].dataIndex;
          return `Month ${m} (Year ${(m / 12).toFixed(1)})`;
        },
      },
    });

    if (chart) {
      chart.options.onClick = (evt, elements) => {
        if (elements.length > 0) {
          const idx = elements[0].index;
          this._showCrosshair(idx);
        }
      };
    }

    this.instances[chartName] = chart;
  },

  _createWageChart() {
    const canvas = document.getElementById('chart-realWage');
    if (!canvas) return;

    const chart = createLineChart('chart-realWage', [
      makeDataset('Nominal Wage', [], CHART_COLORS.nominalWage, { borderDash: [5, 3] }),
      makeDataset('Real Wage', [], CHART_COLORS.realWage, { fill: true }),
    ], {
      labels: [],
      tooltipCallbacks: {
        label: (ctx) => ` ${ctx.dataset.label}: ${formatNum(ctx.parsed.y, ',.1f')}`,
        title: (items) => items.length ? `Month ${items[0].dataIndex}` : '',
      },
    });
    this.instances.realWage = chart;
  },

  _createPurchasingPowerChart() {
    const canvas = document.getElementById('chart-purchasingPower');
    if (!canvas) return;

    const chart = createLineChart('chart-purchasingPower', [
      makeDataset('Purchasing Power Index', [], CHART_COLORS.pp, { fill: true }),
    ], {
      labels: [],
      tooltipCallbacks: {
        label: (ctx) => ` Index: ${formatNum(ctx.parsed.y, ',.2f')}`,
        title: (items) => items.length ? `Month ${items[0].dataIndex}` : '',
      },
    });
    this.instances.purchasingPower = chart;
  },

  update(result) {
    const { history } = result;
    const labels = history.map(r => r.month);

    // Update all single-series charts
    Object.entries(this.chartDefs).forEach(([name, def]) => {
      const chart = this.instances[name];
      if (!chart) return;
      const data = history.map(r => r[def.key]);
      chart.data.labels = labels;
      chart.data.datasets[0].data = data;
      chart.data.datasets[0].label = def.label;

      // Recompute gradient
      if (def.fill) {
        const { ctx, chartArea } = chart;
        if (chartArea) {
          chart.data.datasets[0].backgroundColor = makeGradient(ctx, chartArea, def.color);
        }
      }
      chart.update('none');
    });

    // Wage chart
    if (this.instances.realWage) {
      this.instances.realWage.data.labels = labels;
      this.instances.realWage.data.datasets[0].data = history.map(r => r.nominalWage);
      this.instances.realWage.data.datasets[1].data = history.map(r => r.realWage);
      const { ctx, chartArea } = this.instances.realWage;
      if (chartArea) {
        this.instances.realWage.data.datasets[1].backgroundColor = makeGradient(ctx, chartArea, CHART_COLORS.realWage);
      }
      this.instances.realWage.update('none');
    }

    // Purchasing power
    if (this.instances.purchasingPower) {
      this.instances.purchasingPower.data.labels = labels;
      this.instances.purchasingPower.data.datasets[0].data = history.map(r => r.purchasingPower);
      const { ctx, chartArea } = this.instances.purchasingPower;
      if (chartArea) {
        this.instances.purchasingPower.data.datasets[0].backgroundColor = makeGradient(ctx, chartArea, CHART_COLORS.pp);
      }
      this.instances.purchasingPower.update('none');
    }

    // Update headline values
    this._updateHeadlines(history);
    this._updateKpis(result);
  },

  _updateHeadlines(history) {
    const end = history[history.length - 1];
    const set = (id, v, fmt = ',.2f', suffix = '') => {
      const el = document.getElementById(id);
      if (el) el.textContent = `${formatNum(v, fmt)}${suffix}`;
    };
    set('val-sp500', end.sp500, ',.1f');
    set('val-bondYield', end.bondYield, '.2f', '%');
    set('val-housePrice', end.housePrice, ',.1f');
    set('val-commodity', end.commodity, ',.1f');
    set('val-gdp', end.gdp, ',.1f');
    set('val-inflation', end.inflation, '.2f', '%');
    set('val-unemployment', end.unemployment, '.2f', '%');
    set('val-moneySupply', end.moneySupply, ',.1f');
    set('val-realWage', end.realWage, ',.1f');
    set('val-purchasingPower', end.purchasingPower, ',.1f');

    // Color-code based on trend
    this._colorHeadline('val-sp500', end.sp500, history[0].sp500);
    this._colorHeadline('val-bondYield', end.bondYield, history[0].bondYield, true);
    this._colorHeadline('val-housePrice', end.housePrice, history[0].housePrice);
    this._colorHeadline('val-commodity', end.commodity, history[0].commodity);
  },

  _colorHeadline(elId, current, initial, invert = false) {
    const el = document.getElementById(elId);
    if (!el) return;
    const delta = current - initial;
    const positive = invert ? delta < 0 : delta > 0;
    if (Math.abs(delta) < 0.001) {
      el.style.color = 'var(--text-0)';
    } else {
      el.style.color = positive ? 'var(--emerald)' : 'var(--crimson)';
    }
  },

  _updateKpis(result) {
    const { summary } = result;
    if (!summary) return;

    const kpis = [
      { label: 'GDP Growth', value: `${summary.totalGdpGrowth > 0 ? '+' : ''}${summary.totalGdpGrowth}%`, delta: summary.totalGdpGrowth, upIsGood: true },
      { label: 'CPI Inflation', value: `${summary.totalInflation}%`, delta: summary.totalInflation, upIsGood: false, suffix: '%' },
      { label: 'Equity Return', value: `${summary.equityReturn > 0 ? '+' : ''}${summary.equityReturn}%`, delta: summary.equityReturn, upIsGood: true },
      { label: 'Max Drawdown', value: `${summary.maxEquityDrawdown}%`, delta: summary.maxEquityDrawdown, upIsGood: false },
      { label: 'Unemployment', value: `${summary.endUnemployment}%`, delta: summary.endUnemployment - 4.5, upIsGood: false },
      { label: 'Real Wage Δ', value: `${summary.realWageChange > 0 ? '+' : ''}${summary.realWageChange.toFixed(1)}%`, delta: summary.realWageChange, upIsGood: true },
      { label: 'Purchasing Power', value: `${summary.purchasingPowerChange > 0 ? '+' : ''}${summary.purchasingPowerChange}%`, delta: summary.purchasingPowerChange, upIsGood: true },
      { label: 'Recession Months', value: `${summary.recessionMonths}`, delta: -summary.recessionMonths, upIsGood: true },
    ];

    const row = document.getElementById('kpi-row');
    if (!row) return;
    row.innerHTML = kpis.map(k => {
      const isUp = k.delta > 0;
      const isGood = k.upIsGood ? isUp : !isUp;
      const cls = Math.abs(k.delta) < 0.01 ? 'neutral' : (isGood ? 'up' : 'down');
      const arrow = Math.abs(k.delta) < 0.01 ? '■' : (isUp ? '▲' : '▼');
      return `
        <div class="kpi">
          <div class="kpi__label">${k.label}</div>
          <div class="kpi__value">${k.value}</div>
          <div class="kpi__delta ${cls}">${arrow} ${Math.abs(k.delta).toFixed(2)}${k.suffix || ''}</div>
        </div>`;
    }).join('');
  },

  _showCrosshair(idx) {
    // Could add cross-chart crosshair sync in future
  },

  showGroup(group) {
    const cards = document.querySelectorAll('.chart-card');
    cards.forEach(c => c.hidden = true);

    let show = [];
    if (group === 'markets') show = ['sp500', 'bondYield', 'housePrice', 'commodity'];
    else if (group === 'macro') show = ['gdp', 'inflation', 'unemployment', 'moneySupply'];
    else if (group === 'households') show = ['realWage', 'purchasingPower'];
    else if (group === 'all') show = ['sp500', 'bondYield', 'housePrice', 'commodity', 'gdp', 'inflation', 'unemployment', 'moneySupply'];

    // 2x2 for groups of 4, list for all
    const grid = document.getElementById('chart-grid');
    if (group === 'all') {
      grid.style.gridTemplateColumns = '1fr 1fr';
      grid.style.gridTemplateRows = 'repeat(4, 1fr)';
    } else if (group === 'households') {
      grid.style.gridTemplateColumns = '1fr 1fr';
      grid.style.gridTemplateRows = '1fr';
    } else {
      grid.style.gridTemplateColumns = '1fr 1fr';
      grid.style.gridTemplateRows = '1fr 1fr';
    }

    show.forEach(name => {
      const card = document.querySelector(`.chart-card[data-chart="${name}"]`);
      if (card) card.hidden = false;
    });

    // Charts that were hidden need a resize after becoming visible.
    requestAnimationFrame(() => {
      show.forEach(name => {
        const c = this.instances[name];
        if (c) c.resize();
      });
    });
  },

  resizeAll() {
    Object.values(this.instances).forEach(c => c && c.resize());
  },
};

/**
 * Number formatter.
 */
function formatNum(v, fmt = ',.2f') {
  if (v == null || isNaN(v)) return '—';
  const decimals = (fmt.match(/\.(\d+)f/) || [])[1];
  const d = decimals ? parseInt(decimals) : 2;
  const comma = fmt.includes(',');
  let s = Number(v).toFixed(d);
  if (comma) {
    const parts = s.split('.');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    s = parts.join('.');
  }
  return s;
}
