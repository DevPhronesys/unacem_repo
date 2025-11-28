"""
Interactive delivery distance dashboard using Streamlit.

The app expects an API that returns JSON with fields similar to:
- fecha_creacion or fecha_creacion_copia (date string)
- order_id
- no_orden
- organizacion (cliente)
- local (sede/pedido)
- lat_sede, lng_sede
- latitud_entrega, longitud_entrega

Run with:
    streamlit run dashboard.py --server.port 8501
"""

from __future__ import annotations

import math
from typing import Iterable, List, Tuple

import pandas as pd
import requests
import streamlit as st


DISTANCE_BINS_KM: List[float] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, math.inf]
DISTANCE_LABELS: Tuple[str, ...] = (
    "0-1 km",
    "1-2 km",
    "2-3 km",
    "3-4 km",
    "4-5 km",
    "5-6 km",
    "6-7 km",
    "7-8 km",
    "8-9 km",
    "9-10 km",
    ">10 km",
)

SPANISH_MONTHS = {
    1: "ENERO",
    2: "FEBRERO",
    3: "MARZO",
    4: "ABRIL",
    5: "MAYO",
    6: "JUNIO",
    7: "JULIO",
    8: "AGOSTO",
    9: "SETIEMBRE",
    10: "OCTUBRE",
    11: "NOVIEMBRE",
    12: "DICIEMBRE",
}

DEFAULT_API_URL = "https://retoolapi.dev/dle9do/data"
REQUIRED_COLUMNS = {
    "organizacion",
    "local",
    "lat_sede",
    "lng_sede",
    "latitud_entrega",
    "longitud_entrega",
    "order_id",
    "no_orden",
}


@st.cache_data(show_spinner=False)
def fetch_data(api_url: str) -> pd.DataFrame:
    """Fetch JSON data from the API and normalize into a DataFrame."""
    response = requests.get(api_url, timeout=30)
    response.raise_for_status()
    payload = response.json()
    frame = pd.DataFrame(payload)
    if frame.empty:
        raise ValueError("El API devolvió una lista vacía de órdenes.")
    return frame


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute distance between two lat/lon points in kilometers."""
    radius_km = 6371.0
    lat1_r, lon1_r, lat2_r, lon2_r = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return radius_km * c


def ensure_datetime(df: pd.DataFrame) -> pd.Series:
    """Return a datetime series using the available creation column."""
    date_columns = [col for col in df.columns if col.startswith("fecha_creacion")]
    if not date_columns:
        raise KeyError("No date column found. Expected `fecha_creacion` or `fecha_creacion_copia`.")
    parsed = pd.to_datetime(df[date_columns[0]], errors="coerce")
    if parsed.isna().all():
        raise ValueError("Date column could not be parsed; please ensure ISO or YYYY-MM-DD format.")
    return parsed


def validate_columns(df: pd.DataFrame) -> None:
    """Raise a clear error if any required column is missing."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise KeyError(
            "Faltan columnas requeridas: " + ", ".join(missing) + ". "
            "Verifica que el API exponga los campos esperados."
        )


