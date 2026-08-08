# Econ Sim — Interactive Macroeconomic Simulator

> **Vision**: A production-grade, institutional-dark-mode dashboard that bridges complex macroeconomic theory with intuitive visual feedback. Designed for high school and college economics students, institutional analysts, and policy enthusiasts.

---

## Repository Structure

```
.
├── index.html              # Root landing page (Vercel / GitHub Pages entry)
├── README.md                # This file
├── backend/
│   ├── app.py               # Flask API + stochastic economic engine
│   ├── engine.py            # (optional split) Core simulation logic
│   └── requirements.txt     # Python dependencies
└── frontend/
    ├── index.html           # Full application page
    ├── css/
    │   └── style.css         # Institutional dark-mode styles
    ├── js/
    │   └── app.js            # Vanilla JS controller
    └── lib/
        └── chart.min.js      # Chart.js (offline-capable)
```

---

## Deployment (Vercel / Static Host)

### Option A: Pure Frontend (Static)
1. Push this repo to GitHub.
2. Connect to Vercel.
3. Set the root directory to `.` (default) — `index.html` will serve as the entry point.
4. **Note**: The simulation requires the Python backend (`/api/simulate`). For a fully static experience without a server, replace the `fetch()` calls in `frontend/js/app.js` with a mock data generator. See the "Mock Mode" section below.

### Option B: Full Stack (Vercel Serverless + Static)
1. Configure Vercel `vercel.json` to proxy `/api/*` to the Flask backend via `vercel-python` or a separate serverless function.
2. Example `vercel.json`:
```json
{
  "version": 2,
  "builds": [
    { "src": "backend/app.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "backend/app.py" },
    { "src": "/(.*)", "dest": "/index.html" }
  ]
}
```
3. Deploy. The root `index.html` loads assets from `frontend/`, and `/api` hits the Python engine.

### Option C: Local Development
```bash
# Start backend
cd backend
pip install -r requirements.txt
python app.py

# Open frontend/index.html in a browser
# If using the backend, set API_BASE to 'http://localhost:5000/api' in frontend/js/app.js
```

---

## Economic Theory & Mathematical Models

### 1. Dynamic Economic Engine
The engine is a **stochastic, mean-reverting discrete-time macro model** (20 quarters / 5 years) built in Python with NumPy. It is non-deterministic: identical slider settings produce unique trajectories due to Brownian-motion micro-shocks and random shocks.

### 2. Core Equations

| Variable | Model / Approximation | Key Drivers |
|---|---|---|
| **Real Rate** | Fisher approximation: `r = i - π` | Fed rate (`i`) and Inflation (`π`) |
| **GDP Growth** | `ΔGDP = base + sentiment_boost + fiscal_drag - rate_drag - friction_drag + money_boost + noise` | Policy, supply friction, sentiment, monetary growth |
| **Unemployment** | Okun's Law approximation: `ΔU ≈ -0.6 · (ΔGDP - 2.5%)` | GDP trajectory |
| **Inflation (CPI)** | Phillips Curve + Monetary + Supply: `Δπ = (5 - U)·0.15 + M·0.25 + F·0.8 - (i - 3)·0.2` | Unemployment (`U`), Money (`M`), Friction (`F`), Fed rate (`i`) |
| **Stock Index** | `ΔS = (3 - i)·15 + (M - 2)·40 + sentiment·3 + shock·400 + noise` | Real rates, liquidity, sentiment, shocks |
| **Bond Yields** | `y = i + 0.3π + risk_spread` | Fed rate, inflation, default/spread premium |
| **Real Estate** | `ΔRE = (M - 2)·8 - (i - 3)·18 - max(0, U - 5)·6 + noise` | Monetary conditions, unemployment |
| **Commodity Index** | `ΔC = F/40·3 + sentiment/50·2 + noise` | Supply friction, sentiment |
| **Nominal Wages** | `ΔW_nom = ΔGDP·0.35 + π·0.45 + noise` | Output growth, price pass-through |
| **Real Wages** | `W_real = W_nom / (1 + π/100) · 0.95` | Nominal wages deflated by CPI |
| **Consumer Power** | `P = (W_real / Cost_index) · 100` | Real wages relative to CPI + commodity mix |

