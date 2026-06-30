"""
Streamlit dashboard for the DevOps Monitoring API.

Run the API first:
    uvicorn api.main:app --reload --port 8000

Then:
    streamlit run dashboard/app.py
"""

import time

import httpx
import pandas as pd
import streamlit as st

API_BASE = "http://localhost:8000"
DEFAULT_API_KEY = "dev-key"
MAX_HISTORY = 60

st.set_page_config(
    page_title="DevOps Monitoring Dashboard",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(ttl=2)
def fetch_metrics() -> dict:
    """Fetch live metrics from the API (cached 2 s)."""
    try:
        response = httpx.get(f"{API_BASE}/metrics", timeout=3.0)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"error": str(exc)}


@st.cache_data(ttl=5)
def fetch_servers() -> list[dict] | str:
    """Fetch the server list (cached 5 s)."""
    try:
        response = httpx.get(f"{API_BASE}/servers", timeout=3.0)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return str(exc)


def _status_color(val: str) -> str:
    colors = {
        "UP": "background-color: #d4edda; color: #155724",
        "DEGRADED": "background-color: #fff3cd; color: #856404",
        "DOWN": "background-color: #f8d7da; color: #721c24",
    }
    return colors.get(val, "")


def render_metrics_tab() -> None:
    """Tab 1 — live system metrics with history chart."""
    metrics = fetch_metrics()

    if "error" in metrics:
        st.error(f"Impossible de joindre l'API : {metrics['error']}")
        st.info("Lancez d'abord : `uvicorn api.main:app --reload --port 8000`")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("CPU", f"{metrics['cpu_percent']:.1f} %")
    col2.metric(
        "Mémoire",
        f"{metrics['memory_percent']:.1f} %",
        f"{metrics['memory_used_gb']:.1f} / {metrics['memory_total_gb']:.1f} GB",
    )
    col3.metric("Disque", f"{metrics['disk_percent']:.1f} %")

    if "metrics_history" not in st.session_state:
        st.session_state.metrics_history = []

    st.session_state.metrics_history.append(
        {
            "cpu_percent": metrics["cpu_percent"],
            "memory_percent": metrics["memory_percent"],
        }
    )
    if len(st.session_state.metrics_history) > MAX_HISTORY:
        st.session_state.metrics_history = st.session_state.metrics_history[-MAX_HISTORY:]

    if st.session_state.metrics_history:
        df = pd.DataFrame(st.session_state.metrics_history)
        st.line_chart(df[["cpu_percent", "memory_percent"]], height=250)
        st.caption(f"Dernières {len(st.session_state.metrics_history)} mesures (CPU & mémoire)")


def render_servers_tab() -> None:
    """Tab 2 — server list, registration form, manual health check."""
    if "api_key" not in st.session_state:
        st.session_state.api_key = DEFAULT_API_KEY

    st.session_state.api_key = st.text_input(
        "Clé API (pour POST /servers)",
        value=st.session_state.api_key,
        type="password",
    )

    servers = fetch_servers()
    if isinstance(servers, str):
        st.error(f"Impossible de charger les serveurs : {servers}")
    elif not servers:
        st.info("Aucun serveur enregistré.")
    else:
        df = pd.DataFrame(servers)
        styled = df.style.map(
            lambda v: _status_color(v) if isinstance(v, str) else "",
            subset=["status"],
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)

        ids = [s["id"] for s in servers]
        names = {s["id"]: f"[{s['id']}] {s['name']} ({s['status']})" for s in servers}
        selected_id = st.selectbox(
            "Serveur à vérifier",
            ids,
            format_func=lambda i: names[i],
        )
        if st.button("Lancer un health check"):
            try:
                response = httpx.post(
                    f"{API_BASE}/servers/{selected_id}/check",
                    timeout=5.0,
                )
                response.raise_for_status()
                fetch_servers.clear()
                st.success(response.json().get("message", "Vérification lancée."))
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    st.subheader("Enregistrer un serveur")
    with st.form("register_server", clear_on_submit=True):
        name = st.text_input("Nom", placeholder="api-prod")
        host = st.text_input("Hôte", placeholder="localhost")
        port = st.number_input("Port", min_value=1, max_value=65535, value=8000)
        submitted = st.form_submit_button("Enregistrer")

    if submitted:
        if not name or not host:
            st.error("Le nom et l'hôte sont obligatoires.")
        else:
            try:
                response = httpx.post(
                    f"{API_BASE}/servers",
                    json={"name": name, "host": host, "port": port},
                    headers={"X-API-Key": st.session_state.api_key},
                    timeout=5.0,
                )
                if response.status_code == 201:
                    fetch_servers.clear()
                    st.success(f"Serveur « {name} » enregistré (id={response.json()['id']}).")
                    st.rerun()
                else:
                    st.error(f"Erreur {response.status_code} : {response.text}")
            except Exception as exc:
                st.error(str(exc))


def main() -> None:
    st.title("📊 DevOps Monitoring Dashboard")

    tab_metrics, tab_servers = st.tabs(["Métriques", "Serveurs"])

    with tab_metrics:
        render_metrics_tab()

    with tab_servers:
        render_servers_tab()

    placeholder = st.empty()
    with placeholder.container():
        st.caption(f"Dernière mise à jour : {time.strftime('%H:%M:%S')} — actualisation toutes les 2 s")

    time.sleep(2)
    st.rerun()


if __name__ == "__main__":
    main()
