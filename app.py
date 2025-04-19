import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json

# Ajuste horario a CDMX
ahora = datetime.utcnow() - timedelta(hours=6)

# Conexión a Google Sheets
cred_json = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
cred_dict = json.loads(cred_json) if isinstance(cred_json, str) else dict(cred_json)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key("1LsuO8msQi9vXwNJq1L76fz_rTWJjtNLjecjaetdI8oY").sheet1

# Cargar base
data = pd.DataFrame(sheet.get_all_records())
if not data.empty:
    data["fecha_hora"] = pd.to_datetime(data["fecha"] + " " + data["hora"], errors="coerce")
    data = data.dropna(subset=["fecha_hora"])
    data = data[data["fecha_hora"] <= ahora]

# Título
st.title("🍼 Cuidados de Amelia")

# === Formulario ===
with st.form("registro"):
    fecha = st.date_input("Fecha", value=ahora.date())
    hora = st.time_input("Hora", value=ahora.time())
    tipo = st.selectbox("Tipo de evento", ["toma de leche", "puenteo", "evacuación", "vaciado", "colocación de bolsa"])

    # Inicializar variables
    cantidad_leche_ml = ""
    tipo_leche = ""
    cantidad_popo_puenteada = ""
    hubo_evacuacion = ""

    if tipo == "toma de leche":
        cantidad_leche_oz = st.number_input("Cantidad de leche (oz)", min_value=0.0, step=0.1)
        cantidad_leche_ml = cantidad_leche_oz * 29.5735
        tipo_leche = st.selectbox("Tipo de leche", ["materna", "Puramino"])

    elif tipo == "puenteo":
        cantidad_popo_puenteada = st.number_input("Cantidad de popó puenteada (ml)", min_value=0, step=1)

    elif tipo == "evacuación":
        hubo_evacuacion = "sí"

    enviado = st.form_submit_button("Guardar")

    if enviado:
        fecha_hora_reg = datetime.combine(fecha, hora)
        if fecha_hora_reg > ahora:
            st.error("❌ La fecha y hora no pueden estar en el futuro.")
        else:
            fila = [
                str(fecha),
                str(hora),
                tipo,
                cantidad_leche_ml if tipo == "toma de leche" else "",
                tipo_leche if tipo == "toma de leche" else "",
                cantidad_popo_puenteada if tipo == "puenteo" else "",
                hubo_evacuacion if tipo == "evacuación" else ""
            ]
            sheet.append_row(fila)
            st.success("✅ Registro guardado correctamente.")
            st.experimental_rerun()

# === Estadísticas ===
if not data.empty:
    st.subheader("📊 Estadísticas en tiempo real")
    ultimas_24h = data[data["fecha_hora"] > ahora - timedelta(hours=24)]

    # Leche
    leche = ultimas_24h[ultimas_24h["tipo"] == "toma de leche"]
    leche["cantidad_leche_ml"] = pd.to_numeric(leche["cantidad_leche_ml"], errors="coerce")
    ml_24h = leche["cantidad_leche_ml"].sum()

    def calcular_calorias(row):
        if row["tipo_leche"] == "materna":
            return row["cantidad_leche_ml"] * 0.67
        elif row["tipo_leche"] == "Puramino":
            return row["cantidad_leche_ml"] * 0.72
        return 0

    leche["calorias"] = leche.apply(calcular_calorias, axis=1)
    calorias_24h = leche["calorias"].sum()

    # Puenteo
    puenteos = ultimas_24h[ultimas_24h["tipo"] == "puenteo"]
    puenteos["cantidad_popo_puenteada"] = pd.to_numeric(puenteos["cantidad_popo_puenteada"], errors="coerce")
    puenteo_total = puenteos["cantidad_popo_puenteada"].sum()

    # Evacuaciones
    evacs = ultimas_24h[(ultimas_24h["tipo"] == "evacuación") & (ultimas_24h["hubo_evacuación"] == "sí")]
    n_evacuaciones = len(evacs)

    # Último vaciamiento
    vaciados = data[(data["tipo"] == "vaciado") & (data["fecha_hora"] <= ahora)]
    ultimo_vaciado = vaciados["fecha_hora"].max()
    min_desde_vaciado = (ahora - ultimo_vaciado).total_seconds() // 60 if pd.notna(ultimo_vaciado) else None

    # Última colocación de bolsa
    cambios = data[(data["tipo"] == "colocación de bolsa") & (data["fecha_hora"] <= ahora)]
    ultima_colocacion = cambios["fecha_hora"].max()
    tiempo_desde_cambio = ahora - ultima_colocacion if pd.notna(ultima_colocacion) else None

    # Mostrar métricas
    st.metric("🍼 Leche últimas 24h", f"{ml_24h:.0f} ml")
    st.metric("🔥 Calorías últimas 24h", f"{calorias_24h:.0f} kcal")
    st.metric("💩 Popó puenteada últimas 24h", f"{puenteo_total:.0f} ml")
    st.metric("🚼 Evacuaciones últimas 24h", f"{n_evacuaciones} veces")

    if min_desde_vaciado is not None and min_desde_vaciado >= 0:
        horas = int(min_desde_vaciado // 60)
        minutos = int(min_desde_vaciado % 60)
        st.metric("⏱️ Desde último vaciamiento", f"{horas} h {minutos} min")
    elif min_desde_vaciado is not None:
        st.warning("⚠️ El último vaciamiento está registrado en el futuro.")

    if tiempo_desde_cambio is not None:
        h = int(tiempo_desde_cambio.total_seconds() // 3600)
        m = int(tiempo_desde_cambio.total_seconds() % 3600 // 60)
        st.metric("🩹 Desde última colocación de bolsa", f"{h} h {m} min")

    # Descarga de histórico
    st.download_button("⬇️ Descargar histórico", data.to_csv(index=False), "historico_amelia.csv", "text/csv")
