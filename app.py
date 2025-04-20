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

# Cargar registros
data = pd.DataFrame(sheet.get_all_records())
if not data.empty:
    data["hora"] = pd.to_datetime(data["hora"], errors="coerce").dt.strftime("%H:%M")
    data["fecha_hora"] = pd.to_datetime(data["fecha"] + " " + data["hora"], errors="coerce")
    data = data.dropna(subset=["fecha_hora"])
    data = data[data["fecha_hora"] <= ahora]

st.title("🍼 Cuidados de Amelia")

with st.form("registro"):
    fecha = st.date_input("Fecha", value=ahora.date())
    hora = st.time_input("Hora", value=ahora.time())
    tipo = st.selectbox("Tipo de evento", [
        "toma de leche", "puenteo", "evacuación", "vaciado", "colocación de bolsa", "extracción de leche"
    ])

    cantidad_leche_oz = st.number_input("Cantidad de leche (oz)", min_value=0.0, step=0.1)
    cantidad_leche_ml = (cantidad_leche_oz * 29.5735)
    tipo_leche = st.selectbox("Tipo de leche", ["", "materna", "Puramino"])
    cantidad_popo_puenteada = st.number_input("Cantidad de popó puenteada (ml)", min_value=0, step=1)
    cantidad_extraida_ml = st.number_input("Cantidad extraída de leche (ml)", min_value=0, step=1)

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
                cantidad_leche_ml,
                tipo_leche,
                cantidad_popo_puenteada,
                "sí" if tipo == "evacuación" else "no",
                cantidad_extraida_ml
            ]
            sheet.append_row(fila)
            st.success("✅ Registro guardado correctamente.")
            st.rerun()