### 3. Probabilistic Shocks
Every quarter has an 8% chance of a micro-shock:
- Rate shock, Inflation spike, Supply chain break, Sentiment crash, Commodity spike, Fiscal stimulus, Credit crunch, Productivity boom.
Shocks propagate through all variables, creating realistic macro volatility.

### 4. Historical Scenarios
The engine includes parameter presets that map to landmark economic moments:
- **1970s Stagflation**: High rates (`12%`), high inflation (`9.5%`), severe supply friction (`85`), depressed sentiment (`25`).
- **2008 Financial Crisis**: Near-zero rates (`0.25%`), deflation risk (`0.5%`), credit freeze (`sentiment 15`, `supply friction 45`).
- **2020 Supply Shock**: Zero-rate policy (`0.1%`), massive monetary growth (`22%`), extreme supply friction (`92`), depressed sentiment (`30`).

---

## Feature Set

### A. Interactive "What-If" Historical Scenarios
One-click preset buttons load historical macro conditions into the sliders and instantly regenerate a simulation trajectory.

### B. The "Edu-Engine" (Educational Insight Layer)
- Dynamic plain-English explanations triggered by parameter changes.
- Explicit cause-and-effect chains (e.g., "Rate hikes impact housing affordability via real estate drag and debt service costs").
- Every chart includes a tooltip breaking down the underlying formula.

### C. Household Impact Calculator
- Users input a personal salary and debt profile.
- The calculator applies the simulated `consumer_power_index` and `real_estate_index` to estimate adjusted purchasing power, housing cost index, and monthly debt service proxies.
- Demonstrates how macro dynamics (inflation, real estate, wages) directly affect household budgets.

### D. "Central Banker" Game Mode
- Gamified 5-year challenge.
- Real-time score based on proximity to targets: Inflation ≈ `2%`, Unemployment ≈ `4%`, GDP Growth ≈ `2.5%`.
- Dynamic hints guide the player through monetary policy trade-offs.

---

## Design & Visual System

- **Aesthetic**: Institutional dark-mode (`#060a14` deep navy) with slate surfaces (`#0f1320`) and high-contrast typography.
- **Color Coding**: Emerald (`#10b981`) for growth/gains, Crimson (`#ef4444`) for contraction/recessions, Amber (`#f59e0b`) for warnings and live feeds.
- **Layout**: Responsive 3-column grid (Controls | Main Charts | Insights & Calculator) collapsing to single column on mobile.
- **Typography**: Inter (body), Space Grotesk (display/headings), JetBrains Mono (data/numbers).
- **Charts**: Chart.js with custom dark-mode palettes, smooth tension curves, right-axis dual-scale support (GDP vs. Unemployment).
- **Ticker**: Scrolling live economic news feed simulating micro-shocks and market reactions.

---

## Technical Details

- **Frontend**: Vanilla JavaScript (ES6 modules via single-file architecture), HTML5 semantic tags, responsive CSS Grid / Flexbox.
- **Backend**: Python 3.11, Flask, NumPy (stochastic generation), CORS enabled.
- **Charts**: Chart.js 4.4.1 (bundled locally in `frontend/lib/` for offline/preview compatibility).
- **API Endpoints**:
  - `GET /` — Service status
  - `GET /api/scenarios` — List historical presets
  - `GET /api/scenario/<key>` — Load preset params
  - `POST /api/simulate` — Run stochastic simulation (returns timeline + summary)
  - `POST /api/edu_insight` — Generate plain-English explanations
  - `POST /api/household_impact` — Calculate household-level impact

---

## Mock Mode (No Backend)
If deploying purely as a static site (e.g., GitHub Pages without serverless functions), replace the `fetch()` logic in `frontend/js/app.js` with a mock generator that produces synthetic data locally. The UI remains fully functional.

---

## Educational Value

This simulator is intended for:
- **Economics Students**: Visualizing how interest rates, fiscal policy, and external shocks interact.
- **Policy Enthusiasts**: Experimenting with "what-if" scenarios to understand policy trade-offs.
- **Analysts**: Demonstrating stochastic modeling techniques and macro forecasting approximations.

---

## Credits

Built as a capstone entry for **Econ Sim**. The mathematical models are educational approximations and do not constitute financial advice or real market forecasting.
