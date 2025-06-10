# 1. === IMPORTACIÓN DE MÓDULOS ===

import matplotlib.dates as mdates # Para manejar fechas
import matplotlib.pyplot as plt # Para graficar
import gspread # Para conectar con las hojas de cálculo de Google Sheets
import json # Para manejar datos en formato JSON. En particular, leer credenciales
import pandas as pd # Para manipular datos, en particular DataFrames
import random # Para generar selecciones aleatorias. En particular, desplegar fotos al azar
import streamlit as st # Para la interfaz web

from datetime import datetime, timedelta # Para manejar fechas y horas
from oauth2client.service_account import ServiceAccountCredentials # Para la autenticación con Google Sheets


# 2. === DEFINICIÓN DE FUNCIONES ===

def calcular_calorias(row):
    """Devuelve las calorías correspondientes a la cantidad y tipo de leche de una fila."""
    if row["tipo_leche"] == "materna":
        return row["cantidad_leche_ml"] * 0.67
    elif row["tipo_leche"] == "puramino":
        return row["cantidad_leche_ml"] * 0.72
    elif row["tipo_leche"] == "nutramigen":
        return row["cantidad_leche_ml"] * 0.67
    return 0

def calcular_porcentaje_materna(grupo):
    """Devuelve el porcentaje de leche materna en un grupo diario de tomas."""
    total = grupo["cantidad_leche_ml"].sum()
    materna = grupo[grupo["tipo_leche"] == "materna"]["cantidad_leche_ml"].sum()
    return (materna / total * 100) if total > 0 else 0

def graficar_media_movil(serie, titulo, color, ylim_max=None):
    """Grafica la media móvil de una serie diaria, suavizada a 7 días."""
    fig, ax = plt.subplots(figsize=(12,6))
    fig.patch.set_facecolor('#fff8f8')
    ax.set_facecolor('#fff8f8')
    ax.plot(serie.index, serie.values, linestyle='-', linewidth=3, color=color)
    if ylim_max:
        ax.set_ylim(0, ylim_max)
    else:
        ax.set_ylim(0, serie.max() * 1.10)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    fig.autofmt_xdate(rotation=30)
    st.subheader(titulo)
    st.pyplot(fig)

def limpiar_y_convertir(serie):
    """Convierte texto con posibles comas a número."""
    return pd.to_numeric(serie.astype(str).str.replace(",", "."), errors="coerce")

def proteger_columna(df, columna, valor_por_defecto=pd.NA):
    """Añade la columna al DataFrame si no existe (rellena con valor por defecto)."""
    if columna not in df.columns:
        df[columna] = valor_por_defecto

