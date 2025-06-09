import os
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from xerenity import Xerenity
from info_paises import info_paises
from funciones_xp import get_last_value
import matplotlib.pyplot as plt

# =======================
# 1. Configuración inicial y conexión
# =======================

load_dotenv()
xerenity = Xerenity(os.getenv("XERENITY_USER"), os.getenv("XERENITY_PASS"))

# =======================
# 2. Construir tabla base con TBC y EMBI
# =======================

def construir_tabla():
    tabla = {"country": [], "moneda": [], "tbc": [], "embi": []}
    for pais in info_paises:
        tabla["country"].append(pais["nombre"])
        tabla["moneda"].append(pais["moneda"])
        tbc_series = xerenity.series.search(ticker=pais["tbc_ticker"])
        embi_series = xerenity.series.search(ticker=pais["embi_ticker"])
        tabla["tbc"].append(get_last_value(tbc_series))
        tabla["embi"].append(get_last_value(embi_series))
    return pd.DataFrame(tabla)

df = construir_tabla()
df["tbc"] = pd.to_numeric(df["tbc"], errors="coerce").round(2)
df["embi"] = pd.to_numeric(df["embi"], errors="coerce").round(2)

# =======================
# 3. Cargar y limpiar datos externos de riesgo país
# =======================

df_risk = pd.read_csv(os.path.join("..", "data", "country_risk_actualizado.csv"), sep=",", encoding="utf-8")

df_risk.columns = df_risk.columns.str.strip().str.lower().str.replace(" ", "_")

cols_percent = [
    "default_spread", "total_equity_risk_premium", "country_risk_premium",
    "sovereign_cds", "net_of_us", "country_risk_premium2"
]

for col in cols_percent:
    if col in df_risk.columns:
        df_risk[col] = (
            df_risk[col].astype(str)
            .str.replace("%", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df_risk[col] = pd.to_numeric(df_risk[col], errors="coerce")

# =======================
# 4. Unir la prima de riesgo al DataFrame principal
# =======================

df["country"] = df["country"].astype(str).str.strip()
df_risk["country"] = df_risk["country"].astype(str).str.strip()

df = df.merge(
    df_risk[["country", "country_risk_premium"]],
    on="country",
    how="left"
)

# =======================
# 5. Cálculos de riesgo y devaluación
# =======================

df["country_risk_premium"] = pd.to_numeric(df["country_risk_premium"], errors="coerce")
df["riesgo_minimo"] = df[["embi", "country_risk_premium"]].min(axis=1)
df["moneda_funcional"] = np.where(df["tbc"].isna(), "USD", df["moneda"])
tbc_usa = df.loc[df["country"] == "EE.UU.", "tbc"].values[0]

df["devaluacion_esperada"] = df.apply(
    lambda row: 0.0 if row["moneda_funcional"] == "USD" else row["tbc"] - tbc_usa,
    axis=1
)
df["tasa_libre_riesgo"] = tbc_usa
df["tasa_teorica_descuento"] = (
    df["riesgo_minimo"] + df["devaluacion_esperada"] + df["tasa_libre_riesgo"]
)

# =======================
# 6. Renombrar columnas y reordenar
# =======================

df = df.rename(columns={
    "country": "País",
    "moneda": "Moneda",
    "tbc": "Tasa del Banco Central",
    "embi": "EMBI",
    "country_risk_premium": "Prima de Riesgo",
    "riesgo_minimo": "Riesgo Mínimo",
    "moneda_funcional": "Moneda Funcional",
    "devaluacion_esperada": "Devaluación Esperada",
    "tasa_libre_riesgo": "Tasa Libre de Riesgo",
    "tasa_teorica_descuento": "Tasa Teórica de Descuento"
})

orden_columnas = [
    "País", "Moneda", "Moneda Funcional", "Tasa del Banco Central", "EMBI",
    "Prima de Riesgo", "Riesgo Mínimo", "Devaluación Esperada",
    "Tasa Libre de Riesgo", "Tasa Teórica de Descuento"
]
df = df[orden_columnas]

# =======================
# 7. Crear imagen de tabla con matplotlib
# =======================

# Renombrar columnas para la imagen
df_img = df.rename(columns={
    "Tasa del Banco Central": "T. Banco",
    "Prima de Riesgo": "Riesgo",
    "Riesgo Mínimo": "Min. Riesgo",
    "Devaluación Esperada": "Devaluación",
    "Tasa Libre de Riesgo": "Libre Riesgo",
    "Tasa Teórica de Descuento": "Tasa Teórica"
})

columnas_visibles = [
    "País", "Moneda", "Moneda Funcional", "T. Banco", 
    "EMBI", "Riesgo", "Min. Riesgo", "Devaluación", 
    "Libre Riesgo", "Tasa Teórica"
]
df_img = df_img[columnas_visibles]

# Redondear
for col in df_img.columns:
    if df_img[col].dtype in ["float64", "float32"]:
        df_img[col] = df_img[col].round(2)

# Crear imagen
fig, ax = plt.subplots(figsize=(18, len(df_img) * 0.5 + 2))
ax.axis("off")
tabla = ax.table(
    cellText=df_img.values,
    colLabels=df_img.columns,
    cellLoc='center',
    loc='center'
)
tabla.auto_set_font_size(False)
tabla.set_fontsize(9)
tabla.scale(1, 1.5)

plt.savefig(os.path.join("..", "assets", "tabla_teorica_descuento.jpg"), bbox_inches='tight', dpi=300)
plt.close()

