import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Configuración inicial del título
tz_offset = timedelta(hours=-6)
st.set_page_config(page_title="Cuidados de Amelia")
st.title("🍼 Cuidados de Amelia")

# Autenticación con Google Sheets
import json
cred_json = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
if isinstance(cred_json, str):
    cred_dict = json.loads(cred_json)
else:
    cred_dict = dict(cred_json)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key("1LsuO8msQi9vXwNJq1L76fz_rTWJjtNLjecjaetdI8oY").sheet1

data = pd.DataFrame(sheet.get_all_records())

# Formulario de captura
with st.form("registro"):
    fecha = st.date_input("Fecha")
    hora = st.time_input("Hora")
    tipo = st.selectbox("Tipo de evento", ["toma de leche", "vaciado", "puenteo", "evacuación"])
    
    cantidad_leche_oz = st.number_input("Cantidad de leche (oz)", min_value=0.0, step=0.1, format="%.2f")
    tipo_leche = st.selectbox("Tipo de leche", ["materna", "Puramino"])
    cantidad_popo_puenteada = st.number_input("Cantidad de popó puenteada (ml)", min_value=0)

    submitted = st.form_submit_button("Guardar")
    if submitted:
        nueva_fila = [
            str(fecha), str(hora), tipo,
            round(cantidad_leche_oz * 29.5735, 4),  # convertir a ml
            tipo_leche,
            cantidad_popo_puenteada,
            "sí" if tipo == "evacuación" else "no"
        ]
        sheet.append_row(nueva_fila)
        st.success("Registro guardado exitosamente.")
        st.rerun()

# Procesamiento de datos
if not data.empty:
    data["fecha_hora"] = pd.to_datetime(data["fecha"] + " " + data["hora"], errors="coerce")
    ahora = datetime.now() + tz_offset
    ult_24h = data[data["fecha_hora"] > ahora - timedelta(hours=24)]

    # Convertir texto decimal con coma a punto
    leche = ult_24h[ult_24h["tipo"] == "toma de leche"].copy()
    leche["cantidad_leche_ml"] = pd.to_numeric(
        leche["cantidad_leche_ml"].astype(str).str.replace(",", "."), errors="coerce"
    )

    puenteos = ult_24h[ult_24h["tipo"] == "puenteo"].copy()
    puenteos["cantidad_popo_puenteada"] = pd.to_numeric(
        puenteos["cantidad_popo_puenteada"].astype(str).str.replace(",", "."), errors="coerce"
    )

    # Estadísticas
    st.subheader(":bar_chart: Estadísticas en tiempo real")

    st.metric("🍼 Leche últimas 24h", f"{leche['cantidad_leche_ml'].sum():.0f} ml")
    cal_materna = leche[leche["tipo_leche"] == "materna"]["cantidad_leche_ml"].sum() * 0.65
    cal_puramino = leche[leche["tipo_leche"] == "Puramino"]["cantidad_leche_ml"].sum() * 0.67
    st.metric("🔥 Calorías últimas 24h", f"{(cal_materna + cal_puramino):.0f} kcal")

    st.metric("💩 Popó puenteada últimas 24h", f"{puenteos['cantidad_popo_puenteada'].sum():.0f} ml")

    evacuaciones = ult_24h[ult_24h["tipo"] == "evacuación"]
    st.metric("📉 Evacuaciones últimas 24h", f"{len(evacuaciones)} veces")

    vaciamientos = data[data["tipo"] == "vaciado"].copy()
    vaciamientos["fecha_hora"] = pd.to_datetime(vaciamientos["fecha"] + " " + vaciamientos["hora"], errors="coerce")
    if not vaciamientos.empty:
        ult_vaciado = vaciamientos.sort_values("fecha_hora", ascending=False).iloc[0]
        minutos_desde_vaciado = (ahora - ult_vaciado["fecha_hora"]).total_seconds() / 60
        st.metric("⏰ Desde último vaciamiento", f"{int(minutos_desde_vaciado)} minutos")

    cambios_bolsa = data[data["tipo"] == "cambio de bolsa"].copy()
    cambios_bolsa["fecha_hora"] = pd.to_datetime(cambios_bolsa["fecha"] + " " + cambios_bolsa["hora"], errors="coerce")
    if not cambios_bolsa.empty:
        ult_cambio = cambios_bolsa.sort_values("fecha_hora", ascending=False).iloc[0]
        minutos_desde_cambio = (ahora - ult_cambio["fecha_hora"]).total_seconds() / 60
        st.metric("🕛 Desde último cambio de bolsa", f"{int(minutos_desde_cambio)} minutos")

    # Porcentaje leche materna
    total_ml = leche["cantidad_leche_ml"].sum()
    if total_ml > 0:
        ml_materna = leche[leche["tipo_leche"] == "materna"]["cantidad_leche_ml"].sum()
        porcentaje = ml_materna / total_ml
        st.subheader(":baby_bottle: % Leche materna últimas 24h")
        fig, ax = plt.subplots()
        ax.pie([porcentaje, 1 - porcentaje], labels=["materna", "Puramino"], autopct="%1.0f%%")
        ax.set_title("Distribución de leche (ml) por tipo")
        st.pyplot(fig)

    # Descargar CSV
    st.download_button("⬇️ Descargar histórico", data.to_csv(index=False), "historico_amelia.csv", "text/csv")
