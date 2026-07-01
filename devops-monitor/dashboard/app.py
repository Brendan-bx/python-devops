"""
DevOps Monitoring Dashboard — Streamlit frontend.

Connects to the FastAPI backend for live metrics and server management.
"""

import os
import time

import httpx
import pandas as pd
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
HISTORY_WINDOW = 60

st.set_page_config(
    page_title="DevOps Monitor",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(ttl=2)
def fetch_metrics() -> dict:
    """Fetch current system metrics from the API."""
    try:
        response = httpx.get(f"{API_BASE}/metrics", timeout=3.0)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"error": str(exc)}


@st.cache_data(ttl=5)
def fetch_servers() -> list[dict] | str:
    """Fetch the list of registered servers."""
    try:
        response = httpx.get(f"{API_BASE}/servers", timeout=3.0)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return str(exc)


def status_color(status: str) -> str:
    """Return a background color for a server status."""
    colors = {
        "UP": "background-color: #d4edda; color: #155724",
        "DEGRADED": "background-color: #fff3cd; color: #856404",
        "DOWN": "background-color: #f8d7da; color: #721c24",
        "UNKNOWN": "background-color: #e2e3e5; color: #383d41",
    }
    return colors.get(status, colors["UNKNOWN"])


# ─── Session state ────────────────────────────────────────────────────────────

if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("API_KEY", "")

if "metrics_history" not in st.session_state:
    st.session_state.metrics_history = []

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Paramètres")
    st.session_state.api_key = st.text_input(
        "Clé API",
        value=st.session_state.api_key,
        type="password",
    )
    refresh_interval = st.slider("Rafraîchissement (s)", min_value=1, max_value=10, value=2)

st.title("📊 DevOps Monitoring Dashboard")

tab_metrics, tab_servers = st.tabs(["Métriques", "Serveurs"])

# ─── Metrics tab ──────────────────────────────────────────────────────────────

with tab_metrics:
    metrics = fetch_metrics()

    if "error" in metrics:
        st.error(f"Impossible de joindre l'API : {metrics['error']}")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("CPU", f"{metrics['cpu_percent']:.1f} %")
        col2.metric("Mémoire", f"{metrics['memory_percent']:.1f} %")
        col3.metric("Disque", f"{metrics['disk_percent']:.1f} %")

        timestamp = time.time()
        st.session_state.metrics_history.append(
            {
                "ts": timestamp,
                "cpu_percent": metrics["cpu_percent"],
                "memory_percent": metrics["memory_percent"],
                "disk_percent": metrics["disk_percent"],
            }
        )
        cutoff = timestamp - HISTORY_WINDOW
        st.session_state.metrics_history = [
            point for point in st.session_state.metrics_history if point["ts"] >= cutoff
        ]

        if st.session_state.metrics_history:
            history_df = pd.DataFrame(st.session_state.metrics_history)
            history_df["time"] = pd.to_datetime(history_df["ts"], unit="s")
            chart_df = history_df.set_index("time")[
                ["cpu_percent", "memory_percent", "disk_percent"]
            ]
            st.line_chart(chart_df, height=300)
            st.caption(f"Fenêtre glissante de {HISTORY_WINDOW} secondes")

# ─── Servers tab ──────────────────────────────────────────────────────────────

with tab_servers:
    with st.form("register_server", clear_on_submit=True):
        st.subheader("Enregistrer un serveur")
        name = st.text_input("Nom", placeholder="api-prod")
        host = st.text_input("Hôte", placeholder="10.0.0.1")
        port = st.number_input("Port", min_value=1, max_value=65535, value=8000)
        submitted = st.form_submit_button("Enregistrer")

    if submitted:
        if not name or not host:
            st.error("Le nom et l'hôte sont obligatoires.")
        elif not st.session_state.api_key:
            st.error("La clé API est requise pour enregistrer un serveur.")
        else:
            try:
                response = httpx.post(
                    f"{API_BASE}/servers",
                    json={"name": name, "host": host, "port": int(port)},
                    headers={"X-API-Key": st.session_state.api_key},
                    timeout=5.0,
                )
                if response.status_code == 201:
                    st.success(f"Serveur « {name} » enregistré.")
                    fetch_servers.clear()
                else:
                    st.error(f"Erreur {response.status_code} : {response.text}")
            except Exception as exc:
                st.error(str(exc))

    servers = fetch_servers()

    if isinstance(servers, str):
        st.error(f"Impossible de charger les serveurs : {servers}")
    elif not servers:
        st.info("Aucun serveur enregistré.")
    else:
        df = pd.DataFrame(servers)

        def highlight_status(val: str) -> str:
            return status_color(val)

        styled = df.style.map(highlight_status, subset=["status"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

        with st.expander("Actions"):
            server_ids = [s["id"] for s in servers]
            labels = {s["id"]: f"[{s['id']}] {s['name']} ({s['status']})" for s in servers}
            selected_id = st.selectbox(
                "Serveur",
                server_ids,
                format_func=lambda i: labels[i],
            )
            col_check, col_delete = st.columns(2)

            with col_check:
                if st.button("Vérifier maintenant"):
                    try:
                        response = httpx.post(
                            f"{API_BASE}/servers/{selected_id}/check",
                            timeout=5.0,
                        )
                        if response.status_code == 200:
                            st.success(f"Statut : {response.json()['status']}")
                            fetch_servers.clear()
                        else:
                            st.error(f"Erreur {response.status_code}")
                    except Exception as exc:
                        st.error(str(exc))

            with col_delete:
                if st.button("Supprimer", type="primary"):
                    if not st.session_state.api_key:
                        st.error("La clé API est requise pour supprimer un serveur.")
                    else:
                        try:
                            response = httpx.delete(
                                f"{API_BASE}/servers/{selected_id}",
                                headers={"X-API-Key": st.session_state.api_key},
                                timeout=5.0,
                            )
                            if response.status_code == 204:
                                st.success("Serveur supprimé.")
                                fetch_servers.clear()
                                st.rerun()
                            else:
                                st.error(f"Erreur {response.status_code}")
                        except Exception as exc:
                            st.error(str(exc))

# ─── Auto-refresh ─────────────────────────────────────────────────────────────

st.caption(f"Dernière mise à jour : {time.strftime('%H:%M:%S')}")
time.sleep(refresh_interval)
st.rerun()
