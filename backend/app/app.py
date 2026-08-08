"""
Flask API for the Interactive Macroeconomic Simulator.

Endpoints
---------
GET  /api/health                 — liveness probe
GET  /api/scenarios              — historical what-if presets
GET  /api/tooltips               — educational tooltip glossary
POST /api/simulate               — run a 5-year stochastic simulation
POST /api/household              — overlay a household balance sheet
POST /api/game/score             — score a central-banker game run
GET  /                           — serve the frontend (production)

The calculation engine lives in models.py; the insight layer in insights.py.
This module only validates payloads and serialises JSON.
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from models import (
    EconomicEngine, Levers, HouseholdProfile, compute_household_impact,
    score_game_run, GameConfig, SCENARIOS,
)
from insights import generate_insights, explain_lever_change, TOOLTIPS


FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

app = Flask(__name__, static_folder=None)
CORS(app)


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #

def _parse_levers(payload: dict) -> Levers:
    """Build a Levers dataclass from a JSON payload with sensible bounds."""
    def f(key, default, lo, hi):
        val = payload.get(key, default)
        try:
            val = float(val)
        except (TypeError, ValueError):
            val = default
        return max(lo, min(hi, val))

    return Levers(
        interest_rate=f("interest_rate", 0.045, -0.02, 0.25),
        inflation_target=f("inflation_target", 0.02, 0.0, 0.10),
        money_supply_growth=f("money_supply_growth", 0.05, -0.10, 0.40),
        tax_rate=f("tax_rate", 0.22, 0.0, 0.60),
        supply_chain_friction=f("supply_chain_friction", 0.10, 0.0, 1.0),
        sentiment=f("sentiment", 0.55, 0.02, 0.98),
        government_spending=f("government_spending", 0.20, 0.08, 0.45),
    )


# --------------------------------------------------------------------------- #
# API routes                                                                  #
# --------------------------------------------------------------------------- #

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "macroeconomic-simulator"})


@app.get("/api/scenarios")
def scenarios():
    return jsonify(SCENARIOS)


@app.get("/api/tooltips")
def tooltips():
    return jsonify(TOOLTIPS)


@app.post("/api/simulate")
def simulate():
    payload = request.get_json(silent=True) or {}
    levers = _parse_levers(payload)
    seed = payload.get("seed")
    if seed is not None:
        try:
            seed = int(seed)
        except (TypeError, ValueError):
            seed = None
    months = int(payload.get("months", 60))
    months = max(6, min(months, 240))
    shock_vol = float(payload.get("shock_volatility", 1.0))

    engine = EconomicEngine(levers, seed=seed, months=months,
                            shock_volatility=shock_vol)
    result = engine.run()

    result["insights"] = generate_insights(
        result["levers"], result["history"], result["shocks"]
    )
    return jsonify(result)


@app.post("/api/household")
def household():
    payload = request.get_json(silent=True) or {}
    history = payload.get("history", [])
    if not history:
        return jsonify({"error": "history is required"}), 400

    p = payload.get("profile", {})
    profile = HouseholdProfile(
        gross_salary=float(p.get("gross_salary", 75000)),
        mortgage_debt=float(p.get("mortgage_debt", 250000)),
        mortgage_rate=float(p.get("mortgage_rate", 0.065)),
        other_debt=float(p.get("other_debt", 15000)),
        other_debt_rate=float(p.get("other_debt_rate", 0.18)),
        savings=float(p.get("savings", 20000)),
        monthly_spend=float(p.get("monthly_spend", 3500)),
    )
    result = compute_household_impact(profile, history)
    return jsonify(result)


@app.post("/api/game/score")
def game_score():
    payload = request.get_json(silent=True) or {}
    sim = payload.get("simulation")
    if not sim or "history" not in sim:
        return jsonify({"error": "simulation object with history required"}), 400
    cfg_payload = payload.get("config", {})
    config = GameConfig(
        horizon_months=int(cfg_payload.get("horizon_months", 60)),
        target_inflation=float(cfg_payload.get("target_inflation", 0.02)),
        max_unemployment=float(cfg_payload.get("max_unemployment", 0.06)),
        initial_interest_rate=float(cfg_payload.get("initial_interest_rate", 0.045)),
    )
    score = score_game_run(sim, config)
    return jsonify(score)


@app.post("/api/insights/explain")
def explain():
    payload = request.get_json(silent=True) or {}
    lever = payload.get("lever", "")
    old = float(payload.get("old", 0))
    new = float(payload.get("new", 0))
    return jsonify(explain_lever_change(lever, old, new))


# --------------------------------------------------------------------------- #
# Serve the frontend (production / single-port deployment)                    #
# --------------------------------------------------------------------------- #

@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:path>")
def static_files(path):
    target = FRONTEND_DIR / path
    if target.is_file():
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
