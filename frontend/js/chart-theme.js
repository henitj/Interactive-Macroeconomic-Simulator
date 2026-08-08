/* ==========================================================================
   Chart.js global theme — institutional dark-mode defaults
   ========================================================================== */

const CHART_COLORS = {
  stock: '#34d399',
  bond: '#60a5fa',
  house: '#fbbf24',
  commodity: '#fb7185',
  gdp: '#34d399',
  inflation: '#f87171',
  unemployment: '#fbbf24',
  m2: '#a78bfa',
  nominalWage: '#94a3b8',
  realWage: '#34d399',
  pp: '#22d3ee',
  grid: 'rgba(35, 46, 71, 0.6)',
  tick: '#54607a',
  text: '#7d8aa3',
};

// Apply global Chart.js defaults
if (window.Chart) {
  Chart.defaults.color = CHART_COLORS.text;
  Chart.defaults.borderColor = CHART_COLORS.grid;
  Chart.defaults.font.family = "'Inter', -apple-system, sans-serif";
  Chart.defaults.font.size = 11;
  Chart.defaults.plugins.legend.display = false;
  Chart.defaults.plugins.tooltip = {
    backgroundColor: 'rgba(15, 22, 35, 0.95)',
    titleColor: '#eaf0fb',
    bodyColor: '#b6c2d9',
    borderColor: 'rgba(35, 46, 71, 0.8)',
    borderWidth: 1,
    padding: 10,
    cornerRadius: 6,
    titleFont: { weight: '600', size: 12 },
    bodyFont: { family: "'JetBrains Mono', monospace", size: 11 },
    displayColors: true,
    boxPadding: 4,
  };
  Chart.defaults.elements.line = {
    tension: 0.35,
    borderWidth: 2,
    fill: false,
  };
  Chart.defaults.elements.point = { radius: 0, hoverRadius: 4 };
  Chart.defaults.interaction = { mode: 'index', intersect: false };
}

/**
 * Shared axis factory — keeps every chart visually consistent.
 */
function makeAxis(isTime = false) {
  return {
    grid: {
      color: 'rgba(35, 46, 71, 0.4)',
      drawBorder: false,
    },
    ticks: {
      color: CHART_COLORS.tick,
      font: { family: "'JetBrains Mono', monospace", size: 10 },
      maxTicksLimit: 6,
      padding: 8,
    },
    border: { display: false },
  };
}

/**
 * Build a gradient fill under a line (for area charts).
 */
function makeGradient(ctx, area, color) {
  if (!area) return color;
  const g = ctx.createLinearGradient(0, area.top, 0, area.bottom);
  g.addColorStop(0, hexToRgba(color, 0.35));
  g.addColorStop(1, hexToRgba(color, 0.0));
  return g;
}

function hexToRgba(hex, alpha) {
  const h = hex.replace('#', '');
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * Factory for a standard line/area chart.
 */
function createLineChart(canvasId, datasets, options = {}) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  const labels = options.labels || [];
  const chart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 600, easing: 'easeOutQuart' },
      scales: {
        x: makeAxis(),
        y: { ...makeAxis(), position: 'left' },
        ...(options.rightAxis ? { y1: { ...makeAxis(), position: 'right', grid: { drawOnChartArea: false } } } : {}),
      },
      plugins: {
        tooltip: {
          callbacks: options.tooltipCallbacks || {},
        },
      },
    },
  });
  return chart;
}

/**
 * Build a dataset object with theme defaults.
 */
function makeDataset(label, data, color, opts = {}) {
  return {
    label,
    data,
    borderColor: color,
    backgroundColor: opts.fill ? undefined : hexToRgba(color, 0.1),
    pointRadius: 0,
    pointHoverRadius: 4,
    pointHoverBackgroundColor: color,
    pointHoverBorderColor: '#0f1623',
    pointHoverBorderWidth: 2,
    borderWidth: opts.borderWidth || 2,
    tension: opts.tension ?? 0.35,
    fill: opts.fill || false,
    yAxisID: opts.yAxisID || 'y',
    borderDash: opts.borderDash || [],
  };
}
