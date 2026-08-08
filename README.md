# 📈 Hackonomics 2027 — Interactive Macroeconomic Simulator

An institutional-grade, web-based interactive macroeconomic simulator. Manipulate core economic levers — interest rates, money supply, taxes, supply chains, sentiment — and watch real-time dynamics unfold across stock markets, bond yields, real estate, commodities, wages, GDP, and consumer purchasing power.

Built for the **Hackonomics 2027** challenge to bridge complex economic theory with intuitive, real-time visual feedback for high school and college students.

![Tech](https://img.shields.io/badge/Python-3.11-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![JS](https://img.shields.io/badge/Vanilla-JS-yellow)
![Chart.js](https://img.shields.io/badge/Chart.js-4.4-orange)

---

## ✨ Features

### 🎛️ Six Policy Levers
- **Federal Funds Rate** — the central bank's primary tool
- **Inflation Target** — anchors long-run expectations
- **Money Supply Growth (M2)** — quantity-theory channel
- **Average Tax Rate** — fiscal stance / disposable income
- **Government Spending** — G in Y = C + I + G + NX
- **Supply-Chain Friction** — cost-push / stagflation driver
- **Market Sentiment** — animal spirits & risk premium

Plus adjustable **simulation horizon** (1–20 years) and **shock volatility** (calm → crisis).

### 📊 Real-Time Outputs (2×2 Multi-Chart Grid)
- Stock Market (S&P 500 proxy) — earnings × P/E discount model
- 10-Year Bond Yields — policy rate + term + inflation premium
- Real Estate Index — income / mortgage-carry affordability model
- Commodity Index — inflation hedge × demand × supply shocks
- Real GDP & GDP growth (IS-curve / Okun's law)
- CPI Inflation (Phillips curve + money + cost-push)
- Unemployment (Okun's law)
- Money Supply (M2)
- Real vs. Nominal Wages
- Consumer Purchasing Power (real disposable income net of debt service)

### 🎲 Unique Run Every Time
A stochastic micro-shock engine draws Gaussian + tail events across 10 shock categories (supply, demand, financial, fiscal, energy, geopolitical, labor, monetary, tech, housing). Identical slider settings produce distinct, realistic trajectories. Pass an explicit seed for reproducibility.

### 🕰️ "What-If" Historical Scenarios
One-click presets for landmark economic moments:
- 1970s Stagflation (oil shocks + loose money)
- 2008 Financial Crisis (credit freeze + housing bust)
- 2020 Supply-Chain Shock (pandemic lockdowns + stimulus)
- Volcker Disinflation (1981 brutal rate hikes)
- Great Depression (1929 deflation + money collapse)
- Goldilocks 1990s (productivity boom)

### 🎓 Edu-Engine (Educational Insight Layer)
- Dynamic, plain-English explanations that trigger as parameters change
- Cause-and-effect chains (e.g., how rate hikes hit housing affordability)
- Tooltips on every chart & lever with formulas and economic theory
- Lever-change explanations that list transmission channels

### 👨‍👩‍👧 Household Impact Calculator
Input salary, mortgage, other debt, savings, and monthly spend to see how macro trends hit personal purchasing power, mortgage payments, and discretionary income over the simulation horizon.

### 🏛️ "Central Banker" Game Mode
A gamified 5-year challenge: set the policy rate and money supply growth each year to keep inflation near 2% and unemployment below 6%. Scored on a 0–100 scale with letter grades (S/A/B/C/D/F) and titles like "Maestro of the Mandate" or "Stagflation Architect."

### 📰 Live Event Ticker
A scrolling financial news feed reports simulated economic events and micro-shocks as time progresses.

---

## 🏗️ Architecture

```
Interactive-Macroeconomic-Simulator/
├── backend/
│   ├── app/
│   │   ├── app.py           # Flask API — routing, validation, serialization
│   │   ├── models.py        # Economic engine — all math & stochastic logic
│   │   └── insights.py      # Edu-Engine — plain-English explanations & tooltips
│   └── requirements.txt
├── frontend/
│   ├── index.html           # Dashboard layout
│   ├── css/
│   │   └── styles.css       # Institutional dark-mode design system
│   └── js/
│       ├── app.js           # Initialization, tabs, tooltips, scenarios
│       ├── api.js           # Fetch client for backend endpoints
│       ├── simulation.js    # Lever state, run orchestration
│       ├── charts.js        # Chart.js rendering & KPI updates
│       ├── chart-theme.js   # Global chart theme & gradient helpers
│       ├── household.js     # Household impact calculator
│       └── game.js          # Central Banker game mode
└── README.md
```

**Clean separation**: the Python backend owns all mathematical modeling; the vanilla JS frontend owns layout, state, and interactive charting. The two communicate over a JSON API.

---

## 🧮 Economic Models

The engine advances the economy one month at a time over 60–240 months. Key equations:

### IS-Curve (Output Gap)
```
output_gap = -β·(r - r*) + fiscal_impulse - tax_drag - supply_drag
            + γ·sentiment_gap + δ·shock
```

### GDP Growth
```
ΔGDP = potential_growth + α·output_gap + ε_shock
```

### Okun's Law (Unemployment)
```
u_target = u* - κ·output_gap + shock
```

### Phillips Curve (Inflation)
```
π = w1·π^e + w2·π* + w3·(u* - u) + cost_push
   + money_lag + supply_shock
```
With adaptive expectations anchored to the target:
```
π^e_t = λ·π^e_{t-1} + (1-λ)·π_actual
```

### Stock Market (DCF Proxy)
```
P = E × [1 / (r_f + ERP + π_drag)] × sentiment_premium
```

### Bond Yield
```
y = i_policy + term_premium + 0.6·π^e + output_gap_premium
```

### Real Estate
```
P_house ∝ income^0.6 × (1/mortgage_carry)^0.55
         × supply_constraint × sentiment
```

### Wages
```
ΔW_nominal = a·π^e + b·π + c·(u* - u)
W_real = W_nominal / CPI
```

### Purchasing Power
```
PP = 100 × (W_real / W_real₀) × [(1-τ)/(1-τ₀)] × [(1-debt)/(1-debt₀)]
```

All coefficients are calibrated so a baseline run produces ~2% inflation, ~4.5% unemployment, ~2% real GDP growth, and positive but moderate equity returns over 5 years.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- A modern web browser

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/Interactive-Macroeconomic-Simulator.git
cd Interactive-Macroeconomic-Simulator

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -r backend/requirements.txt
```

### Run the Server

```bash
cd backend/app
python app.py
```

The application will be available at **http://localhost:8000** — the Flask server serves both the API and the frontend from a single port.

### Production Deployment

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```
Run from the `backend/app/` directory.

---

## 🔌 API Reference

### `GET /api/health`
Liveness probe.

### `GET /api/scenarios`
Returns all historical what-if scenario presets.

### `GET /api/tooltips`
Returns the educational glossary for all charts and levers.

### `POST /api/simulate`
Run a stochastic simulation.

**Request body:**
```json
{
  "interest_rate": 0.045,
  "inflation_target": 0.02,
  "money_supply_growth": 0.05,
  "tax_rate": 0.22,
  "government_spending": 0.20,
  "supply_chain_friction": 0.10,
  "sentiment": 0.55,
  "months": 60,
  "seed": 42,
  "shock_volatility": 1.0
}
```

**Response:** `history` (monthly time series), `shocks` (event log), `insights` (Edu-Engine cards), `summary` (KPIs).

### `POST /api/household`
Overlay a personal balance sheet on a simulation.

**Request body:**
```json
{
  "profile": {
    "gross_salary": 75000,
    "mortgage_debt": 250000,
    "mortgage_rate": 0.065,
    "other_debt": 15000,
    "other_debt_rate": 0.18,
    "savings": 20000,
    "monthly_spend": 3500
  },
  "history": [...]
}
```

### `POST /api/game/score`
Score a Central Banker game run.

### `POST /api/insights/explain`
Get a plain-English explanation when a lever changes.

---

## 🎨 Design System

- **Palette**: Slate-and-navy dark mode (`#0a0e1a` → `#1c2640`)
- **Semantic colors**:
  - Emerald `#34d399` — gains / positive / on-target
  - Crimson `#f87171` — recessions / losses / danger
  - Amber `#fbbf24` — warnings / elevated risk
  - Blue `#60a5fa` — policy / information
- **Typography**: Inter (UI) + JetBrains Mono (numerical data)
- **Charts**: Chart.js 4.4 with custom gradient fills and synchronized dark theme
- **Responsive**: 3-column dashboard collapses to single column on tablet/mobile

---

## 🧪 Stochastic Engine

Every simulation month generates a shock:
- 88% of months: Gaussian N(0, 0.75σ)
- 12% of months: tail event N(0, 1.4σ), capped at ±2.8σ
- Shock category randomly selected from 10 types
- Each shock has a headline drawn from a curated vocabulary (~150 events)
- Shocks feed demand, inflation, and risk premium with realistic lags

The `shock_volatility` parameter (0–3×) scales all shock magnitudes — use it to simulate calm expansions vs. crisis regimes.

---

## 📚 Educational Theory References

- **IS-LM / AD-AS** — aggregate demand & output gaps
- **Phillips Curve** — inflation-unemployment tradeoff
- **Okun's Law** — growth-unemployment link
- **Taylor Rule** — policy rate reaction function (intuition)
- **Quantity Theory of Money** (MV = PY) — money growth → inflation
- **Dividend Discount Model** — equity valuation
- **Expectations-Augmented Phillips Curve** — adaptive expectations
- **Ricardian / Fiscal Multipliers** — government spending channel

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Economic Engine | Python 3.11 (pure math, no ML frameworks) |
| API | Flask 3.0 + flask-cors |
| Production WSGI | Gunicorn |
| Frontend | HTML5, CSS3, Vanilla JavaScript (ES6+) |
| Charts | Chart.js 4.4 |
| Fonts | Inter + JetBrains Mono (Google Fonts) |
| Dependencies Zero build step — no npm, no webpack, no framework lock-in.

---

## 📄 License

MIT License — built for Hackonomics 2027.

---

## 🙏 Acknowledgments

Economic models inspired by standard macroeconomic textbooks (Mankiw, Blanchard, Mishkin) and central bank working papers. All simulations are stylized and for educational purposes — not investment advice.
