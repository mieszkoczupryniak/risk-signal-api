import os
import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List

import requests
import streamlit as st

# === Config ===

API_URL = os.getenv("RISKSIGNAL_API_URL", "http://localhost:8000")
DB_PATH = os.getenv("RISKSIGNAL_HISTORY_DB", "risksignal_history.db")


# === Simple SQLite storage for history ===

def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            context_label TEXT NOT NULL,
            run_type TEXT NOT NULL,          -- 'snapshot' or 'trend'
            overall_risk_score INTEGER,
            risk_level TEXT,
            top_risk_tags TEXT,              -- JSON list
            payload_json TEXT NOT NULL,      -- original request
            response_json TEXT NOT NULL      -- API response
        )
        """
    )
    conn.commit()
    conn.close()


def save_run(
    *,
    context_label: str,
    run_type: str,
    overall_risk_score: int | None,
    risk_level: str | None,
    top_risk_tags: List[str] | None,
    payload: Dict[str, Any],
    response: Dict[str, Any],
) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO runs (
            created_at, context_label, run_type,
            overall_risk_score, risk_level, top_risk_tags,
            payload_json, response_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.utcnow().isoformat(timespec="seconds") + "Z",
            context_label,
            run_type,
            overall_risk_score,
            risk_level,
            json.dumps(top_risk_tags or []),
            json.dumps(payload),
            json.dumps(response),
        ),
    )
    conn.commit()
    conn.close()


def load_runs() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            id, created_at, context_label, run_type,
            overall_risk_score, risk_level, top_risk_tags
        FROM runs
        ORDER BY created_at DESC
        LIMIT 100
        """
    )
    rows = cur.fetchall()
    conn.close()

    runs: List[Dict[str, Any]] = []
    for row in rows:
        run_id, created_at, context_label, run_type, score, level, tags_json = row
        try:
            tags = json.loads(tags_json) if tags_json else []
        except Exception:
            tags = []
        runs.append(
            {
                "id": run_id,
                "created_at": created_at,
                "context_label": context_label,
                "run_type": run_type,
                "overall_risk_score": score,
                "risk_level": level,
                "top_risk_tags": tags,
            }
        )
    return runs


def load_run_details(run_id: int) -> Dict[str, Any] | None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT payload_json, response_json
        FROM runs
        WHERE id = ?
        """,
        (run_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    payload_json, response_json = row
    return {
        "payload": json.loads(payload_json),
        "response": json.loads(response_json),
    }


# === Helper: parse textarea into NewsItemInput list ===

def parse_headlines_block(
    headlines_block: str,
    region: str | None = None,
    topic_hint: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Very simple parser:
    - split by newlines
    - ignore empty lines
    - build minimal NewsItemInput objects
    """
    items: List[Dict[str, Any]] = []
    for line in headlines_block.splitlines():
        headline = line.strip()
        if not headline:
            continue
        items.append(
            {
                "headline": headline,
                "body": None,
                "source": None,
                "published_at": None,
                "region": region or None,
                "topic_hint": topic_hint or None,
            }
        )
    return items


# === API client helpers ===

