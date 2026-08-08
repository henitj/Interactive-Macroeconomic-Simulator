"""
Edu-Engine — dynamic plain-English explanations of economic cause & effect.

Given the levers AND the simulated trajectory, this module produces "insight"
cards that explain what is happening and why. It also hosts the tooltip /
glossary content used throughout the UI.
"""

from __future__ import annotations
from typing import Dict, List


TOOLTIPS: Dict[str, Dict[str, str]] = {
    "interest_rate": {
        "label": "Federal Funds Rate",
        "short": "The overnight rate at which banks lend reserves to each other.",
        "formula": "r_real ≈ i - π^e",
        "theory": (
            "The central bank's primary policy tool. Raising the nominal rate "
            "lifts real borrowing costs, cools interest-sensitive demand "
            "(housing, durables, capex), and tends to lower inflation over "
            "12-24 months. It also raises bond yields and compresses equity "
            "valuations via a higher discount rate."
        ),
    },
    "inflation_target": {
        "label": "Inflation Target",
        "short": "The central bank's stated annual CPI goal.",
        "formula": "π* = 2% (typical)",
        "theory": (
            "A credible target anchors long-run inflation expectations. "
            "When expectations are anchored, temporary price shocks fade "
            "instead of becoming a wage-price spiral."
        ),
    },
    "money_supply_growth": {
        "label": "Money Supply Growth (M2)",
        "short": "Annual growth of broad money in circulation.",
        "formula": "M*V = P*Y  →  π ≈ ΔM − ΔY (long run)",
        "theory": (
            "Quantity theory of money: over long horizons, printing money "
            "faster than real output grows shows up as inflation. The "
            "transmission is slow and lagged (6-18 months)."
        ),
    },
    "tax_rate": {
        "label": "Average Tax Rate",
        "short": "Effective tax share of personal income.",
        "formula": "Y_d = Y(1 − τ)",
        "theory": (
            "Higher taxes reduce disposable income, which suppresses "
            "consumption and aggregate demand. They may also reduce labor "
            "supply and investment incentives at the margin."
        ),
    },
    "supply_chain_friction": {
        "label": "Supply-Chain Friction",
        "short": "How clogged production and logistics are.",
        "formula": "Cost-push inflation: π ↑, Y ↓",
        "theory": (
            "Adverse supply shocks are stagflationary: they push prices up "
            "AND push output down simultaneously, the worst possible trade-off "
            "for a central bank."
        ),
    },
    "sentiment": {
        "label": "Market Sentiment",
        "short": "Confidence of consumers, CEOs and investors.",
        "formula": "Animal spirits → C, I ↑",
        "theory": (
            "Confidence shifts consumption and investment directly via "
            "'animal spirits' and indirectly via the equity risk premium. "
            "High sentiment = higher P/Es, tighter spreads, more spending."
        ),
    },
    "gdp": {
        "label": "Real GDP",
        "short": "Inflation-adjusted value of all goods & services produced.",
        "formula": "Y = C + I + G + (X − M)",
        "theory": (
            "The broadest measure of economic activity. Two consecutive "
            "quarters of negative growth is a common rule-of-thumb recession."
        ),
    },
    "inflation": {
        "label": "Inflation (CPI)",
        "short": "Annualised rate of change in consumer prices.",
        "formula": "π_t = (CPI_t / CPI_{t-12}) − 1",
        "theory": (
            "Driven by demand-pull (too much money chasing too few goods), "
            "cost-push (energy/supply shocks) and expectations."
        ),
    },
    "sp500": {
        "label": "Stock Market Index",
        "short": "Broad equity benchmark (S&P 500 proxy).",
        "formula": "P = E × (1 / (i + ERP + π))",
        "theory": (
            "Prices equal expected earnings discounted at a risk-adjusted "
            "rate. Higher rates/inflation/risk-premium compress valuations; "
            "higher earnings lift them."
        ),
    },
    "bond_yield": {
        "label": "10-Year Bond Yield",
        "short": "Annual return on long-dated government debt.",
        "formula": "y = i + tp + π^e",
        "theory": (
            "Long yields = expected policy path + term premium + inflation "
            "premium. Yields move opposite to bond prices."
        ),
    },
    "house_price": {
        "label": "Real Estate Index",
        "short": "Residential property price level.",
        "formula": "P_h ∝ income / mortgage_rate",
        "theory": (
            "Housing is extremely rate-sensitive. Higher mortgage rates raise "
            "monthly carrying costs and reduce what buyers can afford, "
            "pressuring prices; tight supply offsets this."
        ),
    },
    "commodity": {
        "label": "Commodity Index",
        "short": "Basket of energy, metals and agriculture.",
        "formula": "P_c ∝ demand × USD^{-1} × supply shock",
        "theory": (
            "Commodities are an inflation hedge and a growth barometer. They "
            "spike on supply disruptions and a weak dollar."
        ),
    },
    "nominal_wage": {
        "label": "Nominal Wage",
        "short": "Dollar amount paid, unadjusted for inflation.",
        "formula": "W_nominal = W_real × CPI",
        "theory": (
            "What your paycheck says. It can rise while you feel poorer if "
            "inflation rises faster."
        ),
    },
    "real_wage": {
        "label": "Real Wage",
        "short": "Purchasing power of wages after inflation.",
        "formula": "W_real = W_nominal / CPI",
        "theory": (
            "The true measure of living standards. Real wages fall when CPI "
            "outruns paychecks."
        ),
    },
    "purchasing_power": {
        "label": "Consumer Purchasing Power",
        "short": "Real disposable income net of debt service.",
        "formula": "PP = (1−τ)·W_real·(1−debt service)",
        "theory": (
            "What households can actually spend after taxes, inflation, and "
            "debt payments. The most human measure of macro conditions."
        ),
    },
    "unemployment": {
        "label": "Unemployment Rate",
        "short": "Share of the labor force without work but seeking it.",
        "formula": "u = U / LF",
        "theory": (
            "Okun's law links output growth to unemployment; the Phillips "
            "curve links tight labor markets to inflation."
        ),
    },
}


