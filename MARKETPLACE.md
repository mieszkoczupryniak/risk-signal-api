RiskSignal is a lightweight news-based risk signal engine for macro, EM and sector teams. It ingests batches of headlines and returns a 0–100 risk score with explainable driver tags (e.g. `energy_supply_risk_eu`, `banking_stress_eu`, `regulatory_risk_eu`) plus simple trend information between two periods.

The project ships as a FastAPI microservice and a Streamlit “RiskSignal Terminal” (Snapshot / Trend / History) so analysts can either integrate the API into their own dashboards or use a ready-made UI to scan news, see how risk is moving, and review past runs without touching Python.

### What it does

- Scores batches of news headlines on a 0–100 risk scale with low / medium / high bands.
- Attaches granular driver tags so you can see *why* risk is moving for a theme.
- Compares two periods (e.g. previous vs current week) and returns direction, delta and main drivers.
- Logs runs into a simple SQLite history so you can revisit past stress episodes.
- Runs locally via FastAPI + Streamlit or inside a container (Docker / Railway).

### Who it’s for

- Macro and EM portfolio managers who want a quick, explainable risk view by theme.
- Risk managers tracking sanctions, regulatory headlines and banking stress without building an NLP stack.
- Research / data teams who need a small, composable signal generator to plug into dashboards or models.