def attach_computed_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Add month, distance and distance range columns."""
    validate_columns(df)
    df = df.copy()
    created_at = ensure_datetime(df)
    df["mes_period"] = created_at.dt.to_period("M")
    df["mes_nombre"] = df["mes_period"].apply(
        lambda p: f"{SPANISH_MONTHS.get(p.month, '').upper()} {p.year}".strip()
    )
    df["mes"] = df["mes_period"].astype(str)

    df["distancia_km"] = df.apply(
        lambda row: haversine_km(
            float(row["lat_sede"]),
            float(row["lng_sede"]),
            float(row["latitud_entrega"]),
            float(row["longitud_entrega"]),
        ),
        axis=1,
    )

    df["rango_distancia_km"] = pd.cut(
        df["distancia_km"],
        bins=DISTANCE_BINS_KM,
        labels=DISTANCE_LABELS,
        right=False,
        include_lowest=True,
    )
    return df


def filter_frame(df: pd.DataFrame, months: Iterable[str], clients: Iterable[str], sedes: Iterable[str]) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if months:
        mask &= df["mes_nombre"].isin(months)
    if clients:
        mask &= df["organizacion"].isin(clients)
    if sedes:
        mask &= df["local"].isin(sedes)
    return df[mask]


def render_filters(df: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
    st.sidebar.header("Filtros")
    month_order = (
        df.sort_values("mes_period")[["mes_nombre", "mes_period"]]
        .drop_duplicates(subset="mes_period")
        .reset_index(drop=True)
    )
    selected_months = st.sidebar.multiselect("Mes", month_order["mes_nombre"].tolist())
    selected_clients = st.sidebar.multiselect(
        "Cliente (organización)", sorted(df["organizacion"].unique())
    )
    selected_sedes = st.sidebar.multiselect("Sede / local", sorted(df["local"].unique()))
    return selected_months, selected_clients, selected_sedes


def render_distance_matrix(df: pd.DataFrame) -> None:
    st.subheader("Órdenes por rango de distancia (km)")
    if df.empty:
        st.info("No hay órdenes para mostrar en la matriz.")
        return

    counts = (
        df.pivot_table(
            index="mes_nombre",
            columns="rango_distancia_km",
            values="order_id",
            aggfunc="count",
            fill_value=0,
        )
        .reindex(columns=DISTANCE_LABELS, fill_value=0)
    )

    # Ordenar filas por el mes original
    month_order = (
        df.sort_values("mes_period")[["mes_nombre", "mes_period"]]
        .drop_duplicates(subset="mes_period")
        .set_index("mes_nombre")
    )
    counts = counts.loc[[idx for idx in month_order.index if idx in counts.index]]

    row_totals = counts.sum(axis=1)
    grand_total = row_totals.sum()
    percentages = counts.div(row_totals.replace(0, pd.NA), axis=0) * 100

    formatted = pd.DataFrame(index=counts.index)
    for label in DISTANCE_LABELS:
        formatted[(label, "Órdenes")] = counts[label]
        formatted[(label, "%" )] = percentages[label].round(1).fillna(0)

    formatted[("Total", "Órdenes")] = row_totals
    formatted[("Total", "%" )] = (row_totals / grand_total * 100).round(1).fillna(0)

    # Agregar fila de totales generales
    totals_row = pd.DataFrame({
        (label, "Órdenes"): counts[label].sum() for label in DISTANCE_LABELS
    }, index=["TOTAL"])
    totals_row[("Total", "Órdenes")] = grand_total
    totals_row[("Total", "%" )] = 100.0 if grand_total else 0.0
    for label in DISTANCE_LABELS:
        totals_row[(label, "%")] = (
            counts[label].sum() / grand_total * 100 if grand_total else 0.0
        ).__round__(1)

    final_matrix = pd.concat([formatted, totals_row])
    final_matrix.columns = pd.MultiIndex.from_tuples(final_matrix.columns)

    percent_columns = {(label, "%"): "{:.1f}%" for label in list(DISTANCE_LABELS) + ["Total"]}
    st.dataframe(
        final_matrix.style.format(percent_columns).format("{:.0f}", na_rep="0")
    )


def render_map(df: pd.DataFrame) -> None:
    st.subheader("Mapa de sedes y entregas")
    sede_points = df[["local", "lat_sede", "lng_sede"]].drop_duplicates().rename(
        columns={"lat_sede": "lat", "lng_sede": "lon"}
    )
    sede_points["tipo"] = "Sede"

    entrega_points = df[["order_id", "latitud_entrega", "longitud_entrega", "local"]].rename(
        columns={"latitud_entrega": "lat", "longitud_entrega": "lon"}
    )
    entrega_points["tipo"] = "Entrega"

    map_df = pd.concat(
        [sede_points[["lat", "lon", "tipo", "local"]], entrega_points[["lat", "lon", "tipo", "local"]]]
    )

    layer = {
        "Sede": {
            "color": [0, 112, 243],
            "radius": 120,
        },
        "Entrega": {
            "color": [237, 104, 71],
            "radius": 80,
        },
    }

    view_state = {
        "latitude": map_df["lat"].mean() if not map_df.empty else -12.05,
        "longitude": map_df["lon"].mean() if not map_df.empty else -77.04,
        "zoom": 11,
    }

    layers = []
    for tipo, config in layer.items():
        subset = map_df[map_df["tipo"] == tipo]
        if subset.empty:
            continue
        layers.append(
            {
                "type": "ScatterplotLayer",
                "data": subset,
                "get_position": "[lon, lat]",
                "get_fill_color": config["color"],
                "get_radius": config["radius"],
                "pickable": True,
            }
        )

    tooltip = {"text": "{tipo}: {local}"}
    st.pydeck_chart({"layers": layers, "initialViewState": view_state, "tooltip": tooltip})


def render_app(df: pd.DataFrame) -> None:
    st.title("Órdenes por Cliente")
    st.caption(
        "Filtra por mes, cliente y sede para analizar las distancias entre las sedes y los puntos de entrega."
    )

    filtered = df
    months, clients, sedes = render_filters(df)
    filtered = filter_frame(filtered, months, clients, sedes)

    col1, col2, col3 = st.columns(3)
    col1.metric("Órdenes filtradas", len(filtered))
    col2.metric(
        "Distancia promedio (km)",
        f"{filtered['distancia_km'].mean():.2f}" if not filtered.empty else "N/A",
    )
    col3.metric(
        "Clientes únicos", len(filtered["organizacion"].unique()) if not filtered.empty else 0
    )

    render_distance_matrix(filtered)

    st.subheader("Detalle de órdenes")
    date_column = "fecha_creacion" if "fecha_creacion" in filtered.columns else "fecha_creacion_copia"
    detail = filtered[
        [
            date_column,
            "mes_nombre",
            "organizacion",
            "local",
            "order_id",
            "no_orden",
            "distancia_km",
            "rango_distancia_km",
        ]
    ].rename(
        columns={
            date_column: "fecha_creacion",
            "organizacion": "cliente",
            "local": "sede/pedido",
            "rango_distancia_km": "rango_km",
        }
    )
    detail["distancia_km"] = detail["distancia_km"].round(2)
    st.dataframe(detail)

    render_map(filtered)


def main() -> None:
    st.set_page_config(page_title="Dashboard de entregas", layout="wide")
    st.sidebar.title("Fuente de datos")
    api_url = st.sidebar.text_input("API URL", value=DEFAULT_API_URL, help="Endpoint que devuelve la lista de órdenes en formato JSON.")

    if not api_url:
        st.info("Ingresa la URL del API en la barra lateral para cargar datos.")
        return

    try:
        with st.spinner("Descargando y procesando datos..."):
            df_raw = fetch_data(api_url)
            df = attach_computed_fields(df_raw)
    except Exception as exc:  # noqa: BLE001
        st.error(f"No se pudieron cargar los datos: {exc}")
        return

    render_app(df)


if __name__ == "__main__":
    main()