def _trend(history: List[Dict], key: str, window: int = 6) -> float:
    """Return last-vs-trailing-average gap (percentage points or index %)."""
    if len(history) < window + 1:
        return 0.0
    recent = sum(r[key] for r in history[-window:]) / window
    prev = sum(r[key] for r in history[-window * 2:-window]) / max(1, window)
    return recent - prev


def generate_insights(levers: Dict, history: List[Dict],
                      shocks: List[Dict]) -> List[Dict]:
    """
    Produce a list of insight cards.

    Each card: {title, body, severity, category}
    severity ∈ info | positive | warning | danger
    """
    insights: List[Dict] = []
    if not history:
        return insights

    end = history[-1]
    infl = end["inflation"]
    unemp = end["unemployment"]
    gdp_g = end["gdpGrowth"]
    rate = levers["interest_rate"] * 100
    supply = levers["supply_chain_friction"]
    senti = levers["sentiment"]
    m2 = levers["money_supply_growth"] * 100
    tax = levers["tax_rate"] * 100

    # ---------------------------------------------------------------- #
    # Inflation regime                                                 #
    # ---------------------------------------------------------------- #
    if infl > 6:
        insights.append({
            "category": "Inflation",
            "severity": "danger",
            "title": "Runaway Inflation",
            "body": (
                f"Prices are rising at {infl:.1f}% annually — far above the 2% "
                f"target. Money supply is growing at {m2:.1f}%/yr and supply "
                f"friction is {supply*100:.0f}%. Both demand-pull and "
                f"cost-push forces are active. Historically, anchoring "
                f"expectations requires the policy rate to exceed inflation "
                f"(currently {rate:.1f}% vs {infl:.1f}%)."
            ),
        })
    elif infl > 3.5:
        insights.append({
            "category": "Inflation",
            "severity": "warning",
            "title": "Above-Target Inflation",
            "body": (
                f"CPI is running at {infl:.1f}%, above the 2% target. "
                f"Real rates are {rate - infl:.1f}%. If real rates remain "
                f"negative, policy is still accommodative and inflation may "
                f"persist. Expect bond yields to drift higher."
            ),
        })
    elif infl < 0.5:
        insights.append({
            "category": "Inflation",
            "severity": "warning",
            "title": "Disinflation / Deflation Risk",
            "body": (
                f"Inflation is only {infl:.1f}%. Weak demand or a collapsing "
                f"money supply can tip the economy into deflation, where "
                f"consumers delay spending and real debt burdens grow."
            ),
        })
    else:
        insights.append({
            "category": "Inflation",
            "severity": "positive",
            "title": "Price Stability",
            "body": (
                f"Inflation at {infl:.1f}% is close to the 2% target. "
                f"Anchored expectations give the central bank room to "
                f"respond to shocks in either direction."
            ),
        })

    # ---------------------------------------------------------------- #
    # Labor market                                                     #
    # ---------------------------------------------------------------- #
    if unemp > 8:
        insights.append({
            "category": "Employment",
            "severity": "danger",
            "title": "Severe Labor Market Slack",
            "body": (
                f"Unemployment is {unemp:.1f}%. Okun's law implies output is "
                f"running well below potential. Wage growth will cool, easing "
                f"inflation, but at a severe social cost."
            ),
        })
    elif unemp > 5.5:
        insights.append({
            "category": "Employment",
            "severity": "warning",
            "title": "Rising Unemployment",
            "body": (
                f"Joblessness at {unemp:.1f}% is above the natural rate of "
                f"~4.5%. Slack in the labor market reduces workers' bargaining "
                f"power and relieves wage-push inflation."
            ),
        })
    elif unemp < 3.5:
        insights.append({
            "category": "Employment",
            "severity": "warning",
            "title": "Overheating Labor Market",
            "body": (
                f"Unemployment at {unemp:.1f}% is below the natural rate. "
                f"Tight labor markets fuel wage gains that can feed a "
                f"wage-price spiral if productivity doesn't keep up."
            ),
        })

    # ---------------------------------------------------------------- #
    # Growth / recession                                               #
    # ---------------------------------------------------------------- #
    if gdp_g < -2:
        insights.append({
            "category": "Growth",
            "severity": "danger",
            "title": "Sharp Contraction",
            "body": (
                f"GDP is shrinking at {gdp_g:.1f}% annualised. The economy is "
                f"in recession. Monetary easing and/or fiscal stimulus would "
                f"normally be deployed, but policy space depends on inflation."
            ),
        })
    elif gdp_g < 0:
        insights.append({
            "category": "Growth",
            "severity": "warning",
            "title": "Contracting Output",
            "body": (
                f"Growth has turned negative ({gdp_g:.1f}%). Watch for two "
                f"consecutive quarters — the textbook recession signal."
            ),
        })
    elif gdp_g > 4:
        insights.append({
            "category": "Growth",
            "severity": "positive",
            "title": "Booming Growth",
            "body": (
                f"Output is expanding at a blistering {gdp_g:.1f}% — above "
                f"the ~2% potential rate. Enjoy it, but unsustainably fast "
                f"growth eventually stokes inflation."
            ),
        })

    # ---------------------------------------------------------------- #
    # Monetary policy stance                                           #
    # ---------------------------------------------------------------- #
    real_rate = rate - infl
    if real_rate > 3:
        insights.append({
            "category": "Policy",
            "severity": "warning",
            "title": "Highly Restrictive Policy",
            "body": (
                f"The real policy rate is {real_rate:.1f}% — well above the "
                f"neutral ~0.5%. This will crush housing affordability, raise "
                f"debt-service costs and eventually pull inflation down, but "
                f"risks a recession."
            ),
        })
    elif real_rate < -1:
        insights.append({
            "category": "Policy",
            "severity": "warning",
            "title": "Accommodative / Negative Real Rates",
            "body": (
                f"With nominal rates at {rate:.1f}% and inflation at "
                f"{infl:.1f}%, real rates are {real_rate:.1f}%. Borrowers are "
                f"being paid to take on debt, which supports asset prices and "
                f"spending but can fuel bubbles if left in place too long."
            ),
        })

    # ---------------------------------------------------------------- #
    # Supply chain                                                     #
    # ---------------------------------------------------------------- #
    if supply > 0.6:
        insights.append({
            "category": "Supply",
            "severity": "danger",
            "title": "Severe Supply Disruption",
            "body": (
                f"Supply-chain friction is at {supply*100:.0f}%. This is a "
                f"textbook adverse supply shock: prices rise while output "
                f"falls — the central bank's worst dilemma."
            ),
        })
    elif supply > 0.35:
        insights.append({
            "category": "Supply",
            "severity": "warning",
            "title": "Elevated Supply Friction",
            "body": (
                f"Logistics stress at {supply*100:.0f}% is adding cost-push "
                f"pressure. Commodity prices and delivery lags are worth "
                f"monitoring."
            ),
        })

    # ---------------------------------------------------------------- #
    # Sentiment / financial markets                                    #
    # ---------------------------------------------------------------- #
    if senti < 0.3:
        insights.append({
            "category": "Markets",
            "severity": "warning",
            "title": "Risk-Off Sentiment",
            "body": (
                f"Sentiment is {senti*100:.0f}/100 — fear dominates. The "
                f"equity risk premium is elevated, compressing valuations, "
                f"and households are more likely to save than spend."
            ),
        })
    elif senti > 0.75:
        insights.append({
            "category": "Markets",
            "severity": "info",
            "title": "Euphoric Sentiment",
            "body": (
                f"Sentiment is {senti*100:.0f}/100. High confidence supports "
                f"spending and risk assets, but extremes often precede "
                f"reversals — watch for stretched valuations."
            ),
        })

    # ---------------------------------------------------------------- #
    # Household / real wages                                           #
    # ---------------------------------------------------------------- #
    pp_change = history[-1]["purchasingPower"] - history[0]["purchasingPower"]
    if pp_change < -5:
        insights.append({
            "category": "Households",
            "severity": "danger",
            "title": "Households Are Falling Behind",
            "body": (
                f"Consumer purchasing power has fallen by "
                f"{abs(pp_change):.1f}% since the start. Inflation is "
                f"outrunning paychecks, and higher rates are increasing "
                f"debt-service costs. Expect weaker discretionary spending."
            ),
        })
    elif pp_change > 5:
        insights.append({
            "category": "Households",
            "severity": "positive",
            "title": "Rising Living Standards",
            "body": (
                f"Purchasing power is up {pp_change:.1f}%. Real wage growth "
                f"and stable debt costs leave households with more "
                f"discretionary income — a tailwind for consumption."
            ),
        })

    # ---------------------------------------------------------------- #
    # Fiscal                                                           #
    # ---------------------------------------------------------------- #
    if tax > 30:
        insights.append({
            "category": "Fiscal",
            "severity": "info",
            "title": "High Tax Burden",
            "body": (
                f"An average tax rate of {tax:.0f}% reduces disposable "
                f"income and cools demand, but may improve fiscal balances."
            ),
        })

    # ---------------------------------------------------------------- #
    # Recent shock headline                                            #
    # ---------------------------------------------------------------- #
    if shocks:
        recent = shocks[-1]
        if recent["label"] == "negative":
            insights.append({
                "category": "Live Event",
                "severity": "warning",
                "title": f"Latest Shock: {recent['kind'].title()}",
                "body": recent["headline"],
            })
        elif recent["label"] == "positive":
            insights.append({
                "category": "Live Event",
                "severity": "positive",
                "title": f"Latest Tailwind: {recent['kind'].title()}",
                "body": recent["headline"],
            })

    return insights


