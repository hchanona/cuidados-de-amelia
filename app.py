import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# Conectar con Google Sheets
import json
import os

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

st.title("🍼 Cuidados de Amelia")

# Formulario
with st.form("formulario_registro"):
    dia = st.date_input("Día")
    hora = st.time_input("Hora")
    tipo = st.selectbox("Tipo de operación", ["medicamento", "vaciado de bolsa", "toma de leche", "cambio de bolsa"])
    operacion = st.text_input("Operación específica")
    hora_inicio = st.time_input("Hora de inicio")
    hora_fin = st.time_input("Hora de fin")
    cantidad = 0
    if tipo == "toma de leche":
        cantidad = st.number_input("Cantidad de leche (ml)", min_value=0)

    enviar = st.form_submit_button("Guardar")

    if enviar:
        nueva_fila = [
            str(dia),
            str(hora),
            tipo,
            operacion,
            str(hora_inicio),
            str(hora_fin),
            cantidad
        ]
        sheet.append_row(nueva_fila)
        st.success("✅ Registro guardado exitosamente.")
        st.experimental_rerun()

# Mostrar últimos registros
st.subheader("📋 Últimos registros")
if not data.empty:
    st.dataframe(data.tail(10), use_container_width=True)
    data["fecha_hora"] = pd.to_datetime(data["dia"] + " " + data["hora"])
    
    leche = data[data["tipo"] == "toma de leche"]
    if not leche.empty:
        ult_leche = leche.sort_values("fecha_hora", ascending=False).iloc[0]
        st.metric("🍼 Última toma", f'{ult_leche["cantidad_leche"]} ml', ult_leche["hora"])

    meds = data[data["tipo"] == "medicamento"]
    if not meds.empty:
        ult_meds = meds.sort_values("fecha_hora", ascending=False).iloc[0]
        st.metric("💊 Último medicamento", ult_meds["operacion"], ult_meds["hora"])

    ahora = datetime.now()
    ult_24h = leche[leche["fecha_hora"] > ahora - timedelta(hours=24)]
    total_ml = ult_24h["cantidad_leche"].sum()
    st.metric("🕒 Leche últimas 24h", f"{total_ml:.0f} ml")

    # Botón para descargar CSV
    st.download_button("⬇️ Descargar histórico", data.to_csv(index=False), "historico_amelia.csv", "text/csv")
