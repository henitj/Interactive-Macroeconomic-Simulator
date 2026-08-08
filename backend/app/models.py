"""
Macroeconomic simulation engine — pure mathematical / stochastic core.

All equations live here. The Flask API layer (app.py) only validates input
and serialises output; it contains no economic logic of its own.

Design principles
-----------------
* Deterministic given a (seed, shocks) pair — every run is reproducible if the
  client passes the same `seed`.
* Stochastic across runs because the server draws a fresh seed unless one is
  supplied; identical slider settings therefore yield distinct, realistic
  trajectories.
* The state is advanced month-by-month so lagged transmission channels
  (interest-rate -> housing, money-supply -> inflation, etc.) behave naturally.

Economic channels modelled
--------------------------
* Aggregate demand driven by real interest rates, fiscal stance (taxes /
  government spending), sentiment, and supply-chain friction.
* Phillips-curve unemployment gap feeding inflation.
* Money-supply growth feeding inflation with a lag (quantity theory intuition).
* Stock market as DCF-ish proxy: earnings x P/E multiple, where the multiple
  contracts with the discount rate and risk premium.
* Bond yields as policy rate + term premium + inflation expectations premium.
* Real estate as inverse real-rate + income growth, with a supply friction tilt.
* Commodities as inflation hedge plus supply-shock / demand-growth sensitivity.
* Nominal vs. real wages via a wage-Phillips curve and CPI indexation.
* Consumer purchasing power = real disposable income, adjusted for debt service.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple


# --------------------------------------------------------------------------- #
# Tunable constants — calibrated so a "baseline" run looks plausible.         #
# --------------------------------------------------------------------------- #

MONTHS_PER_YEAR = 12

TARGET_INFLATION = 0.02          # 2% central bank target
NEUTRAL_REAL_RATE = 0.005        # r* ~ 0.5%
NATURAL_UNEMPLOYMENT = 0.045     # u* ~ 4.5%
LONG_RUN_GDP_GROWTH = 0.020      # potential GDP ~ 2% / yr

# Initial (month-0) levels for the default "today" baseline.
INITIAL = {
    "cpi": 100.0,
    "gdp": 100.0,
    "sp500": 100.0,
    "bond_yield": 0.04,
    "house_price": 100.0,
    "commodity": 100.0,
    "nominal_wage": 100.0,
    "unemployment": 0.045,
    "sentiment": 0.55,
}

# News-event vocabulary used to build the live ticker.
SHOCK_TYPES = (
    "supply", "demand", "financial", "fiscal", "energy",
    "geopolitical", "labor", "monetary", "tech", "housing",
)

POSITIVE_EVENTS = {
    "supply": [
        "Port backlog clears as container ships unload ahead of schedule.",
        "Semiconductor output surges; factories report full order books.",
        "Agricultural yields beat forecasts on favourable weather.",
        "New logistics hub cuts domestic freight times by 12%.",
    ],
    "demand": [
        "Retail sales surprise to the upside as consumer confidence rises.",
        "Holiday spending tops analyst estimates by 4.2%.",
        "Services PMI jumps to a 14-month high.",
        "Household savings buffer supports a durable-goods rebound.",
    ],
    "financial": [
        "Credit spreads tighten as risk appetite returns.",
        "IPO window reopens; two unicorns price above range.",
        "Corporate bond issuance hits a quarterly record.",
        "Bank lending standards ease for the first time in six quarters.",
    ],
    "fiscal": [
        "Infrastructure bill disburses funds to shovel-ready projects.",
        "Targeted tax credit lifts small-business investment.",
        "State and local government hiring accelerates.",
    ],
    "energy": [
        "Crude inventories build; pump prices fall 6 cents.",
        "Renewable capacity additions outpace grid demand.",
        "Natural gas storage sits 8% above the five-year average.",
    ],
    "geopolitical": [
        "Trade talks yield a partial tariff rollback.",
        "Ceasefire agreement lowers geopolitical risk premium.",
    ],
    "labor": [
        "Weekly jobless claims fall to a new cycle low.",
        "Labor-force participation rises as prime-age workers return.",
        "Wage growth steadies without alarming productivity gauges.",
    ],
    "monetary": [
        "Central bank signals a patient stance; markets rally.",
        "Forward guidance anchors inflation expectations near target.",
    ],
    "tech": [
        "Productivity data surprise higher on AI adoption.",
        "Cloud capex guides above consensus; chipmakers rally.",
    ],
    "housing": [
        "Housing starts rebound as materials costs cool.",
        "Mortgage application volume ticks up on stable rates.",
    ],
}

NEGATIVE_EVENTS = {
    "supply": [
        "Key auto plant idled by parts shortage.",
        "Shipping rates spike as a major route re-routes.",
        "Grocery chains warn of pantry-stocking disruptions.",
    ],
    "demand": [
        "Consumer confidence slips as inflation expectations rise.",
        "Big-ticket item demand cools; furniture orders fall.",
        "Restaurant traffic softens for the third straight month.",
    ],
    "financial": [
        "Regional bank shares slide on deposit-outflow concerns.",
        "High-yield spreads widen sharply in a risk-off session.",
        "Leveraged-loan market seizes up; deals pulled.",
    ],
    "fiscal": [
        "Budget standoff triggers a partial government shutdown.",
        "Austerity measures weigh on public-sector payrolls.",
    ],
    "energy": [
        "Oil jumps after a pipeline outage.",
        "Refinery maintenance pushes gasoline higher.",
        "Natural gas spikes on an unseasonal cold snap.",
    ],
    "geopolitical": [
        "Escalation in a key shipping lane raises freight costs.",
        "New export controls rattle semiconductor supply chains.",
        "Embassy dispute fans safe-haven flows.",
    ],
    "labor": [
        "Large tech employer announces fresh layoffs.",
        "Strike action disrupts freight and logistics.",
        "Job openings decline more than expected.",
    ],
    "monetary": [
        "Hawkish rhetoric pushes the front end higher.",
        "Balance-sheet runoff drains reserves faster than expected.",
    ],
    "tech": [
        "Cybersecurity incident hits a major cloud provider.",
        "Semiconductor export curbs dent capex plans.",
    ],
    "housing": [
        "Mortgage rates climb to a multi-year high; purchase apps fall.",
        "Existing-home inventory rises as sellers capitulate on price.",
    ],
}

NEUTRAL_EVENTS = {
    "supply": ["Logistics indicators hold near recent averages."],
    "demand": ["Consumer spending tracks the consensus path."],
    "financial": ["Markets consolidate after recent volatility."],
    "fiscal": ["Legislative calendar quiet; no major fiscal news."],
    "energy": ["Energy prices trade in a narrow range."],
    "geopolitical": ["Geopolitical backdrop steady; traders monitor headlines."],
    "labor": ["Labor market data broadly in line with expectations."],
    "monetary": ["Central bank enters a quiet period ahead of its meeting."],
    "tech": ["Tech sector trades mixed ahead of earnings."],
    "housing": ["Housing data prints close to trend."],
}


# --------------------------------------------------------------------------- #
# Data containers                                                             #
# --------------------------------------------------------------------------- #

@dataclass
class Levers:
    """User-controlled policy / environment settings (annualised units)."""
    interest_rate: float = 0.045       # federal funds rate, decimal
    inflation_target: float = TARGET_INFLATION
    money_supply_growth: float = 0.05  # M2 growth / yr
    tax_rate: float = 0.22             # average effective tax rate
    supply_chain_friction: float = 0.1 # 0 = frictionless, 1 = severe
    sentiment: float = 0.55            # 0..1, >0.5 = risk-on
    government_spending: float = 0.20  # G as share of baseline GDP


@dataclass
class State:
    """Evolving macro state at the end of a month."""
    month: int = 0
    cpi: float = INITIAL["cpi"]
    gdp: float = INITIAL["gdp"]
    sp500: float = INITIAL["sp500"]
    bond_yield: float = INITIAL["bond_yield"]
    house_price: float = INITIAL["house_price"]
    commodity: float = INITIAL["commodity"]
    nominal_wage: float = INITIAL["nominal_wage"]
    unemployment: float = INITIAL["unemployment"]
    sentiment: float = INITIAL["sentiment"]
    inflation: float = 0.02            # annualised month-over-month
    gdp_growth: float = LONG_RUN_GDP_GROWTH
    real_wage: float = INITIAL["nominal_wage"]
    purchasing_power: float = 100.0
    money_supply: float = 100.0
    earnings: float = 6.0              # index of corporate earnings
    risk_premium: float = 0.055
    # Rolling history of recent shocks so inflation exhibits inertia.
    _shock_history: List[float] = field(default_factory=lambda: [0.0] * 12)
    _demand_history: List[float] = field(default_factory=lambda: [0.0] * 6)


@dataclass
class Shock:
    month: int
    kind: str
    magnitude: float                 # signed, units of standard deviations
    label: str
    headline: str


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _monthly(annual_rate: float) -> float:
    """Convert an annualised decimal rate to a monthly compounding factor."""
    return (1.0 + annual_rate) ** (1.0 / MONTHS_PER_YEAR) - 1.0


def _annually(monthly_rate: float) -> float:
    return (1.0 + monthly_rate) ** MONTHS_PER_YEAR - 1.0


# --------------------------------------------------------------------------- #
# Core engine                                                                 #
# --------------------------------------------------------------------------- #

class EconomicEngine:
    """
    Advances the economy one month at a time.

    The engine is deliberately deterministic given (levers, seed, shocks):
    pass an explicit seed to reproduce a trajectory.
    """

    def __init__(self, levers: Levers, seed: Optional[int] = None,
                 months: int = 60, shock_volatility: float = 1.0):
        self.levers = levers
        self.months = months
        self.shock_volatility = _clamp(shock_volatility, 0.0, 3.0)
        self.rng = random.Random(seed)
        self.state = State()
        self.history: List[Dict] = []
        self.shocks: List[Shock] = []

        # Slow-moving inflation expectations (adaptive, anchored to target).
        self._inflation_expectations = TARGET_INFLATION
        self._term_premium = 0.008

    # ------------------------------------------------------------------ #
    # Shock generation                                                   #
    # ------------------------------------------------------------------ #
    def _generate_shock(self, month: int) -> Shock:
        kind = self.rng.choice(SHOCK_TYPES)
        # Magnitude ~ N(0, shock_volatility); 12% chance of a tail event.
        # Shocks are calibrated in "sigma" units; their GDP/CPI impact is
        # scaled down in the step() function so a 1-sigma event is a
        # moderate headwind rather than a crisis.
        if self.rng.random() < 0.12:
            magnitude = self.rng.gauss(0.0, 1.4 * self.shock_volatility)
            magnitude = _clamp(magnitude, -2.8, 2.8)
        else:
            magnitude = self.rng.gauss(0.0, 0.75 * self.shock_volatility)
            magnitude = _clamp(magnitude, -1.5, 1.5)

        if magnitude > 0.55:
            label = "positive"
            headline = self.rng.choice(POSITIVE_EVENTS[kind])
        elif magnitude < -0.55:
            label = "negative"
            headline = self.rng.choice(NEGATIVE_EVENTS[kind])
        else:
            label = "neutral"
            headline = self.rng.choice(NEUTRAL_EVENTS[kind])

        return Shock(month=month, kind=kind, magnitude=magnitude,
                     label=label, headline=headline)

    # ------------------------------------------------------------------ #
    # Single-step update                                                 #
    # ------------------------------------------------------------------ #
    def step(self) -> State:
        s = self.state
        L = self.levers
        m = s.month + 1
        s.month = m

        shock = self._generate_shock(m)
        self.shocks.append(shock)
        s._shock_history.append(shock.magnitude)
        s._shock_history.pop(0)

        # Rolling average shock gives inflation inertia.
        recent_shock = sum(s._shock_history[-6:]) / 6.0

        # -- Real interest rate stance ----------------------------------
        real_rate = L.interest_rate - self._inflation_expectations
        rate_gap = real_rate - NEUTRAL_REAL_RATE        # >0 = restrictive

        # -- Fiscal stance ----------------------------------------------
        fiscal_impulse = (L.government_spending - 0.20) * 0.6
        tax_drag = (L.tax_rate - 0.22) * 0.9

        # -- Supply chain friction directly shaves output & lifts CPI ----
        supply_drag = L.supply_chain_friction * 0.025    # annual % GDP drag
        supply_price_push = L.supply_chain_friction * 0.030  # annual CPI push

        # -- Sentiment (user lever + drift from shocks) -----------------
        target_sent = _clamp(
            L.sentiment + 0.06 * shock.magnitude, 0.02, 0.98
        )
        s.sentiment += 0.25 * (target_sent - s.sentiment)
        sentiment_gap = s.sentiment - 0.5

        # -- Output gap (IS-curve intuition) ----------------------------
        # demand impulse is an ANNUAL % deviation from potential.
        demand_impulse = (
            -0.55 * rate_gap
            + fiscal_impulse * 0.6
            - tax_drag * 0.5
            - supply_drag * 0.4
            + 0.40 * sentiment_gap
            - 0.18 * L.supply_chain_friction
            + 0.06 * shock.magnitude
        )
        s._demand_history.append(demand_impulse)
        s._demand_history.pop(0)
        # Smooth output gap across 6 months to avoid monthly whipsaws.
        output_gap = sum(s._demand_history) / len(s._demand_history)
        output_gap = _clamp(output_gap, -0.06, 0.06)

        # -- GDP growth --------------------------------------------------
        potential = LONG_RUN_GDP_GROWTH
        # Supply friction hits potential modestly.
        potential -= L.supply_chain_friction * 0.004
        # Shock impact is smoothed — only 30% hits in the month, the rest
        # propagates through the output gap over subsequent months.
        gdp_growth = potential + 0.30 * output_gap + 0.010 * shock.magnitude
        gdp_growth = _clamp(gdp_growth, -0.06, 0.06)
        s.gdp_growth = gdp_growth
        s.gdp *= 1.0 + _monthly(gdp_growth)

        # -- Unemployment (Okun's law) ----------------------------------
        target_u = NATURAL_UNEMPLOYMENT - 0.35 * output_gap
        target_u += 0.008 * max(0.0, -shock.magnitude)
        target_u = _clamp(target_u, 0.025, 0.14)
        s.unemployment += 0.15 * (target_u - s.unemployment)

        # -- Inflation (triangular Phillips curve + money + supply) -----
        u_gap = NATURAL_UNEMPLOYMENT - s.unemployment    # >0 = tight labor
        phillips = 0.25 * u_gap                          # demand-pull
        wage_push = 0.15 * u_gap                         # labor cost push

        # Money-supply channel feeds inflation with a 6-12 month lag.
        lagged_m = (L.money_supply_growth - 0.05) * 0.18

        # Adaptive expectations anchored toward target.
        self._inflation_expectations += 0.10 * (
            s.inflation - self._inflation_expectations
        )
        self._inflation_expectations = _clamp(
            0.70 * self._inflation_expectations
            + 0.30 * L.inflation_target,
            -0.02, 0.20,
        )

        inflation = (
            0.45 * self._inflation_expectations
            + 0.30 * L.inflation_target
            + phillips
            + wage_push * 0.3
            + supply_price_push
            + lagged_m
            + 0.008 * recent_shock
            + 0.008 * L.supply_chain_friction
        )
        inflation = _clamp(inflation, -0.03, 0.22)
        s.inflation = inflation
        s.cpi *= 1.0 + _monthly(inflation)

        # -- Money supply ------------------------------------------------
        s.money_supply *= 1.0 + _monthly(L.money_supply_growth)

        # -- Wages (wage-Phillips with partial CPI indexation) ----------
        nominal_wage_growth = (
            0.50 * self._inflation_expectations
            + 0.35 * inflation
            + 0.30 * u_gap
            + 0.012 * max(0.0, sentiment_gap)
        )
        nominal_wage_growth = _clamp(nominal_wage_growth, -0.02, 0.15)
        s.nominal_wage *= 1.0 + _monthly(nominal_wage_growth)
        s.real_wage = s.nominal_wage / (s.cpi / INITIAL["cpi"])

        # -- Purchasing power = real disposable income relative to debt -
        # Start from a baseline PP of 100; evolve with real wages, tax, and
        # the change in debt-service burden relative to neutral 4.5% rates.
        debt_ratio = L.interest_rate / 0.045
        debt_burden = 0.10 * debt_ratio
        debt_burden = _clamp(debt_burden, 0.04, 0.28)
        baseline_burden = 0.10
        # Real wage relative to starting wage, adjusted for tax and debt.
        wage_factor = s.real_wage / INITIAL["nominal_wage"]
        tax_factor = (1.0 - L.tax_rate) / (1.0 - 0.22)
        debt_factor = (1.0 - debt_burden) / (1.0 - baseline_burden)
        s.purchasing_power = 100.0 * wage_factor * tax_factor * debt_factor

        # -- Corporate earnings (track GDP, sentiment, costs) -----------
        earnings_growth = (
            1.20 * gdp_growth
            + 0.15 * sentiment_gap
            - 0.10 * inflation
            - 0.08 * L.supply_chain_friction
            + 0.04 * shock.magnitude
        )
        s.earnings *= 1.0 + _monthly(earnings_growth)
        s.earnings = max(1.0, s.earnings)

        # -- Risk premium (rises with volatility / negative sentiment) --
        target_rp = 0.045 + 0.020 * (1.0 - s.sentiment) \
            + 0.012 * max(0.0, -shock.magnitude)
        s.risk_premium += 0.15 * (target_rp - s.risk_premium)

        # -- Stock market: earnings x P/E multiple, mean-reverting ------
        # Discount rate = risk-free + equity risk premium + inflation drag.
        discount = L.interest_rate * 0.5 + s.risk_premium * 0.5 + 0.25 * inflation
        # A higher discount => lower multiple; earnings growth drives upside.
        fair_pe = 1.0 / max(0.04, discount) * 0.85
        fair_value = s.earnings * fair_pe
        # Sentiment adds a premium/discount.
        fair_value *= 1.0 + 0.20 * sentiment_gap
        # Mean-revert market toward fair value.
        s.sp500 += 0.15 * (fair_value - s.sp500)
        s.sp500 = max(5.0, s.sp500)

        # -- Bond yield (policy + term premium + inflation premium) -----
        target_yield = (
            L.interest_rate
            + self._term_premium
            + 0.60 * self._inflation_expectations
            + 0.15 * max(0.0, output_gap)
        )
        s.bond_yield += 0.25 * (target_yield - s.bond_yield)
        s.bond_yield = _clamp(s.bond_yield, 0.001, 0.22)

        # -- House prices (inverse real rate + income + supply friction) 
        housing_carry = (L.interest_rate + 0.02) * 100.0   # mortgage-ish
        housing_fair = (
            INITIAL["house_price"]
            * (s.nominal_wage / INITIAL["nominal_wage"]) ** 0.6
            * (1.0 / max(0.6, housing_carry / 5.0)) ** 0.55
            * (1.0 + 0.20 * L.supply_chain_friction)  # constrained supply props price short term
            * (1.0 + 0.18 * sentiment_gap)
        )
        s.house_price += 0.12 * (housing_fair - s.house_price)
        s.house_price = max(10.0, s.house_price)

        # -- Commodities (inflation hedge + demand + supply shocks) -----
        commodity_fair = (
            INITIAL["commodity"]
            * (s.cpi / INITIAL["cpi"]) ** 0.8
            * (1.0 + 0.6 * output_gap)
            * (1.0 + 0.25 * L.supply_chain_friction)
            * (1.0 + 0.12 * shock.magnitude)
        )
        s.commodity += 0.18 * (commodity_fair - s.commodity)
        s.commodity = max(10.0, s.commodity)

        self._record()
        return s

    # ------------------------------------------------------------------ #
    # Recording                                                          #
    # ------------------------------------------------------------------ #
    def _record(self) -> None:
        s = self.state
        self.history.append({
            "month": s.month,
            "year": round(s.month / 12, 2),
            "gdp": round(s.gdp, 4),
            "gdpGrowth": round(s.gdp_growth * 100, 3),
            "cpi": round(s.cpi, 4),
            "inflation": round(s.inflation * 100, 3),
            "sp500": round(s.sp500, 4),
            "bondYield": round(s.bond_yield * 100, 3),
            "housePrice": round(s.house_price, 4),
            "commodity": round(s.commodity, 4),
            "nominalWage": round(s.nominal_wage, 4),
            "realWage": round(s.real_wage, 4),
            "purchasingPower": round(s.purchasing_power, 4),
            "unemployment": round(s.unemployment * 100, 3),
            "sentiment": round(s.sentiment, 4),
            "moneySupply": round(s.money_supply, 4),
            "earnings": round(s.earnings, 4),
            "riskPremium": round(s.risk_premium * 100, 3),
            "realRate": round(
                (self.levers.interest_rate - self._inflation_expectations) * 100, 3
            ),
        })

    # ------------------------------------------------------------------ #
    # Public run                                                         #
    # ------------------------------------------------------------------ #
    def run(self) -> Dict:
        # Record month-0 baseline.
        self._record()
        for _ in range(self.months):
            self.step()

        return {
            "months": self.months,
            "levers": asdict(self.levers),
            "history": self.history,
            "shocks": [asdict(sh) for sh in self.shocks],
            "summary": self._summary(),
        }

    def _summary(self) -> Dict:
        h = self.history
        end = h[-1]
        start = h[0]
        # Peak-to-trough drawdown for equities.
        peak = h[0]["sp500"]
        max_dd = 0.0
        for row in h:
            peak = max(peak, row["sp500"])
            dd = (row["sp500"] - peak) / peak
            max_dd = min(max_dd, dd)

        return {
            "totalGdpGrowth": round((end["gdp"] - start["gdp"]) / start["gdp"] * 100, 2),
            "totalInflation": round((end["cpi"] - start["cpi"]) / start["cpi"] * 100, 2),
            "avgInflation": round(sum(r["inflation"] for r in h) / len(h), 2),
            "endUnemployment": end["unemployment"],
            "equityReturn": round((end["sp500"] - start["sp500"]) / start["sp500"] * 100, 2),
            "maxEquityDrawdown": round(max_dd * 100, 2),
            "bondYieldChange": round(end["bondYield"] - start["bondYield"], 2),
            "housePriceChange": round((end["housePrice"] - start["housePrice"]) / start["housePrice"] * 100, 2),
            "commodityChange": round((end["commodity"] - start["commodity"]) / start["commodity"] * 100, 2),
            "realWageChange": round((end["realWage"] - start["realWage"]) / start["realWage"] * 100, 2),
            "purchasingPowerChange": round((end["purchasingPower"] - start["purchasingPower"]) / start["purchasingPower"] * 100, 2),
            "recessionMonths": sum(1 for r in h if r["gdpGrowth"] < 0),
            "shockCount": len(self.shocks),
        }


# --------------------------------------------------------------------------- #
# Household impact calculator                                                 #
# --------------------------------------------------------------------------- #

@dataclass
class HouseholdProfile:
    gross_salary: float = 75000.0      # annual nominal, USD
    mortgage_debt: float = 250000.0
    mortgage_rate: float = 0.065       # annual
    other_debt: float = 15000.0        # credit cards / auto
    other_debt_rate: float = 0.18
    savings: float = 20000.0
    monthly_spend: float = 3500.0      # baseline monthly consumption


def compute_household_impact(profile: HouseholdProfile,
                             history: List[Dict]) -> Dict:
    """
    Overlays a household balance sheet onto the simulated trajectory.

    Returns month-by-month real income, debt service, real monthly spend and
    ending purchasing-power figures.
    """
    if not history:
        return {}

    start = history[0]
    cpi0 = start["cpi"]
    wage_index0 = start["nominalWage"]

    rows = []
    # Assume mortgage is partially floating / refinances when rates move:
    # 60% of mortgage rate tracks the change in bond yields + 2.5% spread.
    base_mortgage = profile.mortgage_rate
    initial_yield = start["bondYield"] / 100.0

    for r in history:
        cpi_ratio = r["cpi"] / cpi0
        wage_ratio = r["nominalWage"] / wage_index0

        # Nominal salary grows with the aggregate wage index.
        nominal_salary = profile.gross_salary * wage_ratio
        # Apply a representative effective tax (levers tax embedded in wage path
        # already; keep simple here and use 22%).
        after_tax = nominal_salary * (1.0 - 0.22)

        # Effective mortgage rate drifts with market yields.
        effective_mortgage = (
            0.4 * base_mortgage
            + 0.6 * (base_mortgage + (r["bondYield"] / 100.0 - initial_yield))
        )
        effective_mortgage = max(0.02, effective_mortgage)
        monthly_mortgage = (
            profile.mortgage_debt
            * (effective_mortgage / 12)
            / (1 - (1 + effective_mortgage / 12) ** -360)
        ) if profile.mortgage_debt > 0 else 0.0

        monthly_other = (
            profile.other_debt * (profile.other_debt_rate / 12)
        )

        # Real monthly spend deflated by CPI.
        real_monthly_spend = profile.monthly_spend / cpi_ratio
        nominal_monthly_spend = profile.monthly_spend * cpi_ratio

        # Real monthly after-tax income.
        real_monthly_income = (after_tax / 12) / cpi_ratio

        rows.append({
            "month": r["month"],
            "nominalSalary": round(nominal_salary, 0),
            "realSalary": round(nominal_salary / cpi_ratio, 0),
            "afterTaxMonthly": round(after_tax / 12, 0),
            "realAfterTaxMonthly": round(real_monthly_income, 0),
            "mortgagePayment": round(monthly_mortgage, 0),
            "otherDebtPayment": round(monthly_other, 0),
            "nominalMonthlySpend": round(nominal_monthly_spend, 0),
            "realMonthlySpend": round(real_monthly_spend, 0),
            "discretionary": round(
                after_tax / 12 - monthly_mortgage - monthly_other
                - nominal_monthly_spend, 0
            ),
            "effectiveMortgageRate": round(effective_mortgage * 100, 2),
            "cpiRatio": round(cpi_ratio, 4),
        })

    first, last = rows[0], rows[-1]
    return {
        "monthly": rows,
        "summary": {
            "realSalaryChange": round(
                (last["realSalary"] - first["realSalary"]) / first["realSalary"] * 100, 2
            ),
            "mortgagePaymentChange": round(
                last["mortgagePayment"] - first["mortgagePayment"], 0
            ),
            "costOfLivingChange": round(
                (last["nominalMonthlySpend"] - first["nominalMonthlySpend"])
                / first["nominalMonthlySpend"] * 100, 2
            ),
            "discretionaryChange": round(
                last["discretionary"] - first["discretionary"], 0
            ),
            "endingDiscretionary": last["discretionary"],
        },
    }


# --------------------------------------------------------------------------- #
# "Central Banker" game mode                                                  #
# --------------------------------------------------------------------------- #

@dataclass
class GameConfig:
    horizon_months: int = 60
    target_inflation: float = 0.02
    max_unemployment: float = 0.06
    initial_interest_rate: float = 0.045


def score_game_run(sim_result: Dict,
                   config: GameConfig = GameConfig()) -> Dict:
    """
    Score a central-banker run. Lower loss = better.

    Loss components (per month, then averaged):
      * Inflation gap squared (penalise deviations from 2%).
      * Unemployment above threshold squared.
      * Recession penalty when GDP growth < 0.
      * Rate-volatility penalty to discourage knob-twiddling.
    Final score is scaled 0-100 with a letter grade.
    """
    h = sim_result["history"]
    levers_history = sim_result.get("leverHistory")

    infl_loss = 0.0
    unemp_loss = 0.0
    rec_loss = 0.0
    vol_loss = 0.0
    n = len(h)

    for r in h:
        gap = (r["inflation"] - config.target_inflation * 100) / 100
        infl_loss += gap ** 2
        u_excess = max(0.0, r["unemployment"] / 100 - config.max_unemployment)
        unemp_loss += u_excess ** 2
        if r["gdpGrowth"] < 0:
            rec_loss += abs(r["gdpGrowth"]) / 100

    if levers_history and len(levers_history) > 1:
        for i in range(1, len(levers_history)):
            dr = levers_history[i]["interest_rate"] - \
                levers_history[i - 1]["interest_rate"]
            vol_loss += dr ** 2

    avg_infl = infl_loss / n
    avg_unemp = unemp_loss / n
    total_rec = rec_loss
    total_vol = vol_loss

    raw_loss = 100 * (
        4.0 * avg_infl
        + 3.0 * avg_unemp
        + 0.5 * total_rec
        + 0.05 * total_vol
    )
    score = max(0.0, min(100.0, 100.0 - raw_loss * 2.5))

    if score >= 90:
        grade = "S"
        title = "Maestro of the Mandate"
    elif score >= 80:
        grade = "A"
        title = "Steady Hand"
    elif score >= 70:
        grade = "B"
        title = "Competent Technocrat"
    elif score >= 60:
        grade = "C"
        title = "Apprentice Governor"
    elif score >= 45:
        grade = "D"
        title = "Behind the Curve"
    else:
        grade = "F"
        title = "Stagflation Architect"

    return {
        "score": round(score, 1),
        "grade": grade,
        "title": title,
        "avgInflationLoss": round(avg_infl * 1e4, 2),
        "avgUnemploymentLoss": round(avg_unemp * 1e4, 2),
        "recessionMonths": sum(1 for r in h if r["gdpGrowth"] < 0),
        "totalRecessionPenalty": round(total_rec, 4),
        "volatilityPenalty": round(total_vol * 1e4, 2),
        "finalInflation": h[-1]["inflation"],
        "finalUnemployment": h[-1]["unemployment"],
        "finalGdpGrowth": h[-1]["gdpGrowth"],
    }


# --------------------------------------------------------------------------- #
# Scenario presets                                                            #
# --------------------------------------------------------------------------- #

SCENARIOS: Dict[str, Dict] = {
    "baseline": {
        "name": "Baseline Economy",
        "description": "A steady expansion near the Fed's 2% inflation target.",
        "levers": {
            "interest_rate": 0.045,
            "inflation_target": 0.02,
            "money_supply_growth": 0.05,
            "tax_rate": 0.22,
            "supply_chain_friction": 0.10,
            "sentiment": 0.55,
            "government_spending": 0.20,
        },
    },
    "stagflation_1970s": {
        "name": "1970s Stagflation",
        "description": "Oil shocks, loose money and entrenched inflation expectations.",
        "levers": {
            "interest_rate": 0.07,
            "inflation_target": 0.04,
            "money_supply_growth": 0.12,
            "tax_rate": 0.26,
            "supply_chain_friction": 0.75,
            "sentiment": 0.28,
            "government_spending": 0.24,
        },
    },
    "financial_crisis_2008": {
        "name": "2008 Financial Crisis",
        "description": "Credit freeze, housing bust, collapsing demand.",
        "levers": {
            "interest_rate": 0.015,
            "inflation_target": 0.02,
            "money_supply_growth": 0.09,
            "tax_rate": 0.20,
            "supply_chain_friction": 0.30,
            "sentiment": 0.18,
            "government_spending": 0.25,
        },
    },
    "covid_shock_2020": {
        "name": "2020 Supply-Chain Shock",
        "description": "Pandemic lockdowns, fiscal stimulus and snarled ports.",
        "levers": {
            "interest_rate": 0.005,
            "inflation_target": 0.02,
            "money_supply_growth": 0.15,
            "tax_rate": 0.18,
            "supply_chain_friction": 0.78,
            "sentiment": 0.30,
            "government_spending": 0.28,
        },
    },
    "volcker_disinflation": {
        "name": "Volcker Disinflation (1981)",
        "description": "Brutal rate hikes to break the back of inflation.",
        "levers": {
            "interest_rate": 0.16,
            "inflation_target": 0.02,
            "money_supply_growth": 0.025,
            "tax_rate": 0.24,
            "supply_chain_friction": 0.30,
            "sentiment": 0.28,
            "government_spending": 0.22,
        },
    },
    "great_depression": {
        "name": "Great Depression (1929)",
        "description": "Deflation, mass unemployment, collapsing money supply.",
        "levers": {
            "interest_rate": 0.03,
            "inflation_target": 0.02,
            "money_supply_growth": -0.08,
            "tax_rate": 0.12,
            "supply_chain_friction": 0.55,
            "sentiment": 0.08,
            "government_spending": 0.12,
        },
    },
    "goldilocks_1990s": {
        "name": "Goldilocks 1990s",
        "description": "Productivity boom, low inflation, strong equity bull market.",
        "levers": {
            "interest_rate": 0.05,
            "inflation_target": 0.02,
            "money_supply_growth": 0.055,
            "tax_rate": 0.21,
            "supply_chain_friction": 0.08,
            "sentiment": 0.72,
            "government_spending": 0.19,
        },
    },
}
