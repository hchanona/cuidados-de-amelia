# Librerías necesarias
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json

# === Autenticación con Google Sheets ===
# Se cargan las credenciales guardadas como secreto en Streamlit Cloud
cred_json = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
cred_dict = json.loads(cred_json) if isinstance(cred_json, str) else dict(cred_json)

# Se establecen los permisos necesarios
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)

# Se autoriza la conexión a Google Sheets
client = gspread.authorize(creds)

# Aquí se abre la hoja de cálculo por su ID (debe coincidir con la tuya)
sheet = client.open_by_key("1LsuO8msQi9vXwNJq1L76fz_rTWJjtNLjecjaetdI8oY").sheet1

# Se carga el contenido de la hoja como DataFrame
data = pd.DataFrame(sheet.get_all_records())

# Se crea una columna combinando fecha y hora como datetime
data["fecha_hora"] = pd.to_datetime(data["fecha"] + " " + data["hora"], errors="coerce")
data = data.dropna(subset=["fecha_hora"])  # Se eliminan registros con errores en datetime

# === Título principal de la app ===
st.title("🍼 Cuidados de Amelia")

# === FORMULARIO DE REGISTRO ===
with st.form("registro"):
    # Entrada de datos comunes
    fecha = st.date_input("Fecha", value=datetime.now().date())
    hora = st.time_input("Hora", value=datetime.now().time())
    tipo = st.selectbox("Tipo de evento", ["toma de leche", "puenteo", "evacuación", "vaciado", "colocación de bolsa"])

    # Campos condicionales según el tipo seleccionado
    cantidad_leche_ml = ""
    tipo_leche = ""
    cantidad_popo_puenteada = ""
    hubo_evacuacion = ""

    if tipo == "toma de leche":
        cantidad_leche_ml = st.number_input("Cantidad de leche (ml)", min_value=0, step=1)
        tipo_leche = st.selectbox("Tipo de leche", ["materna", "Puramino"])
    elif tipo == "puenteo":
        cantidad_popo_puenteada = st.number_input("Cantidad de popó puenteada (ml)", min_value=0, step=1)
    elif tipo == "evacuación":
        hubo_evacuacion = st.selectbox("¿Hubo evacuación?", ["sí", "no"])

    # Botón para guardar el registro
    enviado = st.form_submit_button("Guardar")

    if enviado:
        # Se prepara la fila con los datos relevantes (otros quedan vacíos)
        fila = [
            str(fecha),
            str(hora),
            tipo,
            cantidad_leche_ml if tipo == "toma de leche" else "",
            tipo_leche if tipo == "toma de leche" else "",
            cantidad_popo_puenteada if tipo == "puenteo" else "",
            hubo_evacuacion if tipo == "evacuación" else ""
        ]
        # Se guarda la fila en la hoja de cálculo
        sheet.append_row(fila)
        st.success("✅ Registro guardado correctamente.")
        st.experimental_rerun()  # Se recarga la app para mostrar cambios

# === MÉTRICAS EN TIEMPO REAL ===
st.subheader("📊 Estadísticas en tiempo real")

# Se define la ventana de las últimas 24 horas
ahora = datetime.now()
ultimas_24h = data[data["fecha_hora"] > ahora - timedelta(hours=24)]

# 1. Mililitros de leche en las últimas 24h
leche = ultimas_24h[ultimas_24h["tipo"] == "toma de leche"]
leche["cantidad_leche_ml"] = pd.to_numeric(leche["cantidad_leche_ml"], errors="coerce")
ml_24h = leche["cantidad_leche_ml"].sum()

# 2. Calorías en las últimas 24h (usando valores promedio por tipo)
def calcular_calorias(row):
    if row["tipo_leche"] == "materna":
        return row["cantidad_leche_ml"] * 0.67
    elif row["tipo_leche"] == "Puramino":
        return row["cantidad_leche_ml"] * 0.72
    return 0

leche["calorias"] = leche.apply(calcular_calorias, axis=1)
calorias_24h = leche["calorias"].sum()

# 3. Popó puenteada
puenteos = ultimas_24h[ultimas_24h["tipo"] == "puenteo"]
puenteos["cantidad_popo_puenteada"] = pd.to_numeric(puenteos["cantidad_popo_puenteada"], errors="coerce")
puenteo_total = puenteos["cantidad_popo_puenteada"].sum()

# 4. Evacuaciones (solo si hubo evacuación afirmada)
evacs = ultimas_24h[(ultimas_24h["tipo"] == "evacuación") & (ultimas_24h["hubo_evacuación"] == "sí")]
n_evacuaciones = len(evacs)

# 5. Tiempo desde el último vaciamiento
vaciados = data[data["tipo"] == "vaciado"]
ultimo_vaciado = vaciados["fecha_hora"].max()
min_desde_vaciado = (ahora - ultimo_vaciado).total_seconds() // 60 if pd.notna(ultimo_vaciado) else None

# 6. Tiempo desde la última colocación de bolsa
cambios = data[data["tipo"] == "colocación de bolsa"]
ultima_colocacion = cambios["fecha_hora"].max()
dias_desde_cambio = (ahora - ultima_colocacion).days if pd.notna(ultima_colocacion) else None

# === Visualización de métricas ===
st.metric("🍼 Leche últimas 24h", f"{ml_24h:.0f} ml")
st.metric("🔥 Calorías últimas 24h", f"{calorias_24h:.0f} kcal")
st.metric("💩 Popó puenteada últimas 24h", f"{puenteo_total:.0f} ml")
st.metric("🚼 Evacuaciones últimas 24h", f"{n_evacuaciones} veces")

# Se muestran los tiempos transcurridos desde últimos eventos
if min_desde_vaciado is not None:
    st.metric("⏱️ Desde último vaciamiento", f"{int(min_desde_vaciado)} minutos")
if dias_desde_cambio is not None:
    st.metric("🩹 Desde última colocación de bolsa", f"{int(dias_desde_cambio)} días")

# === Botón para descargar el histórico completo en CSV ===
st.download_button("⬇️ Descargar histórico", data.to_csv(index=False), "historico_amelia.csv", "text/csv")

