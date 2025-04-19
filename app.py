import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json

# === Autenticación con Google Sheets ===
cred_json = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
cred_dict = json.loads(cred_json) if isinstance(cred_json, str) else dict(cred_json)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key("1LsuO8msQi9vXwNJq1L76fz_rTWJjtNLjecjaetdI8oY").sheet1

# === Cargar datos ===
data = pd.DataFrame(sheet.get_all_records())

# Validación robusta de estructura
if data.empty:
    st.warning("⚠️ Aún no hay datos registrados en la hoja. Usa el formulario para agregar el primero.")
else:
    try:
        data["fecha_hora"] = pd.to_datetime(data["fecha"] + " " + data["hora"], errors="coerce")
        data = data.dropna(subset=["fecha_hora"])
    except KeyError as e:
        st.error(f"❌ Error: falta la columna esperada: {e}")

st.title("🍼 Cuidados de Amelia")

# === FORMULARIO ===
with st.form("registro"):
    fecha = st.date_input("Fecha", value=datetime.now().date())
    hora = st.time_input("Hora", value=datetime.now().time())
    tipo = st.selectbox("Tipo de evento", ["toma de leche", "puenteo", "evacuación", "vaciado", "colocación de bolsa"])

    # Inicializar campos
    cantidad_leche_ml = ""
    tipo_leche = ""
    cantidad_popo_puenteada = ""
    hubo_evacuacion = ""

    # Campos condicionales según tipo
    if tipo == "toma de leche":
        cantidad_leche_ml = st.number_input("Cantidad de leche (ml)", min_value=0, step=1)
        tipo_leche = st.selectbox("Tipo de leche", ["materna", "Puramino"])
    elif tipo == "puenteo":
        cantidad_popo_puenteada = st.number_input("Cantidad de popó puenteada (ml)", min_value=0, step=1)
    elif tipo == "evacuación":
        hubo_evacuacion = st.selectbox("¿Hubo evacuación?", ["sí", "no"])

    enviado = st.form_submit_button("Guardar")

    if enviado:
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

# === MÉTRICAS EN TIEMPO REAL ===
if not data.empty:
    st.subheader("📊 Estadísticas en tiempo real")
    ahora = datetime.now()
    ultimas_24h = data[data["fecha_hora"] > ahora - timedelta(hours=24)]

    # 1. Leche en 24h
    leche = ultimas_24h[ultimas_24h["tipo"] == "toma de leche"]
    leche["cantidad_leche_ml"] = pd.to_numeric(leche["cantidad_leche_ml"], errors="coerce")
    ml_24h = leche["cantidad_leche_ml"].sum()

    # 2. Calorías en 24h
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

    # 4. Evacuaciones
    evacs = ultimas_24h[(ultimas_24h["tipo"] == "evacuación") & (ultimas_24h["hubo_evacuación"] == "sí")]
    n_evacuaciones = len(evacs)

    # 5. Tiempo desde último vaciamiento
    vaciados = data[data["tipo"] == "vaciado"]
    ultimo_vaciado = vaciados["fecha_hora"].max()
    min_desde_vaciado = (ahora - ultimo_vaciado).total_seconds() // 60 if pd.notna(ultimo_vaciado) else None

    # 6. Tiempo desde última colocación de bolsa
    cambios = data[data["tipo"] == "colocación de bolsa"]
    ultima_colocacion = cambios["fecha_hora"].max()
    dias_desde_cambio = (ahora - ultima_colocacion).days if pd.notna(ultima_colocacion) else None

    # === Mostrar métricas ===
    st.metric("🍼 Leche últimas 24h", f"{ml_24h:.0f} ml")
    st.metric("🔥 Calorías últimas 24h", f"{calorias_24h:.0f} kcal")
    st.metric("💩 Popó puenteada últimas 24h", f"{puenteo_total:.0f} ml")
    st.metric("🚼 Evacuaciones últimas 24h", f"{n_evacuaciones} veces")
    if min_desde_vaciado is not None:
        st.metric("⏱️ Desde último vaciamiento", f"{int(min_desde_vaciado)} minutos")
    if dias_desde_cambio is not None:
        st.metric("🩹 Desde última colocación de bolsa", f"{int(dias_desde_cambio)} días")

    # === Descargar CSV ===
    st.download_button("⬇️ Descargar histórico", data.to_csv(index=False), "historico_amelia.csv", "text/csv")