def tiempo_a_texto(tiempo):
    """Convierte minutos o timedelta a texto 'X h Y min' para mostrar en la app."""
    if tiempo is None:
        return "No registrado"
    
    # Si es timedelta, convierto a minutos
    if isinstance(tiempo, timedelta):
        minutos = tiempo.total_seconds() / 60
    else:
        minutos = tiempo  # se asume que es ya minutos (float o int)
    
    # Evito valores negativos
    minutos = max(minutos, 0)
    
    h = int(minutos // 60)
    m = int(minutos % 60)
    return f"{h} h {m} min"

# 3. === CONFIGURACIÓN INICIAL Y CONEXIÓN A GOOGLE SHEETS ===

# Ajusto manualmente el horario a Cdmx, que es UTC-6. UTC significa "tiempo universal coordinado".
ahora = datetime.utcnow() - timedelta(hours=6)

# Conexión a Google Sheets
cred_json = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
cred_dict = json.loads(cred_json) if isinstance(cred_json, str) else dict(cred_json)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key("1LsuO8msQi9vXwNJq1L76fz_rTWJjtNLjecjaetdI8oY").sheet1

# 4. === LIMPIEZA Y PREPROCESAMIENTO DE LOS DATOS ===

# Convierto la hoja de Google Sheets en un DataFrame de pandas
data = pd.DataFrame(sheet.get_all_records())

# Limpio los nombres de las columnas
data.columns = data.columns.str.strip()

data["hora"] = pd.to_datetime(data["hora"], errors="coerce")
data["fecha_hora"] = pd.to_datetime(data["fecha"] + " " + data["hora"], errors="coerce")
data = data.dropna(subset=["fecha_hora"])
data["tipo_leche"] = data["tipo_leche"].astype(str).str.strip().str.lower()
data = data[data["fecha_hora"] <= ahora]

proteger_columna(data, "duracion_seno_materno")
proteger_columna(data, "hubo_evacuación")

# 5. === PRESENTACIÓN INICIAL DE LA APP ===

# Genero una lista con los nombres de los jpg de las fotos
fotos_amelia = [
    "foto_amor1.jpg",
    "foto_amor2.jpg",
    "foto_amor3.jpg",
    "foto_amor4.jpg",
    "foto_amor5.jpg"
]

# Elijo, de manera aleatoria, el nombre de una foto
foto_elegida = random.choice(fotos_amelia)

st.title("Registro de cuidados de Amelia")
st.image(foto_elegida, use_container_width=True)
st.markdown("<div style='text-align: center'><em>Por ella, que sonríe, y en cuya alegría encontramos fuerza para seguir.</em></div>", unsafe_allow_html=True)

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

# 6. === FORMULARIO DE REGISTRO ===

st.header("Evento")

fecha = ahora.date()
hora = ahora.time()

st.info(f"El registro se guardará automáticamente con la fecha {fecha} y la hora actual {hora.strftime('%H:%M')}.")


tipo = st.radio("Tipo de evento", [
    "colocación de bolsa", "extracción de leche", "evacuación", "puenteo", "toma de leche", "seno materno", "vaciado"
])

# Inicializo valores
cantidad_leche_ml = 0.0
tipo_leche = ""
cantidad_popo_puenteada = 0
cantidad_extraida_ml = 0
duracion_seno_materno = 0

# Genero campos condicionales reactivos
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

# Creo un botón para guardar los registros
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

# 7. === PROCESAMIENTO Y CÁLCULO DE MÉTRICAS ===

hoy = ahora.date()
data["fecha"] = pd.to_datetime(data["fecha"], errors="coerce").dt.date
datos_hoy = data[data["fecha"] == hoy]

# Limpieza y conversión

columnas_a_limpiar = ["cantidad_leche_ml", "cantidad_popo_puenteada", "cantidad_extraida_de_leche", "duracion_seno_materno"]

for col in columnas_a_limpiar:
    data[col] = limpiar_y_convertir(data[col])
    
# === Última toma de leche (incluye seno materno) ===

leche_historica = data[data["tipo"].isin(["toma de leche", "seno materno"])]
ultima_toma_historica = leche_historica.sort_values("fecha_hora", ascending=False).iloc[0]
minutos_desde_ultima_toma = (ahora - ultima_toma_historica["fecha_hora"]).total_seconds() / 60
texto_ultima_toma = tiempo_a_texto(minutos_desde_ultima_toma)

# === Leche hoy (solo tipo "toma de leche") ===

leche = datos_hoy[datos_hoy["tipo"] == "toma de leche"]
leche = leche[leche["tipo_leche"].isin(["materna", "nutramigen", "puramino"])]

ml_24h = leche["cantidad_leche_ml"].sum()
ml_materna = leche[leche["tipo_leche"] == "materna"]["cantidad_leche_ml"].sum()
porcentaje_materna = (ml_materna / ml_24h * 100) if ml_24h > 0 else 0


# Seno hoy
seno_hoy = datos_hoy[datos_hoy["tipo"] == "seno materno"]
duracion_total_seno_hoy = seno_hoy["duracion_seno_materno"].sum()
leche["calorias"] = leche.apply(calcular_calorias, axis=1)
calorias_24h = leche["calorias"].sum()

# Consumo acumulado de leche hoy
leche_diaria = leche.dropna(subset=["cantidad_leche_ml"]).sort_values("fecha_hora")
leche_diaria["hora"] = leche_diaria["fecha_hora"].dt.strftime("%H:%M")
leche_diaria["acumulado"] = leche_diaria["cantidad_leche_ml"].cumsum()

# Promedio histórico
tomas_pasadas = data[
    (data["tipo"] == "toma de leche") &
    (data["tipo_leche"].isin(["materna", "puramino"])) &
    (data["fecha"] < hoy)
]
promedio_historico = tomas_pasadas.groupby("fecha")["cantidad_leche_ml"].sum().mean()

# Otros eventos
puenteos = datos_hoy[datos_hoy["tipo"] == "puenteo"]
puenteo_total = puenteos["cantidad_popo_puenteada"].sum()

evacs = datos_hoy[(datos_hoy["tipo"] == "evacuación") & (datos_hoy["hubo_evacuación"] == "sí")]
n_evacuaciones = len(evacs)

extracciones = datos_hoy[datos_hoy["tipo"] == "extracción de leche"]
ultima_extraccion = extracciones["fecha_hora"].max()
tiempo_desde_extraccion = ahora - ultima_extraccion if pd.notna(ultima_extraccion) else None
ml_extraido = extracciones["cantidad_extraida_de_leche"].sum()


vaciados = data[(data["tipo"] == "vaciado") & (data["fecha_hora"] <= ahora)]
ultimo_vaciado = vaciados["fecha_hora"].max()
min_desde_vaciado = (ahora - ultimo_vaciado).total_seconds() // 60 if pd.notna(ultimo_vaciado) else None

cambios = data[(data["tipo"] == "colocación de bolsa") & (data["fecha_hora"] <= ahora)]
ultima_colocacion = cambios["fecha_hora"].max()
tiempo_desde_cambio = ahora - ultima_colocacion if pd.notna(ultima_colocacion) else None

# 7. === DESPLIEGUE DE LAS MÉTRICAS EN STREAMLIT ===

# === Indicadores de alimentación ===

st.subheader("Indicadores de alimentación del día")

st.metric("Tiempo desde última toma de leche, incluyendo seno", texto_ultima_toma)
st.metric("Tiempo desde última extracción", tiempo_a_texto(tiempo_desde_extraccion))
st.metric("Leche consumida", f"{ml_24h:.0f} ml")
st.metric("Leche extraída", f"{ml_extraido:.0f} ml")
st.metric("Calorías consumidas", f"{calorias_24h:.0f} kcal")
st.metric("Porcentaje de leche materna", f"{porcentaje_materna:.0f}%")
st.metric("Duración de seno materno", f"{duracion_total_seno_hoy:.0f} min")

# === Indicadores de digestión ===

st.subheader("Indicadores de digestión del día")

st.metric("Número de puenteos", f"{len(puenteos)} veces")
st.metric("Volumen puenteado", f"{puenteo_total:.0f} ml")
st.metric("Número de evacuaciones", f"{n_evacuaciones} veces")
st.metric("Tiempo desde último vaciamiento", tiempo_a_texto(min_desde_vaciado))
st.metric("Tiempo desde último cambio de bolsa", tiempo_a_texto(tiempo_desde_cambio))

# 8. === GRÁFICOS EXPLICATIVOS ===
# Creo gráficos con una media móvil de 7 días, para que las curvas sean más lisas. Documento esto con un caption

st.caption("Todas las gráficas a continuación presentan valores suavizados con media móvil de 7 días, para facilitar el seguimiento de tendencias.")

# === Gráfico de consumo de calorías ===
historico_leche = data[
    (data["tipo"] == "toma de leche") &
    (data["tipo_leche"].isin(["materna", "nutramigen", "puramino"]))
].copy()
historico_leche["calorias"] = historico_leche.apply(calcular_calorias, axis=1)
calorias_por_dia = historico_leche.groupby("fecha")["calorias"].sum().sort_index()
media_movil = calorias_por_dia.rolling(window=7, min_periods=7).mean()
graficar_media_movil(media_movil, "Calorías diarias", '#c8a2c8')


# === Gráfico de extracción de leche ===
historico_extraccion = data[data["tipo"] == "extracción de leche"].copy()
extraccion_por_dia = historico_extraccion.groupby("fecha")["cantidad_extraida_de_leche"].sum().sort_index()
extraccion_media_movil = extraccion_por_dia.rolling(window=7, min_periods=7).mean()
graficar_media_movil(extraccion_media_movil, "Extracción de leche (ml)", '#f4c2c2', ylim_max=220)


# === Gráfico de porcentaje de leche materna ===
historico_tomas = data[data["tipo"] == "toma de leche"].copy()
porcentaje_materna_por_dia = historico_tomas.groupby("fecha").apply(calcular_porcentaje_materna).sort_index()
porcentaje_materna_media_movil = porcentaje_materna_por_dia.rolling(window=7, min_periods=7).mean()
graficar_media_movil(porcentaje_materna_media_movil, "Porcentaje de leche materna", '#e3a6b4', ylim_max=100)