def check_health() -> bool:
    try:
        resp = requests.get(f"{API_URL}/health", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def call_risk_signal(payload: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.post(f"{API_URL}/risk-signal", json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def call_trend(payload: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.post(f"{API_URL}/risk-signal/trend", json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


# === Streamlit UI ===

def render_snapshot_tab() -> None:
    st.header("Single snapshot")

    st.markdown(
        "Paste a batch of headlines, pick an optional region/topic, and run a quick risk scan."
    )

    col1, col2 = st.columns(2)
    with col1:
        region = st.text_input("Region (optional, e.g. EU, US, MENA)", value="EU")
    with col2:
        topic_hint = st.text_input(
            "Topic hint (optional, e.g. energy, banking, defense)", value="energy"
        )

    headlines_block = st.text_area(
        "Headlines (one per line)",
        height=200,
        placeholder="EU considers new sanctions on Russian oil exports\n"
        "European banks face stress over energy sector exposure",
    )

    col_run1, col_run2 = st.columns(2)
    with col_run1:
        focus = st.text_input("Focus label (for context / history)", value="europe_energy")
    with col_run2:
        horizon_days = st.number_input(
            "Horizon (days)",
            min_value=1,
            max_value=365,
            value=7,
            step=1,
            key="snapshot_horizon_days",  # unikamy konfliktu ID
        )

    if st.button("Run risk scan", type="primary"):
        items = parse_headlines_block(
            headlines_block,
            region=region or None,
            topic_hint=topic_hint or None,
        )
        if not items:
            st.warning("Please enter at least one headline.")
            return

        payload = {
            "items": items,
            "focus": focus or None,
            "horizon_days": int(horizon_days),
        }

        with st.spinner("Calling /risk-signal..."):
            try:
                result = call_risk_signal(payload)
            except Exception as e:
                st.error(f"Error calling backend: {e}")
                return

        save_run(
            context_label=focus or "snapshot",
            run_type="snapshot",
            overall_risk_score=result.get("overall_risk_score"),
            risk_level=result.get("risk_level"),
            top_risk_tags=result.get("top_risk_tags"),
            payload=payload,
            response=result,
        )

        st.subheader("Overall risk")

        score = result.get("overall_risk_score", 0)
        level = result.get("risk_level", "unknown")
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Overall risk score", f"{score}/100")
        with col_b:
            level_color = {
                "low": "🟢",
                "medium": "🟡",
                "high": "🔴",
            }.get(level, "⚪")
            st.metric("Risk level", f"{level_color} {level}")

        st.subheader("Top risk tags")
        tags = result.get("top_risk_tags") or []
        if tags:
            for tag in tags:
                st.markdown(f"- `{tag}`")
        else:
            st.write("No dominant granular risk tags.")

        st.subheader("Per-headline breakdown")
        items_out = result.get("items") or []
        if items_out:
            rows = []
            for item in items_out:
                rows.append(
                    {
                        "headline": item.get("headline"),
                        "sentiment": item.get("sentiment"),
                        "categories": ", ".join(item.get("categories") or []),
                        "affects_score": item.get("affects_score"),
                        "risk_contribution": item.get("risk_contribution"),
                    }
                )
            st.dataframe(rows, hide_index=True)
        else:
            st.write("No per-headline data returned.")

        st.subheader("Summary")
        st.write(result.get("summary", ""))

        with st.expander("Methodology note"):
            st.write(result.get("methodology_note", ""))


def render_trend_tab() -> None:
    st.header("Trend between two periods")

    st.markdown(
        "Compare a baseline period vs a current period and see how the risk signal moved."
    )

    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        focus = st.text_input(
            "Focus label (for context / history)", value="europe_energy_trend"
        )
    with col_cfg2:
        horizon_days = st.number_input(
            "Horizon (days)",
            min_value=1,
            max_value=365,
            value=7,
            step=1,
            key="trend_horizon_days",  # drugi unikalny key
        )

    st.subheader("Baseline period headlines")
    baseline_block = st.text_area(
        "Baseline headlines (one per line)",
        height=150,
        key="baseline_block",
        placeholder="EU signals possible sanctions on Russian oil exports",
    )

    st.subheader("Current period headlines")
    current_block = st.text_area(
        "Current headlines (one per line)",
        height=150,
        key="current_block",
        placeholder="EU approves new sanctions package on Russian oil exports\n"
        "European banks face stress over energy exposure",
    )

    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        baseline_label = st.text_input("Baseline label", value="previous_week")
    with col_meta2:
        current_label = st.text_input("Current label", value="current_week")

    if st.button("Compute trend", type="primary"):
        baseline_items = parse_headlines_block(
            baseline_block, region="EU", topic_hint="energy"
        )
        current_items = parse_headlines_block(
            current_block, region="EU", topic_hint="energy"
        )

        if not baseline_items:
            st.warning("Please enter at least one baseline headline.")
            return
        if not current_items:
            st.warning("Please enter at least one current headline.")
            return

        payload = {
            "baseline": {
                "period_label": baseline_label,
                "items": baseline_items,
            },
            "current": {
                "period_label": current_label,
                "items": current_items,
            },
            "focus": focus or None,
            "horizon_days": int(horizon_days),
        }

        with st.spinner("Calling /risk-signal/trend..."):
            try:
                result = call_trend(payload)
            except Exception as e:
                st.error(f"Error calling backend: {e}")
                return

        current_score = (
            result.get("current", {}).get("overall_risk_score")
            if isinstance(result.get("current"), dict)
            else None
        )
        current_level = (
            result.get("current", {}).get("risk_level")
            if isinstance(result.get("current"), dict)
            else None
        )
        save_run(
            context_label=focus or "trend",
            run_type="trend",
            overall_risk_score=current_score,
            risk_level=current_level,
            top_risk_tags=result.get("driver_tags"),
            payload=payload,
            response=result,
        )

        st.subheader("Baseline vs current")

        baseline = result.get("baseline", {})
        current = result.get("current", {})
        delta = result.get("delta", {})

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Baseline score", f"{baseline.get('overall_risk_score', 0)}/100")
            st.caption(f"Level: {baseline.get('risk_level', 'unknown')}")
        with col2:
            st.metric("Current score", f"{current.get('overall_risk_score', 0)}/100")
            st.caption(f"Level: {current.get('risk_level', 'unknown')}")
        with col3:
            direction = delta.get("direction", "flat")
            score_change = delta.get("score_change", 0)
            arrow = {"up": "🔺", "down": "🔻", "flat": "➖"}.get(direction, "➖")
            st.metric("Delta", f"{score_change}", f"{arrow} {direction}")

        st.subheader("Trend comment")
        st.write(delta.get("comment", ""))

        st.subheader("Driver tags")
        driver_tags = result.get("driver_tags") or []
        if driver_tags:
            for tag in driver_tags:
                st.markdown(f"- `{tag}`")
        else:
            st.write("No clear driver tags identified.")

        with st.expander("Raw response (debug)"):
            st.json(result)


def render_history_tab() -> None:
    st.header("History")

    runs = load_runs()
    if not runs:
        st.write("No history yet. Run a snapshot or trend first.")
        return

    st.subheader("Recent runs")

    for run in runs:
        with st.expander(
            f"[{run['created_at']}] {run['context_label']} "
            f"({run['run_type']}, score={run['overall_risk_score']}, level={run['risk_level']})"
        ):
            st.write("Top tags:")
            tags = run.get("top_risk_tags") or []
            if tags:
                st.write(", ".join(tags))
            else:
                st.write("No tags recorded.")

            if st.button("Show details", key=f"details_{run['id']}"):
                details = load_run_details(run["id"])
                if not details:
                    st.error("Could not load run details.")
                else:
                    st.subheader("Request payload")
                    st.json(details["payload"])

                    st.subheader("Response")
                    st.json(details["response"])


def main() -> None:
    st.set_page_config(
        page_title="RiskSignal Terminal",
        page_icon="📈",
        layout="wide",
    )

    init_db()

    st.sidebar.title("RiskSignal Terminal")
    st.sidebar.markdown(f"Backend: `{API_URL}`")

    health_ok = check_health()
    if health_ok:
        st.sidebar.success("Backend health: OK")
    else:
        st.sidebar.error("Backend health: NOT OK")
        st.sidebar.write("Check that FastAPI is running on the configured URL.")

    tab1, tab2, tab3 = st.tabs(["Snapshot", "Trend", "History"])

    with tab1:
        render_snapshot_tab()
    with tab2:
        render_trend_tab()
    with tab3:
        render_history_tab()


if __name__ == "__main__":
    main()