def explain_lever_change(lever: str, old: float, new: float) -> Dict:
    """Produce a plain-English explanation when one slider is moved."""
    delta = new - old
    direction = "raised" if delta > 0 else "cut"
    pct = abs(delta) * 100

    explanations = {
        "interest_rate": {
            "title": f"Policy rate {direction} by {pct:.2f} pp",
            "body": (
                "Higher rates lift mortgage and loan costs, cool housing and "
                "business investment, raise bond yields, and reduce equity "
                "valuations. Inflation falls over 12-24 months but growth "
                "slows first. Cutting does the reverse."
            ),
            "channels": ["Housing demand", "Bond yields ↑", "Equity P/E ↓",
                         "Consumption ↓", "Inflation ↓ (lagged)"],
        },
        "money_supply_growth": {
            "title": f"Money growth {direction} to {new*100:.1f}%/yr",
            "body": (
                "Faster money creation supports near-term spending but feeds "
                "inflation with a 6-18 month lag (quantity theory). Slower "
                "growth removes liquidity, pressuring risk assets."
            ),
            "channels": ["Liquidity", "Inflation expectations", "Asset prices"],
        },
        "tax_rate": {
            "title": f"Tax rate {direction} to {new*100:.0f}%",
            "body": (
                "Tax changes hit disposable income directly. Higher taxes "
                "cool consumption and GDP; lower taxes stimulate them but may "
                "widen the deficit."
            ),
            "channels": ["Disposable income", "Consumption", "GDP"],
        },
        "supply_chain_friction": {
            "title": f"Supply-chain friction {direction}",
            "body": (
                "More friction means cost-push stagflation: prices rise AND "
                "output falls. Less friction is unambiguously good for both "
                "growth and inflation."
            ),
            "channels": ["Cost-push inflation", "Output", "Commodities"],
        },
        "sentiment": {
            "title": f"Sentiment shifted to {new*100:.0f}/100",
            "body": (
                "Animal spirits drive the equity risk premium, consumer "
                "spending and CEO capex decisions. A confident economy "
                "becomes a self-fulfilling boom — and vice versa."
            ),
            "channels": ["Equity risk premium", "Consumption", "Capex"],
        },
        "government_spending": {
            "title": f"Government spending {direction}",
            "body": (
                "Fiscal policy feeds directly into G in Y=C+I+G+NX. More "
                "spending adds to aggregate demand; austerity subtracts."
            ),
            "channels": ["Aggregate demand", "GDP", "Employment"],
        },
        "inflation_target": {
            "title": f"Inflation target set to {new*100:.1f}%",
            "body": (
                "The target anchors long-run expectations. A credible higher "
                "target permits slightly higher inflation but can unanchor "
                "expectations; a lower target requires tighter policy."
            ),
            "channels": ["Expectations", "Long yields"],
        },
    }

    base = explanations.get(lever, {
        "title": f"{lever} changed to {new}",
        "body": "Adjusting this parameter alters the economic trajectory.",
        "channels": [],
    })
    base["lever"] = lever
    base["old"] = old
    base["new"] = new
    base["delta"] = delta
    return base