# === Estadísticas ===
if not data.empty:
    st.subheader("📊 Estadísticas en tiempo real")
    hoy = ahora.date()
    data["fecha"] = pd.to_datetime(data["fecha"], errors="coerce").dt.date
    datos_hoy = data[data["fecha"] == hoy]

    # Limpieza
    data["cantidad_leche_ml"] = data["cantidad_leche_ml"].astype(str).str.replace(",", ".")
    data["cantidad_popo_puenteada"] = data["cantidad_popo_puenteada"].astype(str).str.replace(",", ".")
    data["cantidad_extraida_de_leche"] = data["cantidad_extraida_de_leche"].astype(str).str.replace(",", ".")

    data["cantidad_leche_ml"] = pd.to_numeric(data["cantidad_leche_ml"], errors="coerce")
    data["cantidad_popo_puenteada"] = pd.to_numeric(data["cantidad_popo_puenteada"], errors="coerce")
    data["cantidad_extraida_de_leche"] = pd.to_numeric(data["cantidad_extraida_de_leche"], errors="coerce")

    leche = datos_hoy[datos_hoy["tipo"] == "toma de leche"]
    leche["cantidad_leche_ml"] = pd.to_numeric(leche["cantidad_leche_ml"], errors="coerce")
    leche["tipo_leche"] = leche["tipo_leche"].astype(str).str.strip().str.lower()
    leche = leche[leche["tipo_leche"].isin(["materna", "puramino"])]

    ml_24h = leche["cantidad_leche_ml"].sum()

    if not leche.empty:
        ultima_toma = leche.sort_values("fecha_hora", ascending=False).iloc[0]
        minutos_desde_ultima = (ahora - ultima_toma["fecha_hora"]).total_seconds() / 60
        if minutos_desde_ultima >= 0:
            h = int(minutos_desde_ultima // 60)
            m = int(minutos_desde_ultima % 60)
            st.metric("⏱️ Desde última toma de leche", f"{h} h {m} min")
        else:
            st.warning("⚠️ La última toma de leche está registrada en el futuro.")

    def calcular_calorias(row):
        if row["tipo_leche"] == "materna":
            return row["cantidad_leche_ml"] * 0.67
        elif row["tipo_leche"] == "puramino":
            return row["cantidad_leche_ml"] * 0.72
        return 0

    leche["calorias"] = leche.apply(calcular_calorias, axis=1)
    calorias_24h = leche["calorias"].sum()

    leche_tipo_ml = leche.groupby("tipo_leche")["cantidad_leche_ml"].sum()
    if not leche_tipo_ml.empty:
        st.subheader("🥛 Proporción de tipo de leche por volumen (hoy, en ml)")
        st.pyplot(leche_tipo_ml.plot.pie(autopct='%1.0f%%', ylabel="").figure)

    leche_diaria = leche.copy().dropna(subset=["fecha_hora", "cantidad_leche_ml"])
    leche_diaria = leche_diaria.sort_values("fecha_hora")
    leche_diaria["hora"] = leche_diaria["fecha_hora"].dt.strftime("%H:%M")
    leche_diaria["acumulado"] = leche_diaria["cantidad_leche_ml"].cumsum()

    tomas_pasadas = data[
        (data["tipo"] == "toma de leche") &
        (data["tipo_leche"].isin(["materna", "puramino"])) &
        (data["fecha"] < hoy)
    ]
    tomas_pasadas["cantidad_leche_ml"] = pd.to_numeric(tomas_pasadas["cantidad_leche_ml"], errors="coerce")
    promedio_historico = tomas_pasadas.groupby("fecha")["cantidad_leche_ml"].sum().mean()

    st.subheader("📈 Consumo acumulado de leche hoy")
    if not leche_diaria.empty:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot(leche_diaria["hora"], leche_diaria["acumulado"], marker='o', label="Hoy")
        ax.axhline(promedio_historico, color='red', linestyle='--', label="Promedio histórico")
        ax.set_xlabel("Hora del día")
        ax.set_ylabel("Consumo acumulado (ml)")
        ax.set_title("Leche acumulada vs promedio histórico")
        ax.legend()
        plt.xticks(rotation=45)
        st.pyplot(fig)

    puenteos = datos_hoy[datos_hoy["tipo"] == "puenteo"]
    puenteos["cantidad_popo_puenteada"] = pd.to_numeric(puenteos["cantidad_popo_puenteada"], errors="coerce")
    puenteo_total = puenteos["cantidad_popo_puenteada"].sum()

    evacs = datos_hoy[
        (datos_hoy["tipo"] == "evacuación") & 
        (datos_hoy["hubo_evacuación"] == "sí")
    ]
    n_evacuaciones = len(evacs)

    extracciones = datos_hoy[datos_hoy["tipo"] == "extracción de leche"]
    ultima_extraccion = extracciones["fecha_hora"].max()
    tiempo_desde_extraccion = ahora - ultima_extraccion if pd.notna(ultima_extraccion) else None

    vaciados = data[(data["tipo"] == "vaciado") & (data["fecha_hora"] <= ahora)]
    ultimo_vaciado = vaciados["fecha_hora"].max()
    min_desde_vaciado = (ahora - ultimo_vaciado).total_seconds() // 60 if pd.notna(ultimo_vaciado) else None

    cambios = data[(data["tipo"] == "colocación de bolsa") & (data["fecha_hora"] <= ahora)]
    ultima_colocacion = cambios["fecha_hora"].max()
    tiempo_desde_cambio = ahora - ultima_colocacion if pd.notna(ultima_colocacion) else None

    st.metric("🍼 Leche hoy", f"{ml_24h:.0f} ml")
    st.metric("🔥 Calorías hoy", f"{calorias_24h:.0f} kcal")
    st.metric("💩 Popó puenteada hoy", f"{puenteo_total:.0f} ml")
    st.metric("🔁 Número de puenteos hoy", f"{len(puenteos)} veces")
    st.metric("🚼 Evacuaciones hoy", f"{n_evacuaciones} veces")

    if tiempo_desde_extraccion is not None:
        h = int(tiempo_desde_extraccion.total_seconds() // 3600)
        m = int(tiempo_desde_extraccion.total_seconds() % 3600 // 60)
        st.metric("🕓 Desde última extracción", f"{h} h {m} min")
    else:
        st.info("🕓 Hoy no se ha extraído leche")

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

    st.subheader("📆 Calorías diarias totales")
    historico_leche = data[(data["tipo"] == "toma de leche") & data["tipo_leche"].isin(["materna", "puramino"])]
    historico_leche["cantidad_leche_ml"] = pd.to_numeric(historico_leche["cantidad_leche_ml"], errors="coerce")

    def calcular_calorias_historico(row):
        if row["tipo_leche"] == "materna":
            return row["cantidad_leche_ml"] * 0.67
        elif row["tipo_leche"] == "puramino":
            return row["cantidad_leche_ml"] * 0.72
        return 0

    historico_leche["calorias"] = historico_leche.apply(calcular_calorias_historico, axis=1)
    calorias_por_dia = historico_leche.groupby("fecha")["calorias"].sum().sort_index()

    if not calorias_por_dia.empty:
        fig, ax = plt.subplots()
        ax.plot(calorias_por_dia.index, calorias_por_dia.values, marker='o', linestyle='-')
        ax.set_xlabel("Fecha")
        ax.set_ylabel("Calorías totales")
        ax.set_title("Consumo diario de calorías")
        plt.xticks(rotation=45)
        st.pyplot(fig)

    st.download_button("⬇️ Descargar histórico", data.to_csv(index=False), "historico_amelia.csv", "text/csv")
