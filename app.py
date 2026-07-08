# -*- coding: utf-8 -*-
"""
Mr. Beast Burger — Dashboard de Delivery
Fuente: Google Sheets | Deploy: Streamlit Cloud + GitHub
"""
from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

LOGO = Path(__file__).parent / "assets" / "logo.png"

st.set_page_config(page_title="Mr. Beast Burger — Dashboard", page_icon="🍔", layout="wide")

PRIMARY, SECONDARY, TERTIARY = "#00BFFF", "#FF007F", "#FFFFFF"
NEUTRAL, CARD_BG, MUTED = "#121212", "#1E1E1E", "#9AA4AC"
HORA_APERTURA, HORA_CIERRE = 12, 23
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Anybody:wght@600;800&family=Be+Vietnam+Pro:wght@300;400;600&display=swap');
html, body, [class*="css"] {{ font-family: 'Be Vietnam Pro', sans-serif; }}
h1, h2, h3 {{ font-family: 'Anybody', sans-serif !important; letter-spacing: .5px; }}
.stApp {{ background-color: {NEUTRAL}; }}
.kpi-card {{ background: {CARD_BG}; border-radius: 14px; padding: 18px 20px;
    border: 1px solid #2a2a2a; height: 100%; }}
.kpi-label {{ color: {MUTED}; font-size: .78rem; text-transform: uppercase; letter-spacing: 1px; }}
.kpi-value {{ font-family: 'Anybody', sans-serif; font-size: 1.9rem; font-weight: 800; color: {TERTIARY}; }}
.kpi-sub {{ font-size: .8rem; color: {MUTED}; }}
.legend-chip {{ display: inline-block; padding: 3px 14px; border-radius: 20px;
    font-size: .75rem; font-weight: 600; margin-right: 8px; color: #121212; }}
</style>
""", unsafe_allow_html=True)

# ----------------------------- DATOS -----------------------------------------
COLMAP = {
    "Nombre del restaurante": "restaurante",
    "Fecha de entrega (creada para pedidos cancelados)": "fecha_entrega",
    "Número de pedido": "pedido",
    "Monto": "monto",
    "Descuento": "descuento",
    "Método de pago": "metodo_pago",
    "Estado": "estado",
    "Se pagará": "se_pagara",
    "Tiempo de preparación del pedido (min)": "prep_min",
    "Hora de creación del pedido": "creado",
    "Pedido confirmado por el restaurante": "confirmado",
    "El pedido está listo": "listo",
    "Pedido recogido por mensajero": "recogido",
}

SUCURSALES = {
    "Equipetrol": "Mr. Beast Burger Equipetrol",
    "Centro": "Mr. Beast Burger Centro",
    "Norte": "Mr. Beast Burger Norte",
}


def df_map(frame, func):
    """Compatibilidad pandas 2/3: DataFrame.map reemplazó a applymap."""
    try:
        return frame.map(func)
    except AttributeError:
        return frame.applymap(func)


def transform(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns={k: v for k, v in COLMAP.items() if k in raw.columns}).copy()
    df["creado"] = pd.to_datetime(df["creado"], errors="coerce")
    df = df.dropna(subset=["creado"])
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)
    df["prep_min"] = pd.to_numeric(df.get("prep_min"), errors="coerce")
    for c in ["fecha_entrega", "confirmado", "listo", "recogido"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    df["fecha"] = df["creado"].dt.date
    df["hora"] = df["creado"].dt.hour
    df["dow"] = df["creado"].dt.dayofweek
    df["dia"] = df["dow"].map(dict(enumerate(DIAS)))
    suc = df["restaurante"].astype(str).str.extract(r"-\s*(\w+)")[0].str.capitalize()
    df["sucursal"] = suc.map(SUCURSALES).fillna("Otra")
    df["finalizado"] = df["estado"].astype(str).str.strip().eq("Finalizado")
    # Tiempos de la cadena (solo válidos en finalizados)
    df["t_conf"] = (df["confirmado"] - df["creado"]).dt.total_seconds() / 60
    df["t_espera"] = (df["recogido"] - df["listo"]).dt.total_seconds() / 60
    df["t_viaje"] = (df["fecha_entrega"] - df["recogido"]).dt.total_seconds() / 60
    df["t_total"] = (df["fecha_entrega"] - df["creado"]).dt.total_seconds() / 60
    return df


@st.cache_data(ttl=300, show_spinner="Cargando datos desde Google Sheets...")
def load_data() -> pd.DataFrame:
    """Lee la base desde Google Sheets (endpoint gviz, funciona con hojas
    compartidas como 'cualquiera con el enlace')."""
    cfg = st.secrets["connections"]["gsheets"]
    sheet_id = cfg["spreadsheet"].split("/d/")[1].split("/")[0]
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
    gid = str(cfg.get("worksheet", "")).strip()
    if gid and gid != "0":
        csv_url += f"&gid={gid}"
    raw = pd.read_csv(csv_url)
    return transform(raw)


gs_error = None
try:
    data = load_data()
except Exception as e:
    gs_error = e
    data = pd.DataFrame()

if data.empty:
    st.warning("No se pudo leer Google Sheets. Verifica los *secrets* o sube el reporte manualmente:")
    if gs_error is not None:
        with st.expander("🔍 Ver detalle del error de conexión"):
            st.exception(gs_error)
    up = st.file_uploader("Reporte de delivery (.xlsx o .csv)", type=["xlsx", "csv"])
    if up is None:
        st.stop()
    raw = pd.read_csv(up) if up.name.endswith(".csv") else pd.read_excel(up)
    data = transform(raw)

# ----------------------------- FILTROS ---------------------------------------
if LOGO.exists():
    st.sidebar.image(str(LOGO), use_container_width=True)
else:
    st.sidebar.markdown(f"<h2 style='color:{PRIMARY}'>🍔 MR. BEAST BURGER</h2>", unsafe_allow_html=True)
st.sidebar.caption("Filtros del dashboard")

fmin, fmax = data["fecha"].min(), data["fecha"].max()
rango = st.sidebar.date_input("Rango de fechas", value=(fmin, fmax), min_value=fmin, max_value=fmax)
if isinstance(rango, tuple) and len(rango) == 2:
    f_ini, f_fin = rango
else:
    f_ini = f_fin = rango[0] if isinstance(rango, tuple) else rango

sucursales_sel = st.sidebar.multiselect(
    "Sucursal", options=list(SUCURSALES.values()), default=list(SUCURSALES.values()))

banda = st.sidebar.slider("Banda 'cerca de la media' (± %)", 5, 40, 20, step=5,
                          help="Qué tan cerca del ticket promedio se considera 'en la media'.")

df = data[(data["fecha"] >= f_ini) & (data["fecha"] <= f_fin) & (data["sucursal"].isin(sucursales_sel))]
fin = df[df["finalizado"]]
canc = df[~df["finalizado"]]

if LOGO.exists():
    h1, h2 = st.columns([1, 5])
    h1.image(str(LOGO), width=170)
    h2.markdown("# DASHBOARD DELIVERY")
else:
    st.markdown("# DASHBOARD DELIVERY")
st.caption(f"Período: **{f_ini} → {f_fin}** · Sucursales: {', '.join(s.split()[-1] for s in sucursales_sel) or '—'}")

if df.empty or fin.empty:
    st.info("No hay datos para los filtros seleccionados.")
    st.stop()

# ----------------------------- KPI CARDS -------------------------------------
n_dias = max(fin["fecha"].nunique(), 1)
ticket_prom = fin["monto"].mean()


def kpi(container, label, value, sub, accent=PRIMARY):
    container.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value" style="color:{accent}">{value}</div>
      <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)


def fig_layout(fig, height=300):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": TERTIARY, "family": "Be Vietnam Pro"}, height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(gridcolor="#2a2a2a"), yaxis=dict(gridcolor="#2a2a2a"),
    )
    return fig


c1, c2, c3, c4, c5 = st.columns(5)
kpi(c1, "Venta total", f"Bs {fin['monto'].sum():,.0f}", f"Bs {fin['monto'].sum()/n_dias:,.0f} por día")
kpi(c2, "Transacciones", f"{len(fin):,}", f"{len(fin)/n_dias:,.0f} pedidos por día")
kpi(c3, "Ticket promedio", f"Bs {ticket_prom:,.1f}", f"Mediana: Bs {fin['monto'].median():,.0f}")
kpi(c4, "Cancelaciones", f"{len(canc):,}", f"{len(canc)/max(len(df),1)*100:.1f}% de los pedidos", accent=SECONDARY)
kpi(c5, "Monto cancelado", f"Bs {canc['monto'].sum():,.0f}", "Venta no concretada", accent=SECONDARY)

st.caption("💡 El 100% de la venta se recibe **en línea**. «Pago en efectivo» = el cliente paga al repartidor; "
           "el rider no entrega efectivo ni transferencias al negocio.")
st.divider()

# ----------------------------- HEATMAP ---------------------------------------
st.markdown("## 🔥 Heatmap de demanda por hora (12:00 – 23:00)")

horas = list(range(HORA_APERTURA, HORA_CIERRE + 1))
dias_activos = fin.groupby("dow")["fecha"].nunique()

ped = fin.pivot_table(index="dow", columns="hora", values="pedido", aggfunc="count").reindex(
    index=range(7), columns=horas).fillna(0)
ven = fin.pivot_table(index="dow", columns="hora", values="monto", aggfunc="sum").reindex(
    index=range(7), columns=horas).fillna(0)
den = dias_activos.reindex(range(7))
ped_avg = ped.div(den, axis=0)
ven_avg = ven.div(den, axis=0)

vals = ped_avg.stack().dropna()
vals = vals[vals > 0]
if len(vals) >= 3:
    t1, t2 = vals.quantile(1 / 3), vals.quantile(2 / 3)
else:
    t1 = t2 = vals.max() if len(vals) else 0


def clasificar(x):
    if pd.isna(x) or x == 0:
        return np.nan
    if x <= t1:
        return 0
    if x <= t2:
        return 1
    return 2


z = df_map(ped_avg, clasificar)
con_datos = [i for i in range(7) if pd.notna(den.iloc[i]) and ped.iloc[i].sum() > 0]
z = z.iloc[con_datos]
ped_avg_v, ven_avg_v = ped_avg.iloc[con_datos], ven_avg.iloc[con_datos]
etiquetas_y = [DIAS[i] for i in con_datos]

text = [[("" if pd.isna(ped_avg_v.iat[r, c]) or ped_avg_v.iat[r, c] == 0 else
          f"{ped_avg_v.iat[r, c]:.0f} ped<br>Bs {ven_avg_v.iat[r, c]:,.0f}")
         for c in range(len(horas))] for r in range(len(etiquetas_y))]

COLORS = {"Bajo": "#123B4F", "Medio": "#0083B8", "Rush": PRIMARY}
colorscale = [[0.0, COLORS["Bajo"]], [0.33, COLORS["Bajo"]],
              [0.34, COLORS["Medio"]], [0.66, COLORS["Medio"]],
              [0.67, COLORS["Rush"]], [1.0, COLORS["Rush"]]]

fig = go.Figure(go.Heatmap(
    z=z.values, x=[f"{h}:00" for h in horas], y=etiquetas_y,
    text=text, texttemplate="%{text}", textfont={"size": 11},
    colorscale=colorscale, zmin=0, zmax=2, xgap=4, ygap=4, showscale=False,
    hovertemplate="<b>%{y} %{x}</b><br>%{text}<extra></extra>"))
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font={"color": TERTIARY, "family": "Be Vietnam Pro"},
    height=110 + 62 * max(len(etiquetas_y), 1),
    margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(autorange="reversed"))
st.plotly_chart(fig, use_container_width=True)

st.markdown(f"""
<span class="legend-chip" style="background:{COLORS['Bajo']};color:#fff">BAJO ≤ {t1:.0f} ped/h</span>
<span class="legend-chip" style="background:{COLORS['Medio']};color:#fff">MEDIO ≤ {t2:.0f} ped/h</span>
<span class="legend-chip" style="background:{COLORS['Rush']}">RUSH &gt; {t2:.0f} ped/h</span>
<span style="color:{MUTED};font-size:.78rem"> · Cada celda: pedidos promedio y venta promedio por día en esa hora.</span>
""", unsafe_allow_html=True)
st.divider()

# ----------------------------- TIEMPOS DE OPERACIÓN --------------------------
st.markdown("## ⏱️ Tiempos de operación (pedidos finalizados)")

metricas_t = [("Confirmación", "t_conf"), ("Preparación", "prep_min"),
              ("Espera del rider", "t_espera"), ("Viaje al cliente", "t_viaje"),
              ("Total al cliente", "t_total")]
cols_t = st.columns(5)
for col, (lbl, c) in zip(cols_t, metricas_t):
    s = fin[c].dropna()
    if len(s):
        kpi(col, lbl, f"{s.mean():.0f} min", f"Mediana {s.median():.0f} · p90 {s.quantile(.9):.0f} min")
    else:
        kpi(col, lbl, "—", "sin datos")

t_tot = fin["t_total"].dropna()
if len(t_tot):
    tarde = (t_tot > 60).mean() * 100
    color_t = SECONDARY if tarde > 15 else PRIMARY
    st.markdown(f"<p style='color:{color_t};font-weight:600'>⚠️ {tarde:.1f}% de los pedidos "
                f"tardan más de 60 min en llegar al cliente.</p>", unsafe_allow_html=True)

ca, cb = st.columns([1.4, 1])
with ca:
    por_hora = fin.groupby("hora").agg(Pedidos=("pedido", "count"), Prep=("prep_min", "mean")).reindex(horas)
    figh = make_subplots(specs=[[{"secondary_y": True}]])
    figh.add_bar(x=[f"{h}:00" for h in horas], y=por_hora["Pedidos"], name="Pedidos",
                 marker_color=PRIMARY, opacity=.75)
    figh.add_scatter(x=[f"{h}:00" for h in horas], y=por_hora["Prep"], name="Prep. promedio (min)",
                     mode="lines+markers", line=dict(color=SECONDARY, width=3), secondary_y=True)
    fig_layout(figh, 320)
    figh.update_layout(title="Pedidos vs. tiempo de preparación por hora",
                       legend=dict(orientation="h", y=1.15))
    figh.update_yaxes(title_text="Pedidos", secondary_y=False, gridcolor="#2a2a2a")
    figh.update_yaxes(title_text="Prep (min)", secondary_y=True, showgrid=False)
    st.plotly_chart(figh, use_container_width=True)
    st.caption("Si la línea rosa sube en el rush, el cuello de botella es cocina, no delivery.")
with cb:
    tt = fin.groupby("sucursal")[["t_conf", "prep_min", "t_espera", "t_viaje", "t_total"]].mean().round(1)
    tt.columns = ["Confirm.", "Prep.", "Espera rider", "Viaje", "Total"]
    st.markdown("**Minutos promedio por sucursal**")
    st.dataframe(tt, use_container_width=True)
st.divider()

# ----------------------------- TICKET vs MEDIA -------------------------------
st.markdown("## 🎯 Transacciones vs. ticket promedio")

lo, hi = ticket_prom * (1 - banda / 100), ticket_prom * (1 + banda / 100)
en_media = fin[(fin["monto"] >= lo) & (fin["monto"] <= hi)]
arriba = fin[fin["monto"] >= ticket_prom]
abajo_fuera = fin[fin["monto"] < lo]
arriba_fuera = fin[fin["monto"] > hi]

a, b = st.columns([1, 1.4])
with a:
    kpi(st, f"Cerca / dentro de la media (±{banda}%)", f"{len(en_media):,}",
        f"{len(en_media)/len(fin)*100:.1f}% · Bs {lo:,.0f} – Bs {hi:,.0f}")
    st.write("")
    kpi(st, "En el ticket promedio o más (≥ media)", f"{len(arriba):,}",
        f"{len(arriba)/len(fin)*100:.1f}% · desde Bs {ticket_prom:,.1f}", accent=SECONDARY)
with b:
    seg = pd.Series({
        f"Bajo la media (< Bs {lo:,.0f})": len(abajo_fuera),
        f"En la media (±{banda}%)": len(en_media),
        f"Sobre la media (> Bs {hi:,.0f})": len(arriba_fuera)})
    figt = go.Figure(go.Bar(
        x=seg.values, y=seg.index, orientation="h",
        marker_color=["#5A6570", PRIMARY, SECONDARY],
        text=[f"{v:,} ({v/len(fin)*100:.0f}%)" for v in seg.values], textposition="outside"))
    fig_layout(figt, 260)
    figt.update_layout(xaxis=dict(showgrid=False, visible=False), margin=dict(r=80))
    st.plotly_chart(figt, use_container_width=True)

bins = [0, 50, 80, 110, 150, 200, float("inf")]
labels = ["0–50", "51–80", "81–110", "111–150", "151–200", "200+"]
dist = pd.cut(fin["monto"], bins=bins, labels=labels).value_counts().reindex(labels)
figd2 = go.Figure(go.Bar(x=labels, y=dist.values, marker_color=PRIMARY,
                         text=dist.values, textposition="outside"))
fig_layout(figd2, 280)
figd2.update_layout(title="Distribución del ticket (Bs)")
st.plotly_chart(figd2, use_container_width=True)
st.divider()

# ----------------------------- CANCELACIONES ---------------------------------
st.markdown("## 🚫 Cancelaciones")
if len(canc):
    k1, k2, k3, k4 = st.columns(4)
    kpi(k1, "Pedidos cancelados", f"{len(canc):,}",
        f"{len(canc)/max(len(df),1)*100:.1f}% del total", accent=SECONDARY)
    kpi(k2, "Monto no concretado", f"Bs {canc['monto'].sum():,.0f}",
        f"Ticket prom.: Bs {canc['monto'].mean():,.0f}", accent=SECONDARY)
    sin_prep = ((canc["prep_min"].fillna(0) == 0)).sum()
    kpi(k3, "Cancelados sin preparar", f"{sin_prep:,}",
        "prep = 0 min (cancelación temprana)", accent=SECONDARY)
    efec = (canc["metodo_pago"].astype(str).str.strip().eq("Pago en efectivo")).mean() * 100
    kpi(k4, "Con pago en efectivo", f"{efec:.0f}%",
        "el efectivo cancela más que el pago online", accent=SECONDARY)
    st.write("")
    g1, g2 = st.columns(2)
    with g1:
        ch = canc.groupby("hora")["pedido"].count().reindex(horas).fillna(0)
        figc = go.Figure(go.Bar(x=[f"{h}:00" for h in horas], y=ch.values, marker_color=SECONDARY))
        fig_layout(figc, 280)
        figc.update_layout(title="Cancelaciones por hora")
        st.plotly_chart(figc, use_container_width=True)
    with g2:
        cs = canc.groupby("sucursal").agg(Cancelados=("pedido", "count"), Monto=("monto", "sum"))
        tot = df.groupby("sucursal")["pedido"].count()
        cs["Tasa %"] = (cs["Cancelados"] / tot * 100).round(1)
        st.markdown("**Por sucursal**")
        st.dataframe(cs.style.format({"Monto": "Bs {:,.0f}", "Tasa %": "{:.1f}%"}),
                     use_container_width=True)
        st.caption("Si el pico de cancelaciones coincide con el rush del heatmap, "
                   "la causa probable es saturación de cocina.")
else:
    st.info("Sin cancelaciones en el período seleccionado. 🎉")
st.divider()

# ----------------------------- DETALLE ---------------------------------------
col_l, col_r = st.columns(2)
with col_l:
    st.markdown("### 🏪 Por sucursal")
    tabla = fin.groupby("sucursal").agg(
        Pedidos=("pedido", "count"), Venta=("monto", "sum"), Ticket=("monto", "mean")).round(1)
    tabla["Cancelados"] = canc.groupby("sucursal")["pedido"].count()
    tabla = tabla.fillna(0).sort_values("Venta", ascending=False)
    st.dataframe(tabla.style.format({"Venta": "Bs {:,.0f}", "Ticket": "Bs {:,.1f}",
                                     "Cancelados": "{:,.0f}"}), use_container_width=True)
with col_r:
    st.markdown("### 💳 Método de pago del cliente")
    pago = fin.groupby("metodo_pago").agg(Pedidos=("pedido", "count"), Venta=("monto", "sum"),
                                          Ticket=("monto", "mean")).round(1)
    st.dataframe(pago.style.format({"Venta": "Bs {:,.0f}", "Ticket": "Bs {:,.1f}"}),
                 use_container_width=True)
    st.caption("«Pago en efectivo» = pago del cliente al repartidor. El negocio recibe todo en línea.")

st.markdown("### 📈 Venta por día")
por_dia = fin.groupby("fecha").agg(Venta=("monto", "sum"), Pedidos=("pedido", "count")).reset_index()
figd = go.Figure(go.Bar(x=por_dia["fecha"], y=por_dia["Venta"], marker_color=PRIMARY,
                        customdata=por_dia["Pedidos"],
                        hovertemplate="%{x}<br>Bs %{y:,.0f} · %{customdata} pedidos<extra></extra>"))
fig_layout(figd, 300)
st.plotly_chart(figd, use_container_width=True)
