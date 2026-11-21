"""San Francisco Crust Pizza — Dashboard comercial (sin indicador de margen bruto).

Datos exclusivamente de los tres archivos Excel proporcionados.
Para actualizar ventas: usar el cargador lateral o reemplazar el Excel de ventas
conservando el esquema de columnas, sin modificar este archivo de código.
"""

import os
import json
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="San Francisco Crust Pizza | Dashboard Comercial",
    page_icon="🍕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Fondo beige, contraste suficiente y tarjetas claras para presentación ejecutiva.
st.markdown(
    """
    <style>
      html, body, [data-testid="stAppViewContainer"] { background-color: #FBF8F3; }
      [data-testid="stSidebar"] { background: #F2EDE5; }
      .block-container { max-width: 1500px; padding: 1.5rem 2.3rem 3rem; }
      h1, h2, h3 { color: #46392E !important; letter-spacing: -.02em; }
      h1 { font-size: 2.4rem !important; }
      h2 { font-size: 1.62rem !important; }
      h3 { font-size: 1.24rem !important; }
      [data-testid="stMetric"] {
        border: 1px solid #E5DACC; border-radius: 16px;
        padding: 18px 20px; background: #FFFFFF;
        box-shadow: 0 3px 14px rgba(80, 61, 45, .045);
      }
      [data-testid="stMetricLabel"] { color: #6F6155; font-weight: 650; font-size: 1rem; }
      [data-testid="stMetricValue"] { color: #3C3026; font-size: 1.82rem; font-weight: 760; }
      [data-testid="stVerticalBlockBorderWrapper"] { border-color: #E9DFD3; }
      [data-testid="stSidebar"] h2 { font-size: 1.25rem !important; }
      div.stButton > button[kind="primary"] { background: #A34E38; border-color: #A34E38; }
      .subtitle { color: #736557; margin-top: -.3rem; font-size: 1.05rem; }
      .section-note { color: #85776C; font-size: .95rem; }
      .stCaption { font-size: .94rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

REQUIRED = {
    "ventas": ["VentaID", "Fecha", "Ciudad", "Sucursal", "ClienteID", "ProductoID", "Cantidad", "VentaNeta", "CostoTotal", "UtilidadBruta"],
    "clientes": ["ClienteID", "Segmento"],
    "productos": ["ProductoID", "Producto", "Categoria"],
}
COLORS = ["#B95F45", "#4D8B7B", "#D29A52", "#7C79A6", "#638DB6", "#A36C89", "#A5A16F"]
PLOT_BG = "#FFFFFF"


@st.cache_data(show_spinner="Procesando archivo Excel…")
def load_excel(raw: bytes) -> pd.DataFrame:
    return pd.read_excel(BytesIO(raw), engine="openpyxl")


def default_file(kind: str) -> Path | None:
    """Busca los archivos originales en la raíz y, como alternativa, en data/."""
    parent = Path(__file__).resolve().parent
    candidates = []
    for folder in (parent, parent / "data"):
        if folder.is_dir():
            candidates.extend(folder.glob("*.xlsx"))
    suffix = f"_{kind.lower()}.xlsx"
    matches = [p for p in candidates if p.name.lower().endswith(suffix)]
    return sorted(matches, key=lambda p: (p.parent != parent, p.name.lower()))[0] if matches else None


def read_input(upload, kind: str) -> pd.DataFrame:
    if upload is not None:
        content = upload.getvalue()
        source = upload.name
    else:
        file = default_file(kind)
        if not file:
            st.error(f"Falta el archivo Excel de {kind}. Cárgalo en el panel izquierdo.")
            st.stop()
        content, source = file.read_bytes(), file.name
    try:
        data = load_excel(content).copy()
    except Exception as exc:
        st.error(f"No se pudo leer el Excel de {kind} ({source}): {exc}")
        st.stop()
    data.columns = data.columns.astype(str).str.strip()
    missing = set(REQUIRED[kind]) - set(data.columns)
    if missing:
        st.error(f"El archivo de {kind} no cumple el esquema. Columnas faltantes: {', '.join(sorted(missing))}.")
        st.stop()
    return data


def chart(fig, height=360):
    fig.update_layout(
        height=height, paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG,
        margin=dict(l=18, r=24, t=63, b=32),
        font=dict(family="Arial", size=14, color="#4C423A"),
        title_font=dict(size=18, color="#44372E"),
        legend=dict(orientation="h", y=-0.20, x=0),
        hoverlabel=dict(bgcolor="#FFFFFF", font_size=13),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#EEE7DF", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#EEE7DF", zeroline=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def usd(value: float) -> str:
    return f"USD {value:,.2f}"


st.title("🍕 San Francisco Crust Pizza")
st.markdown('<p class="subtitle">Sistema inteligente de apoyo a las decisiones · Dashboard comercial</p>', unsafe_allow_html=True)

with st.sidebar:
    st.header("📁 Actualización de datos")
    st.write("Cambia cualquiera de las bases Excel sin modificar el código. Todos los indicadores y gráficos se recalculan al cargarla.")
    u_ventas = st.file_uploader("Reemplazar ventas (.xlsx)", type=["xlsx"], key="ventas_upload")
    u_clientes = st.file_uploader("Reemplazar clientes (.xlsx)", type=["xlsx"], key="clientes_upload")
    u_productos = st.file_uploader("Reemplazar productos (.xlsx)", type=["xlsx"], key="productos_upload")
    st.caption("La carga sustituye temporalmente esa base en la sesión. Los archivos originales del servidor no se modifican.")
    st.divider()
    st.caption("Fuente: exclusivamente Ventas, Clientes y Productos de San Francisco Crust Pizza.")

ventas = read_input(u_ventas, "ventas")
clientes = read_input(u_clientes, "clientes")
productos = read_input(u_productos, "productos")

for data, col in ((clientes, "ClienteID"), (productos, "ProductoID")):
    data[col] = data[col].astype(str).str.strip()
for col in ("VentaID", "ClienteID", "ProductoID"):
    ventas[col] = ventas[col].astype(str).str.strip()

if clientes.ClienteID.duplicated().any() or productos.ProductoID.duplicated().any():
    st.error("Hay identificadores duplicados en los archivos de clientes o productos. Corrige los archivos antes de continuar.")
    st.stop()
ventas["Fecha"] = pd.to_datetime(ventas["Fecha"], errors="coerce")
for col in ("Cantidad", "VentaNeta", "CostoTotal", "UtilidadBruta"):
    ventas[col] = pd.to_numeric(ventas[col], errors="coerce")
invalid_rows = int(ventas[["Fecha", "Cantidad", "VentaNeta", "CostoTotal"]].isna().any(axis=1).sum())
if invalid_rows:
    st.error(f"Hay {invalid_rows:,} filas con fechas, cantidades, ventas o costos inválidos; corrige el Excel de ventas.")
    st.stop()
if ventas.empty:
    st.error("El archivo de ventas está vacío.")
    st.stop()

# Utilidad bruta conservada; NO se calcula ni presenta el indicador de margen bruto.
ventas["UtilidadCalculada"] = ventas["VentaNeta"] - ventas["CostoTotal"]
base = ventas.merge(
    clientes[["ClienteID", "Segmento"]], on="ClienteID", how="left",
    validate="many_to_one", indicator="_cliente_match"
)
prod_cols = ["ProductoID", "Producto", "Categoria"] + (["Tamaño"] if "Tamaño" in productos.columns else [])
base = base.merge(
    productos[prod_cols], on="ProductoID", how="left",
    validate="many_to_one", indicator="_producto_match"
)
base["Segmento"] = base["Segmento"].fillna("Sin clasificar")
base["Producto"] = base["Producto"].fillna("Sin identificar")
base["Categoria"] = base["Categoria"].fillna("Sin categoría")
base["ProductoDetalle"] = base["Producto"].astype(str)
if "Tamaño" in base.columns:
    base["ProductoDetalle"] += " · " + base["Tamaño"].fillna("").astype(str)

# Filtros horizontales (no en la barra lateral), como se solicitó en el proyecto.
st.subheader("🎛️ Filtros interactivos")
min_date, max_date = base["Fecha"].min().date(), base["Fecha"].max().date()
with st.container(border=True):
    c1, c2, c3, c4 = st.columns([1.7, 1.2, 1.2, 1.2])
    with c1:
        date_range = st.date_input("Período", (min_date, max_date), min_value=min_date, max_value=max_date)
    with c2:
        ciudades = st.multiselect("Ciudad", sorted(base["Ciudad"].dropna().astype(str).unique()), placeholder="Todas")
    with c3:
        suc_opts = base[base["Ciudad"].isin(ciudades)] if ciudades else base
        sucursales = st.multiselect("Sucursal", sorted(suc_opts["Sucursal"].dropna().astype(str).unique()), placeholder="Todas")
    with c4:
        segmentos = st.multiselect("Segmento", sorted(base["Segmento"].dropna().astype(str).unique()), placeholder="Todos")
    p1, p2 = st.columns([2.4, 1])
    with p1:
        prods = st.multiselect("Producto", sorted(base["ProductoDetalle"].dropna().astype(str).unique()), placeholder="Todos los productos")
    with p2:
        st.caption("Los filtros son combinables. Si no se selecciona un valor, se incluyen todos.")

f = base.copy()
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    f = f[f["Fecha"].dt.date.between(date_range[0], date_range[1])]
if ciudades:
    f = f[f["Ciudad"].isin(ciudades)]
if sucursales:
    f = f[f["Sucursal"].isin(sucursales)]
if segmentos:
    f = f[f["Segmento"].isin(segmentos)]
if prods:
    f = f[f["ProductoDetalle"].isin(prods)]
if f.empty:
    st.warning("No hay registros con los filtros seleccionados.")
    st.stop()

ventas_total = float(f["VentaNeta"].sum())
utilidad = float(f["UtilidadCalculada"].sum())
transacciones = int(f["VentaID"].nunique())
clientes_unicos = int(f["ClienteID"].nunique())
unidades = float(f["Cantidad"].sum())
ticket = ventas_total / transacciones if transacciones else 0.0

st.subheader("Indicadores ejecutivos")
metrics = [
    ("Ventas netas", usd(ventas_total)),
    ("Utilidad bruta", usd(utilidad)),
    ("Ticket promedio", usd(ticket)),
    ("Transacciones", f"{transacciones:,}"),
    ("Clientes únicos", f"{clientes_unicos:,}"),
    ("Unidades vendidas", f"{unidades:,.0f}"),
]
row1 = st.columns(3, gap="medium")
row2 = st.columns(3, gap="medium")
for col, (label, value) in zip([*row1, *row2], metrics):
    col.metric(label, value)
st.caption("Utilidad bruta = ventas netas − costo total. Ticket promedio = ventas netas ÷ transacciones únicas.")

st.subheader("Evolución comercial")
by_month = (
    f.assign(Mes=f["Fecha"].dt.to_period("M").dt.to_timestamp())
    .groupby("Mes", as_index=False)
    .agg(Ventas=("VentaNeta", "sum"), Utilidad=("UtilidadCalculada", "sum"), Transacciones=("VentaID", "nunique"))
    .sort_values("Mes")
)
left, right = st.columns([1.55, 1], gap="large")
with left:
    fig = px.line(
        by_month, x="Mes", y=["Ventas", "Utilidad"], markers=True,
        title="Ventas netas y utilidad bruta por mes",
        labels={"value": "USD", "variable": "Indicador", "Mes": "Mes"},
        color_discrete_sequence=[COLORS[0], COLORS[1]],
    )
    fig.update_traces(line_width=3, marker_size=7)
    chart(fig)
with right:
    fig = px.bar(
        by_month, x="Mes", y="Transacciones", title="Transacciones por mes",
        labels={"Mes": "Mes", "Transacciones": "Transacciones"},
        color_discrete_sequence=[COLORS[2]],
    )
    chart(fig)

st.subheader("Desempeño por ubicación")
left, right = st.columns(2, gap="large")
with left:
    city = f.groupby("Ciudad", as_index=False)["VentaNeta"].sum().sort_values("VentaNeta", ascending=True)
    fig = px.bar(
        city, x="VentaNeta", y="Ciudad", orientation="h",
        title="Ventas por ciudad", labels={"VentaNeta": "Ventas (USD)", "Ciudad": ""},
        color_discrete_sequence=[COLORS[1]],
    )
    chart(fig)
with right:
    branch = f.groupby("Sucursal", as_index=False)["VentaNeta"].sum().nlargest(15, "VentaNeta").sort_values("VentaNeta")
    fig = px.bar(
        branch, x="VentaNeta", y="Sucursal", orientation="h",
        title="Sucursales con mayores ventas · Top 15",
        labels={"VentaNeta": "Ventas (USD)", "Sucursal": ""},
        color_discrete_sequence=[COLORS[0]],
    )
    chart(fig, height=max(380, 34 * len(branch) + 110))

st.subheader("Clientes y productos")
left, right = st.columns([1, 1.35], gap="large")
with left:
    seg = f.groupby("Segmento", as_index=False)["VentaNeta"].sum().sort_values("VentaNeta", ascending=False)
    fig = px.pie(
        seg, names="Segmento", values="VentaNeta", hole=0.55,
        title="Participación de ventas por segmento",
        color_discrete_sequence=COLORS,
    )
    fig.update_traces(textposition="inside", textinfo="percent")
    chart(fig, height=400)
with right:
    top = (
        f.groupby("ProductoDetalle", as_index=False)
        .agg(Unidades=("Cantidad", "sum"), Ventas=("VentaNeta", "sum"), Utilidad=("UtilidadCalculada", "sum"))
        .nlargest(10, "Unidades").sort_values("Unidades")
    )
    fig = px.bar(
        top, x="Unidades", y="ProductoDetalle", orientation="h",
        title="Los 10 productos más vendidos (unidades)",
        labels={"ProductoDetalle": "", "Unidades": "Unidades"},
        color_discrete_sequence=[COLORS[3]],
    )
    chart(fig, height=400)

with st.expander("📊 Ver detalle de ventas y descargar CSV"):
    detail = f[["VentaID", "Fecha", "Ciudad", "Sucursal", "ClienteID", "Segmento", "ProductoDetalle", "Cantidad", "VentaNeta", "CostoTotal", "UtilidadCalculada"]].copy()
    detail = detail.rename(columns={"UtilidadCalculada": "UtilidadBrutaRecalculada"})
    st.dataframe(detail, use_container_width=True, hide_index=True)
    st.download_button(
        "Descargar ventas filtradas (CSV)", detail.to_csv(index=False).encode("utf-8-sig"),
        file_name="ventas_filtradas_san_francisco_pizza.csv", mime="text/csv",
    )

with st.expander("🔎 Calidad y trazabilidad de datos"):
    st.write(f"Registros originales: **{len(ventas):,}**. Registros con filtros: **{len(f):,}**.")
    st.write(f"Ventas sin cliente relacionado: **{int((base['_cliente_match'] == 'left_only').sum()):,}**.")
    st.write(f"Ventas sin producto relacionado: **{int((base['_producto_match'] == 'left_only').sum()):,}**.")
    discrepancias = (ventas["UtilidadBruta"] - ventas["UtilidadCalculada"]).abs()
    st.write(f"Registros con diferencia de utilidad superior a USD 0,02: **{int((discrepancias > 0.02).sum()):,}**.")
    st.info("La utilidad es recalculada como ventas netas menos costo. Las transacciones se identifican mediante VentaID.")

st.subheader("🤖 Diagnóstico y recomendaciones comerciales")
st.caption("Se emplean únicamente los datos filtrados. Las recomendaciones son hipótesis para validar por el equipo.")
prod_stats = f.groupby("ProductoDetalle").agg(Ventas=("VentaNeta", "sum"), Unidades=("Cantidad", "sum"), Utilidad=("UtilidadCalculada", "sum")).sort_values("Ventas", ascending=False)
branch_stats = f.groupby("Sucursal").agg(Ventas=("VentaNeta", "sum"), Utilidad=("UtilidadCalculada", "sum")).sort_values("Ventas", ascending=False)
seg_stats = f.groupby("Segmento")["VentaNeta"].sum().sort_values(ascending=False)

if st.button("Generar diagnóstico automático", type="primary"):
    st.markdown("**Observaciones fundamentadas en los registros seleccionados:**")
    if not branch_stats.empty:
        best, lowest = branch_stats.iloc[0], branch_stats.iloc[-1]
        st.write(f"1. La sucursal con mayores ventas es **{branch_stats.index[0]}** ({usd(float(best['Ventas']))}); la de menores ventas es **{branch_stats.index[-1]}** ({usd(float(lowest['Ventas']))}). Comprobar diferencias de demanda y cobertura antes de extrapolar estrategias.")
    if not top.empty:
        winner = top.iloc[-1]
        st.write(f"2. El producto líder en unidades es **{winner['ProductoDetalle']}** ({winner['Unidades']:,.0f} unidades). Revisar inventario y su disponibilidad en cada sucursal.")
    if len(by_month) > 1:
        current, prior = by_month.iloc[-1], by_month.iloc[-2]
        st.write(f"3. Las ventas del último mes registrado fueron **{usd(float(current['Ventas']))}**, frente a **{usd(float(prior['Ventas']))}** del mes anterior. Verificar que ambos meses estén completos.")
    st.write(f"4. La utilidad bruta de las ventas filtradas asciende a **{usd(utilidad)}**. Revisar productos y sucursales con contribución baja o negativa antes de diseñar acciones comerciales.")
    st.warning("Antes de ejecutar decisiones, contrastar inventario, estacionalidad, costos, restricciones operativas y competencia.")

st.markdown("**Análisis adicional con IA (opcional)**")
api_key = st.text_input("Clave API de OpenAI (opcional, solo esta sesión)", type="password")
question = st.text_area("Consulta comercial", "¿Qué oportunidades comerciales muestran los datos y cómo priorizarlas?")
if st.button("Consultar IA"):
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        st.info("Introduce una clave API para usar esta función; el diagnóstico automático anterior funciona sin ella.")
    else:
        context = {
            "ventas_netas": round(ventas_total, 2), "utilidad_bruta": round(utilidad, 2),
            "ticket_promedio": round(ticket, 2), "clientes_unicos": clientes_unicos,
            "transacciones": transacciones, "unidades": round(unidades, 2),
            "productos": prod_stats.head(8).round(2).reset_index().to_dict("records"),
            "sucursales": branch_stats.head(15).round(2).reset_index().to_dict("records"),
            "segmentos": seg_stats.round(2).to_dict(),
            "ventas_mensuales": by_month.tail(18).round(2).assign(Mes=lambda d: d.Mes.dt.strftime("%Y-%m")).to_dict("records"),
        }
        try:
            from openai import OpenAI
            client = OpenAI(api_key=key)
            response = client.responses.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
                instructions=(
                    "Eres analista comercial. Contesta en español usando exclusivamente "
                    "las cifras agregadas recibidas; no inventes información. "
                    "No calcules ni muestres métricas porcentuales de rentabilidad. "
                    "Distingue hallazgos, acciones propuestas y supuestos."
                ),
                input=f"Datos: {json.dumps(context, ensure_ascii=False, default=str)}\nPregunta: {question}",
            )
            st.markdown(response.output_text)
            st.warning("Validar los cálculos y la viabilidad de cada recomendación antes de usarla.")
        except Exception as exc:
            st.error(f"No fue posible consultar el modelo: {exc}")
