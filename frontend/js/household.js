/* ==========================================================================
   Household Impact Calculator module
   ========================================================================== */

const Household = {
  chart: null,
  mortgageChart: null,
  result: null,

  init() {
    const form = document.getElementById('household-form');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        this.calculate();
      });
    }

    // Create charts
    this._createCharts();

    // Auto-calculate when a new simulation completes
    Simulation.subscribe(() => {
      if (!document.getElementById('view-household').hidden) {
        this.calculate();
      }
    });
  },

  _createCharts() {
    // Income vs expenses chart
    this.chart = createLineChart('chart-household', [
      makeDataset('Real After-Tax Income', [], CHART_COLORS.emerald, { fill: true, borderWidth: 2.5 }),
      makeDataset('Real Cost of Living', [], CHART_COLORS.crimson, { fill: false, borderWidth: 2, borderDash: [6, 3] }),
      makeDataset('Discretionary (Real)', [], CHART_COLORS.amber, { fill: false, borderWidth: 2 }),
    ], {
      labels: [],
      tooltipCallbacks: {
        label: (ctx) => ` ${ctx.dataset.label}: $${formatNum(ctx.parsed.y, ',.0f')}`,
        title: (items) => items.length ? `Month ${items[0].dataIndex}` : '',
      },
    });

    // Mortgage payment chart
    this.mortgageChart = createLineChart('chart-mortgage', [
      makeDataset('Mortgage Payment', [], CHART_COLORS.bond, { fill: true, borderWidth: 2.5 }),
      makeDataset('Other Debt Service', [], CHART_COLORS.commodity, { fill: false, borderWidth: 2, borderDash: [4, 3] }),
    ], {
      labels: [],
      tooltipCallbacks: {
        label: (ctx) => ` ${ctx.dataset.label}: $${formatNum(ctx.parsed.y, ',.0f')}/mo`,
        title: (items) => items.length ? `Month ${items[0].dataIndex}` : '',
      },
    });
  },

  getProfile() {
    return {
      gross_salary: parseFloat(document.getElementById('hh-salary').value) || 75000,
      mortgage_debt: parseFloat(document.getElementById('hh-mortgage').value) || 0,
      mortgage_rate: (parseFloat(document.getElementById('hh-mortgage-rate').value) || 6.5) / 100,
      other_debt: parseFloat(document.getElementById('hh-other').value) || 0,
      other_debt_rate: (parseFloat(document.getElementById('hh-other-rate').value) || 18) / 100,
      savings: parseFloat(document.getElementById('hh-savings').value) || 0,
      monthly_spend: parseFloat(document.getElementById('hh-spend').value) || 3500,
    };
  },

  async calculate() {
    if (!Simulation.current) {
      // Run a quick sim first
      await Simulation.run();
    }
    if (!Simulation.current) return;

    try {
      const profile = this.getProfile();
      const result = await Api.household(profile, Simulation.current.history);
      this.result = result;
      this._render(result);
    } catch (err) {
      console.error('Household calc failed:', err);
    }
  },

  _render(result) {
    const { monthly, summary } = result;
    if (!monthly || !monthly.length) return;

    const labels = monthly.map(r => r.month);

    // Update charts
    this.chart.data.labels = labels;
    this.chart.data.datasets[0].data = monthly.map(r => r.realAfterTaxMonthly);
    this.chart.data.datasets[1].data = monthly.map(r => r.realMonthlySpend);
    this.chart.data.datasets[2].data = monthly.map(r => r.discretionary);
    const area = this.chart.chartArea;
    if (area) {
      this.chart.data.datasets[0].backgroundColor = makeGradient(this.chart.ctx, area, CHART_COLORS.emerald);
    }
    this.chart.update();

    this.mortgageChart.data.labels = labels;
    this.mortgageChart.data.datasets[0].data = monthly.map(r => r.mortgagePayment);
    this.mortgageChart.data.datasets[1].data = monthly.map(r => r.otherDebtPayment);
    if (area) {
      this.mortgageChart.data.datasets[0].backgroundColor = makeGradient(this.mortgageChart.ctx, this.mortgageChart.chartArea, CHART_COLORS.bond);
    }
    this.mortgageChart.update();

    // KPIs
    const last = monthly[monthly.length - 1];
    const first = monthly[0];
    const kpis = [
      { label: 'Final Real Salary', val: `$${formatNum(last.realSalary, ',.0f')}`, delta: summary.realSalaryChange, suffix: '%' },
      { label: 'Monthly Mortgage', val: `$${formatNum(last.mortgagePayment, ',.0f')}`, delta: summary.mortgagePaymentChange, prefix: '$' },
      { label: 'Cost of Living Δ', val: `${summary.costOfLivingChange > 0 ? '+' : ''}${summary.costOfLivingChange}%`, delta: summary.costOfLivingChange, invert: true },
      { label: 'Monthly Discretionary', val: `$${formatNum(last.discretionary, ',.0f')}`, delta: summary.discretionaryChange, prefix: '$' },
      { label: 'Effective Mortgage Rate', val: `${last.effectiveMortgageRate.toFixed(2)}%`, delta: last.effectiveMortgageRate - first.effectiveMortgageRate, invert: true },
    ];

    const kpiEl = document.getElementById('household-kpis');
    if (kpiEl) {
      kpiEl.innerHTML = kpis.map(k => {
        const good = k.invert ? k.delta < 0 : k.delta > 0;
        const cls = Math.abs(k.delta) < 0.01 ? '' : (good ? 'up' : 'down');
        const arrow = Math.abs(k.delta) < 0.01 ? '' : (k.delta > 0 ? '▲' : '▼');
        return `
          <div class="hh-kpi">
            <div class="hh-kpi__label">${k.label}</div>
            <div class="hh-kpi__val">${k.val}</div>
            <div class="hh-kpi__delta kpi__delta ${cls}">${arrow} ${Math.abs(k.delta).toFixed(2)}${k.suffix || ''}</div>
          </div>`;
      }).join('');
    }
  },
};
