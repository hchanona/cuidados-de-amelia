import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json

# Ajuste horario manual a CDMX
ahora = datetime.utcnow() - timedelta(hours=6)

# Conexión a Google Sheets
cred_json = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
cred_dict = json.loads(cred_json) if isinstance(cred_json, str) else dict(cred_json)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key("1LsuO8msQi9vXwNJq1L76fz_rTWJjtNLjecjaetdI8oY").sheet1

data = pd.DataFrame(sheet.get_all_records())
data.columns = data.columns.str.strip()

if not data.empty:
    data["hora"] = pd.to_datetime(data["hora"], errors="coerce").dt.strftime("%H:%M")
    data["fecha_hora"] = pd.to_datetime(data["fecha"] + " " + data["hora"], errors="coerce")
    data = data.dropna(subset=["fecha_hora"])
    data = data[data["fecha_hora"] <= ahora]

st.title("Registro de cuidados de Amelia")
st.image("foto_amor.jpg", use_container_width=True)
st.markdown("<div style='text-align: center'><em>Para cuidar un poco mejor a una hermosa bebé que ha luchado tanto </em></div>", unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #fff4f6;  /* Blush clarísimo */
        color: #555555;  /* Gris semi-oscuro elegante */
        font-family: 'Georgia', 'Palatino Linotype', 'Times New Roman', serif;
    }

    h1, h2, h3, h4, h5, h6 {
        color: #555555;
        font-family: 'Georgia', 'Palatino Linotype', 'Times New Roman', serif;
    }

    .stMetricLabel, .stMetricValue {
        color: #555555 !important;
        font-family: 'Georgia', 'Palatino Linotype', 'Times New Roman', serif;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# === FORMULARIO DE REGISTRO ===

# === REGISTRO DE EVENTO ===

st.header("Evento")

fecha = ahora.date()
hora = ahora.time()

st.info(f"El registro se guardará automáticamente con la fecha {fecha} y la hora actual {hora.strftime('%H:%M')}.")


tipo = st.radio("Tipo de evento", [
    "colocación de bolsa", "extracción de leche", "evacuación", "puenteo", "toma de leche", "seno materno", "vaciado"
])

# Inicializamos valores
cantidad_leche_ml = 0.0
tipo_leche = ""
cantidad_popo_puenteada = 0
cantidad_extraida_ml = 0
duracion_seno_materno = 0

# Campos condicionales reactivos
if tipo == "toma de leche":
    cantidad_leche_oz = st.number_input("Cantidad de leche (oz)", min_value=0.0, step=0.1)
    cantidad_leche_ml = (cantidad_leche_oz * 29.5735)
    tipo_leche = st.selectbox("Tipo de leche", ["materna", "Nutramigen", "Puramino"])

elif tipo == "puenteo":
    cantidad_popo_puenteada = st.number_input("Cantidad de popó puenteada (ml)", min_value=0, step=1)

elif tipo == "extracción de leche":
    cantidad_extraida_ml = st.number_input("Cantidad extraída de leche (ml)", min_value=0, step=1)

elif tipo == "seno materno":
    duracion_seno_materno = st.number_input("Duración de seno materno (minutos)", min_value=0, step=1)

# Botón de guardar (fuera de formulario)
if st.button("Guardar"):
    fecha_hora_reg = datetime.combine(fecha, hora)
    if fecha_hora_reg > ahora:
        st.error("La fecha y hora no pueden estar en el futuro.")
    else:
        fila = [
            str(fecha),
            str(hora),
            tipo,
            cantidad_leche_ml,
            tipo_leche,
            cantidad_popo_puenteada,
            "sí" if tipo == "evacuación" else "no",
            cantidad_extraida_ml,
            duracion_seno_materno if tipo == "seno materno" else ""
        ]
        sheet.append_row(fila)
        st.success("Registro guardado con éxito.")

# === Procesamiento de datos ===

hoy = ahora.date()
data["fecha"] = pd.to_datetime(data["fecha"], errors="coerce").dt.date
datos_hoy = data[data["fecha"] == hoy]

if "duracion_seno_materno" not in datos_hoy.columns:
    datos_hoy["duracion_seno_materno"] = pd.NA

# Limpieza y conversión
data["cantidad_leche_ml"] = data["cantidad_leche_ml"].astype(str).str.replace(",", ".")
data["cantidad_popo_puenteada"] = data["cantidad_popo_puenteada"].astype(str).str.replace(",", ".")
data["cantidad_extraida_de_leche"] = data["cantidad_extraida_de_leche"].astype(str).str.replace(",", ".")

data["cantidad_leche_ml"] = pd.to_numeric(data["cantidad_leche_ml"], errors="coerce")
data["cantidad_popo_puenteada"] = pd.to_numeric(data["cantidad_popo_puenteada"], errors="coerce")
data["cantidad_extraida_de_leche"] = pd.to_numeric(data["cantidad_extraida_de_leche"], errors="coerce")

# Protección para duracion_seno_materno
if "duracion_seno_materno" not in data.columns:
    data["duracion_seno_materno"] = pd.NA

data["duracion_seno_materno"] = pd.to_numeric(data["duracion_seno_materno"], errors="coerce")

# === Última toma de leche (incluye seno materno) ===

leche_historica = data[data["tipo"].isin(["toma de leche", "seno materno"])]

if not leche_historica.empty:
    ultima_toma_historica = leche_historica.sort_values("fecha_hora", ascending=False).iloc[0]
    minutos_desde_ultima_toma = (ahora - ultima_toma_historica["fecha_hora"]).total_seconds() / 60
    if minutos_desde_ultima_toma >= 0:
        h_ultima_toma = int(minutos_desde_ultima_toma // 60)
        m_ultima_toma = int(minutos_desde_ultima_toma % 60)
        texto_ultima_toma = f"{h_ultima_toma} h {m_ultima_toma} min"
    else:
        texto_ultima_toma = "⚠️ Registro futuro"
else:
    texto_ultima_toma = "No registrada"

# === Leche hoy (solo tipo "toma de leche") ===

leche = datos_hoy[datos_hoy["tipo"] == "toma de leche"]
leche["cantidad_leche_ml"] = pd.to_numeric(leche["cantidad_leche_ml"], errors="coerce")
leche["tipo_leche"] = leche["tipo_leche"].astype(str).str.strip().str.lower()
leche = leche[leche["tipo_leche"].isin(["materna", "nutramigen", "puramino"])]

ml_24h = leche["cantidad_leche_ml"].sum()
ml_materna = leche[leche["tipo_leche"] == "materna"]["cantidad_leche_ml"].sum()
porcentaje_materna = (ml_materna / ml_24h * 100) if ml_24h > 0 else 0


# Seno hoy
seno_hoy = datos_hoy[datos_hoy["tipo"] == "seno materno"]

duracion_total_seno_hoy = seno_hoy["duracion_seno_materno"].sum()

# Último seno materno
if not seno_hoy.empty:
    ultima_seno = seno_hoy.sort_values("fecha_hora", ascending=False).iloc[0]
    minutos_desde_ultimo_seno = (ahora - ultima_seno["fecha_hora"]).total_seconds() / 60
    if minutos_desde_ultimo_seno >= 0:
        h_ultimo_seno = int(minutos_desde_ultimo_seno // 60)
        m_ultimo_seno = int(minutos_desde_ultimo_seno % 60)
        texto_ultimo_seno = f"{h_ultimo_seno} h {m_ultimo_seno} min"
    else:
        texto_ultimo_seno = "Registro futuro"
else:
    texto_ultimo_seno = "No registrado hoy"

# Calorías
def calcular_calorias(row):
    if row["tipo_leche"] == "materna":
        return row["cantidad_leche_ml"] * 0.67
    elif row["tipo_leche"] == "puramino":
        return row["cantidad_leche_ml"] * 0.72
    elif row["tipo_leche"] == "nutramigen":
        return row["cantidad_leche_ml"] * 0.67
    return 0

leche["calorias"] = leche.apply(calcular_calorias, axis=1)
calorias_24h = leche["calorias"].sum()

# Consumo acumulado de leche hoy
leche_diaria = leche.dropna(subset=["fecha_hora", "cantidad_leche_ml"]).sort_values("fecha_hora")
leche_diaria["hora"] = leche_diaria["fecha_hora"].dt.strftime("%H:%M")
leche_diaria["acumulado"] = leche_diaria["cantidad_leche_ml"].cumsum()

# Promedio histórico
tomas_pasadas = data[
    (data["tipo"] == "toma de leche") &
    (data["tipo_leche"].isin(["materna", "puramino"])) &
    (data["fecha"] < hoy)
]
tomas_pasadas["cantidad_leche_ml"] = pd.to_numeric(tomas_pasadas["cantidad_leche_ml"], errors="coerce")
promedio_historico = tomas_pasadas.groupby("fecha")["cantidad_leche_ml"].sum().mean()

# Otros eventos
puenteos = datos_hoy[datos_hoy["tipo"] == "puenteo"]
puenteos["cantidad_popo_puenteada"] = pd.to_numeric(puenteos["cantidad_popo_puenteada"], errors="coerce")
puenteo_total = puenteos["cantidad_popo_puenteada"].sum()

evacs = datos_hoy[(datos_hoy["tipo"] == "evacuación") & (datos_hoy["hubo_evacuación"] == "sí")]
n_evacuaciones = len(evacs)

extracciones = datos_hoy[datos_hoy["tipo"] == "extracción de leche"]
ultima_extraccion = extracciones["fecha_hora"].max()
tiempo_desde_extraccion = ahora - ultima_extraccion if pd.notna(ultima_extraccion) else None
extracciones["cantidad_extraida_de_leche"] = pd.to_numeric(extracciones["cantidad_extraida_de_leche"], errors="coerce")
ml_extraido = extracciones["cantidad_extraida_de_leche"].sum()


vaciados = data[(data["tipo"] == "vaciado") & (data["fecha_hora"] <= ahora)]
ultimo_vaciado = vaciados["fecha_hora"].max()
min_desde_vaciado = (ahora - ultimo_vaciado).total_seconds() // 60 if pd.notna(ultimo_vaciado) else None

cambios = data[(data["tipo"] == "colocación de bolsa") & (data["fecha_hora"] <= ahora)]
ultima_colocacion = cambios["fecha_hora"].max()
tiempo_desde_cambio = ahora - ultima_colocacion if pd.notna(ultima_colocacion) else None

# === Estadísticas finales ===

# === Indicadores de alimentación ===

st.subheader("Indicadores de alimentación del día")

st.metric("Tiempo desde última toma de leche, incluyendo seno", texto_ultima_toma)

if tiempo_desde_extraccion is not None:
    h = int(tiempo_desde_extraccion.total_seconds() // 3600)
    m = int(tiempo_desde_extraccion.total_seconds() % 3600 // 60)
    st.metric("Tiempo desde última extracción", f"{h} h {m} min")
else:
    st.info("Hoy no se ha extraído leche")

st.metric("Leche consumida", f"{ml_24h:.0f} ml")
st.metric("Leche extraída", f"{ml_extraido:.0f} ml")
st.metric("Calorías consumidas", f"{calorias_24h:.0f} kcal")
st.metric("Porcentaje de leche materna", f"{porcentaje_materna:.0f}%")
st.metric("Duración de seno materno", f"{duracion_total_seno_hoy:.0f} min")

# === Indicadores de digestión y manejo de bolsa ===

st.subheader("Indicadores de digestión del día")

st.metric("Número de puenteos", f"{len(puenteos)} veces")
st.metric("Volumen puenteado", f"{puenteo_total:.0f} ml")
st.metric("Número de evacuaciones", f"{n_evacuaciones} veces")

if min_desde_vaciado is not None and min_desde_vaciado >= 0:
    horas = int(min_desde_vaciado // 60)
    minutos = int(min_desde_vaciado % 60)
    st.metric("Tiempo desde último vaciamiento", f"{horas} h {minutos} min")
elif min_desde_vaciado is not None:
    st.warning("No puede registrarse un vaciamiento en el futuro.")

if tiempo_desde_cambio is not None:
    h = int(tiempo_desde_cambio.total_seconds() // 3600)
    m = int(tiempo_desde_cambio.total_seconds() % 3600 // 60)
    st.metric("Tiempo desde último cambio de bolsa", f"{h} h {m} min")


# === Gráfico: Tendencia de consumo de calorías ===

# Normalizamos primero los campos relevantes
data["tipo_leche"] = data["tipo_leche"].astype(str).str.strip().str.lower()
data["fecha"] = pd.to_datetime(data["fecha"], errors="coerce").dt.date
data["cantidad_leche_ml"] = pd.to_numeric(data["cantidad_leche_ml"], errors="coerce")

# Seleccionamos solo las tomas válidas
historico_leche = data[
    (data["tipo"] == "toma de leche") &
    (data["tipo_leche"].isin(["materna", "nutramigen", "puramino"]))
].copy()

# Cálculo de calorías
historico_leche["calorias"] = historico_leche.apply(lambda row: 
    row["cantidad_leche_ml"] * (0.67 if row["tipo_leche"] == "materna" else 0.72), axis=1)

# Agrupamos por fecha
calorias_por_dia = historico_leche.groupby("fecha")["calorias"].sum().sort_index()

# Calculamos media móvil de 10 días (puedes ajustar el window si quieres)
media_movil = calorias_por_dia.rolling(window=7, min_periods=7).mean()

# Gráfico
st.subheader("Calorías diarias: media móvil de 7 días (kcal)")

if not media_movil.empty:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    
    fig, ax = plt.subplots(figsize=(12,6))
    fig.patch.set_facecolor('#fff8f8')
    ax.set_facecolor('#fff8f8')
    ax.plot(media_movil.index, media_movil.values, linestyle='-', linewidth=2, color='#c8a2c8')
    ax.set_ylim(0, media_movil.max() * 1.10)
    
    # Formato de fechas en X
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    fig.autofmt_xdate(rotation=30)
    
    st.pyplot(fig)

# === Gráfico: Media móvil de 14 días de extracción de leche ===

st.subheader("Extracción de leche: media móvil de 7 días (ml)")

# Filtramos las extracciones válidas
historico_extraccion = data[data["tipo"] == "extracción de leche"].copy()
historico_extraccion["cantidad_extraida_de_leche"] = pd.to_numeric(historico_extraccion["cantidad_extraida_de_leche"], errors="coerce")

# Agrupamos por día
extraccion_por_dia = historico_extraccion.groupby("fecha")["cantidad_extraida_de_leche"].sum().sort_index()

# Media móvil de 7 días
extraccion_media_movil = extraccion_por_dia.rolling(window=7, min_periods=7).mean()

# Gráfico
if not extraccion_media_movil.empty:
    fig2, ax2 = plt.subplots(figsize=(12,6))
    fig2.patch.set_facecolor('#fff8f8')
    ax2.set_facecolor('#fff8f8')
    ax2.plot(extraccion_media_movil.index, extraccion_media_movil.values, linestyle='-', linewidth=2, color='#f4c2c2')
    ax2.set_ylim(0, 220)
    ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    fig2.autofmt_xdate(rotation=30)
    st.pyplot(fig2)
else:
    st.info("No hay registros de extracción de leche.")

# === Gráfico: Media móvil de 7 días del porcentaje de leche materna ===

st.subheader("Porcentaje de leche materna: media móvil de 7 días")

# Filtramos tomas válidas
historico_tomas = data[data["tipo"] == "toma de leche"].copy()
historico_tomas["cantidad_leche_ml"] = pd.to_numeric(historico_tomas["cantidad_leche_ml"], errors="coerce")
historico_tomas["tipo_leche"] = historico_tomas["tipo_leche"].astype(str).str.strip().str.lower()

# Creamos función para calcular % materna por día
def calcular_porcentaje_materna(grupo):
    total = grupo["cantidad_leche_ml"].sum()
    materna = grupo[grupo["tipo_leche"] == "materna"]["cantidad_leche_ml"].sum()
    return (materna / total * 100) if total > 0 else 0

# Agrupamos por fecha
porcentaje_materna_por_dia = historico_tomas.groupby("fecha").apply(calcular_porcentaje_materna).sort_index()

# Media móvil de 7 días
porcentaje_materna_media_movil = porcentaje_materna_por_dia.rolling(window=7, min_periods=7).mean()

# Gráfico
if not porcentaje_materna_media_movil.empty:
    fig3, ax3 = plt.subplots(figsize=(12,6))
    fig3.patch.set_facecolor('#fff8f8')
    ax3.set_facecolor('#fff8f8')
    ax3.plot(porcentaje_materna_media_movil.index, porcentaje_materna_media_movil.values, linestyle='-', linewidth=2, color='#e3a6b4')
    ax3.set_ylim(0, 100)
    ax3.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    fig3.autofmt_xdate(rotation=30)
    st.pyplot(fig3)
else:
    st.info("No hay registros de tomas de leche.")
