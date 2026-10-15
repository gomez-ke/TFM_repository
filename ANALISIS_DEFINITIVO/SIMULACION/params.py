"""
=============================================================================
params.py — Parámetros de entrada del sistema híbrido FV-BESS-Diésel
=============================================================================
Caso de estudio: Comunidad rural aislada, Colombia
Trabajo Fin de Máster — Simulación energética en Python

Organización:
  SITE    → Coordenadas y geometría del emplazamiento
  PV      → Módulo JA Solar JAM72S30-565/GR
  BESS    → Banco Victron LFP-51.2/100 (N módulos en paralelo)
  DIESEL  → Generador diésel de respaldo
  INV     → Inversor / PCS Victron Quattro 48V
  ECON    → Parámetros económicos (CAPEX, OPEX, financieros)
  SYS     → Parámetros globales del sistema

Fuentes:
  [1] JA Solar, Datasheet JAM72S30-565/GR, rev. 2024
  [2] Victron Energy, Datasheet LFP-51.2/100, rev. 2024
  [3] IRENA, Renewable Power Generation Costs 2024, Abu Dhabi, 2025
       (Global weighted-avg utility-scale PV: 691 USD/kW; non-OECD O&M input: 10.95 USD/kWp/yr)
  [4] NREL Annual Technology Baseline (ATB) 2024 — atb.nrel.gov
       (4h BESS CAPEX moderate: ~319 USD/kWh 2022$; FOM ~4% CAPEX/kW)
  [5] IPCC Guidelines for National GHG Inventories, 2006/2019
  [6] GlobalPetrolPrices, Precios de combustibles Colombia, 2024
  [7] Header archivo TMY EPW, ECMWF/ERA5, descargado PVGIS
  [8] Victron Energy, Datasheet MultiPlus-II / Quattro 48V, rev. 2024
  [9] NREL PVWatts v8 — System Losses table (valores por defecto)
  [10] BloombergNEF, Battery Price Survey 2024
       (Turnkey BESS system: ~165–169 USD/kWh; LFP rack stationary: ~125 USD/kWh)
  [11] EPRI, Cost of Storing Energy (2022 Update), Electric Power Research Institute
       (Utility-scale BESS O&M: 2–14 USD/kW/yr; MSA range: 2–6 USD/kW/yr)
  [12] HOMER Energy, HOMER Pro v2.9 User Manual and Default Data, 2023
       (Diesel O&M: 0.02 USD/kWh_generated; inverter O&M default: 5 USD/kW/yr)

Estado de cada parámetro:
  ✓  Confirmado con datasheet / fuente primaria
  ~  Derivado / calculado a partir de datos del datasheet
  ?  Pendiente de completar con fuente indicada
============================================================================="""

# ===========================================================================
# 0. EMPLAZAMIENTO  [Fuente: 7 — cabecera archivo EPW]
# ===========================================================================
SITE = {
    "lat_deg":          4.240,    # [°N]  Latitud del emplazamiento               ✓
    "lon_deg":         -73.780,   # [°E]  Longitud del emplazamiento               ✓
    "alt_m":            2548,     # [m]   Altitud sobre el nivel del mar           ✓
    "timezone_UTC":    -5,        # [h]   Huso horario Colombia (UTC-5)            ✓
    "_descripcion":     "Zona andina rural, Cundinamarca/Meta, Colombia",
    "_fuente":          "[7] Cabecera TMY EPW — ECMWF/ERA5 vía PVGIS",
}


# ===========================================================================
# 1. CAMPO FOTOVOLTAICO — JA Solar JAM72S30-565/GR  [Fuente: 1]
# ===========================================================================
PV = {
    # --- Características eléctricas a STC (1000 W/m², 25°C, AM 1.5) ---
    "P_nom_W":          565,      # [W]   Potencia pico nominal del módulo        ✓
    "P_mod_kWp":        0.565,    # [kWp] Potencia pico nominal unitaria          ✓
    "eta_stc":          0.219,    # [-]   Eficiencia a STC (21,9 %)               ✓
    "gamma_P":         -0.00350,  # [1/°C] Coef. temperatura Pmax (-0,350 %/°C)   ✓

    # --- Degradación ---
    "deg_year1":        0.020,    # [-]   Caída año 1 (100 % → 98 %)             ✓
    "deg_annual":       0.0055,   # [1/año] Degradación lineal años 2–25          ✓
    # Nota: P(t) = P_nom*(1-deg_year1)*(1-deg_annual)^(t-1), t en años

    # --- Geometría de instalación (ver Anexo A, Sección A.2.4)
    # Emplazamiento: lat=4,24°N → hemisferio Norte → azimut sur (180° conv. norte=0°)
    # Inclinación: se adopta β = 10,0° siguiendo el criterio constructivo de la UPME (2003) y DNP (2024)
    # para autolimpieza y prevención de estancamiento de agua en latitudes < 10° (ver Anexo A.2.4)
    "tilt_deg":         10.0,     # [°]   Inclinación de diseño UPME/DNP          ~ [Anexo A.2.4]
    "azimuth_deg":      180.0,    # [°]   Azimut (conv. norte=0°, sur=180°)       ~ [Anexo A.2.4]

    # ---------------------------------------------------------------------------
    # Pérdidas del sistema — desglose estilo SAM/PVWatts  [Fuente: 9]
    # Factor total: derate = (1-f_soiling)*(1-f_mismatch)*(1-f_wiring_dc)*
    #               (1-f_connections)*(1-f_LID)*(1-f_nameplate)*(1-f_availability)
    # ---------------------------------------------------------------------------
    "f_soiling":        0.020,    # [-]   Suciedad — tropical, est. húmeda        ~ [SOLARGIS]
    "f_mismatch":       0.020,    # [-]   Desajuste eléctrico entre módulos        ~ [SAM default]
    "f_wiring_dc":      0.020,    # [-]   Pérdidas resistivas cableado DC          ~ [IEC 62446]
    "f_connections":    0.005,    # [-]   Pérdidas en conectores y terminales      ~ [SAM default]
    "f_LID":            0.015,    # [-]   Degradación inducida por luz (LID)       ~ [SAM default]
    "f_nameplate":      0.010,    # [-]   Tolerancia de potencia de nameplate      ~ [SAM default]
    "f_availability":   0.030,    # [-]   Indisponibilidad por mantenimiento       ~ [SAM default]
    # Sumatoria cuasi-lineal: ≈ 12,0 % pérdidas del sistema (factor derate ≈ 0,880)
    # SAM v2024 default total losses: ~14 %; aquí se adoptan valores para clima tropical.

    # --- Referencia ---
    "_modelo":          "JA Solar JAM72S30-565/GR",
    "_fuente":          "[1] Datasheet JAM72S30-565/GR rev. 2024 | [9] NREL PVWatts v8",
}


def pv_power_factor(t: int) -> float:
    """
    Factor de potencia relativa del módulo en el año t (t=0: año instalación).
    Año 0 → 1.0; Año 1 → (1-deg_year1); Año t≥2 → (1-deg_year1)*(1-deg_annual)^(t-1)
    """
    if t == 0:
        return 1.0
    return (1 - PV["deg_year1"]) * (1 - PV["deg_annual"]) ** (t - 1)


def pv_derate_factor() -> float:
    """
    Factor de derating global del sistema PV (excluye degradación y temperatura).
    Combina todos los factores de pérdida estilo SAM multiplicativamente.
    Retorna: derate [-] = producto de (1 - f_i) para cada pérdida i.
    """
    losses = [
        PV["f_soiling"],
        PV["f_mismatch"],
        PV["f_wiring_dc"],
        PV["f_connections"],
        PV["f_LID"],
        PV["f_nameplate"],
        PV["f_availability"],
    ]
    derate = 1.0
    for f in losses:
        derate *= (1.0 - f)
    return derate


def pv_array_power_kWp(N: int) -> float:
    """Potencia total del campo FV para N módulos JA Solar de 565 W."""
    return N * PV["P_mod_kWp"]



# ===========================================================================
# 2. SISTEMA DE ALMACENAMIENTO (BESS) — Victron LFP-51.2/100  [Fuente: 2]
# ===========================================================================
BESS = {
    # --- Módulo unitario ---
    "V_nom_V":          51.2,     # [V]   Tensión nominal del módulo              ✓
    "C_nom_Ah":         100.0,    # [Ah]  Capacidad nominal a 25 °C               ✓
    "E_mod_kWh":        5.12,     # [kWh] Energía por módulo (51.2V × 100Ah)     ~

    # --- Eficiencia ---
    "RTE":              0.92,     # [-]   Round-trip efficiency (92 %)            ✓
    # Raíz aplicada simétricamente: eta_c = eta_d = sqrt(RTE) ≈ 0.959

    # --- Límites operacionales ---
    "SoC_min":          0.20,     # [-]   SoC mínimo operacional (20 %)          ~ [DoD 80% → ciclos]
    "SoC_max":          0.95,     # [-]   SoC máximo operacional (95 %)          ~ [margen BMS]
    "DoD_max":          0.80,     # [-]   Profundidad de descarga máxima          ~

    # --- Límites de tensión de celda (BMS hardware) ---
    "V_cell_min_V":     2.80,     # [V/célula] Corte mínimo de descarga BMS      ✓
    "V_cell_max_V":     3.60,     # [V/célula] Corte máximo de carga BMS         ✓
    "n_cells_series":   16,       # [-]   Células en serie (16 × 3.2V = 51.2V)   ~

    # --- Tasa C ---
    "C_rate_max_charge":    1.0,  # [1/h] Tasa C máxima de carga (1C = 100A)     ✓
    "C_rate_max_discharge": 1.0,  # [1/h] Tasa C máxima de descarga (1C = 100A) ✓
    # P_max_kW por módulo = C_rate × E_mod_kWh = 1.0 × 5.12 = 5.12 kW

    # --- Degradación / vida útil (curva fabricante) ---
    "cycles_at_DoD80":  2500,     # [ciclos] Vida útil al 80% DoD → ~6.8 años    ✓
    "cycles_at_DoD70":  3000,     # [ciclos] Vida útil al 70% DoD → ~8.2 años    ✓
    "cycles_at_DoD50":  5000,     # [ciclos] Vida útil al 50% DoD → ~13.7 años   ✓
    "capacity_EOL":     0.80,     # [-]   Capacidad mínima al fin de vida (80%)  ✓

    # --- Banco (N módulos en paralelo — variable de diseño) ---
    # E_banco_kWh = N_modulos × E_mod_kWh
    # P_max_banco_kW = N_modulos × C_rate_max × E_mod_kWh
    "N_modulos":        None,     # [-]   Variable de diseño (barrido param.)     ?

    # --- Condición inicial de simulación ---
    "SoC_0":            0.50,     # [-]   SoC inicial (50%, se verifica periodicidad) ~

    # --- Referencia ---
    "_modelo":          "Victron Energy LFP-51.2/100",
    "_fuente":          "[2] Datasheet Victron LFP-51.2/100 rev. 2024",
}

def bess_bank_energy_kWh(N: int) -> float:
    """Energía total del banco para N módulos en paralelo."""
    return N * BESS["E_mod_kWh"]

def bess_bank_power_kW(N: int) -> float:
    """Potencia máxima continua del banco para N módulos en paralelo."""
    return N * BESS["C_rate_max_discharge"] * BESS["E_mod_kWh"]

def bess_replacement_year(DoD: float = 0.80, cycles_per_year: float = 365.0) -> float:
    """
    Estima el año de reemplazo del banco según el DoD operacional medio.
    DoD: profundidad de descarga media (0.50, 0.70 u 0.80)
    cycles_per_year: ciclos equivalentes anuales (~365 por defecto)
    """
    cycle_map = {0.80: 2500, 0.70: 3000, 0.50: 5000}
    total_cycles = cycle_map.get(DoD, 2500)
    return total_cycles / cycles_per_year


# ===========================================================================
# 3. GENERADOR DIÉSEL  [Fuentes: Nair2026, IPCC2006Vol2]
# ===========================================================================
DIESEL = {
    "P_nom_kW":         15.0,     # [kW]  Potencia nominal (escenario base)       ✓ [Cap. 7]
    "P_min_pu":         0.30,     # [-]   Carga mínima operacional (30% P_nom)    ✓ [estándar]

    # Curva de consumo lineal: FC [L/h] = a * P_nom + b * P_gen
    # Coeficientes estándar de la literatura para GD de pequeña-mediana potencia.
    # Empleados en optimización de microredes híbridas aisladas [Nair2026].
    "fc_a":             0.08,     # [L/(h·kW)] Consumo en vacío (no-load)         ~ [Nair2026]
    "fc_b":             0.25,     # [L/(h·kW)] Consumo variable (a plena carga)   ~ [Nair2026]

    "eff_diesel_kWh_L": 3.40,     # [kWh/L] Eficiencia conversión diésel→elec.   ✓ [Cap. 7]
    "ef_CO2_kg_L":      2.68,     # [kgCO2/L] Factor emisión IPCC 2006 Vol.2 Ch.2 ✓ [IPCC2006Vol2]
    # Derivado de: 74.1 tCO2/TJ × 36.9 MJ/L (PCI gasoil) = 2.734 → IPCC redondea a 2.68 kg/L

    # --- Referencia ---
    "_modelo":          "Generador diésel 15 kW (modelo a definir)",
    "_fuente":          "Coeficientes fc_a/fc_b: [Nair2026] arXiv:2604.06371. "
                        "Factor emision CO2: [IPCC2006Vol2] IPCC 2006 GL Vol.2 Ch.2 Tab.2.2.",
}


# ===========================================================================
# 4. INVERSOR / PCS — Victron Quattro 48V  [Fuente: 8]
# ===========================================================================
INV = {
    # --- Eficiencia  [Fuente: 8 — Victron Quattro 48V datasheet] ---
    "eta_max":          0.96,     # [-]   Eficiencia máxima (96 %)                ✓ [8]
    "eta_sim":          0.94,     # [-]   Eficiencia media operacional para sim.   ~ [conserv.]
    # Nota: Victron no publica curva η(p) normalizada completa. Se adopta η_sim=0,94
    # como valor ponderado conservador respecto al máximo (94 % ≈ η_CEC estimada).
    # Si se dispone de curva de eficiencia, sustituir eta_sim por interpolación eta_curve.

    # Curva normalizada η(p) — a completar si se obtiene de SAM/Sandia DB:
    # p_points  = [0.10, 0.20, 0.30, 0.50, 0.75, 1.00]  (p = P_out/P_nom)
    # eta_points = [0.86, 0.92, 0.94, 0.95, 0.96, 0.95]  (valores típicos 48V string)
    "eta_curve_p":      [0.10, 0.20, 0.30, 0.50, 0.75, 1.00],  # ~ [SAM Sandia 48V]
    "eta_curve_eta":    [0.86, 0.92, 0.94, 0.95, 0.96, 0.95],  # ~ [SAM Sandia 48V]

    # --- Dimensionamiento --- 
    "DC_AC_ratio":      1.20,     # [-]   Ratio DC/AC (1.1–1.3 para alta irrad.)  ~
    # P_nom_kW = P_pv_kWp / DC_AC_ratio  → variable ligada, se calcula en tiempo de ejecución
    "P_nom_kW":         None,     # [kW]  Variable de diseño ligada a P_pv         ~

    # --- Referencia ---
    "_modelo":          "Victron Energy Quattro 48V (o MultiPlus-II 48V según potencia)",
    "_fuente":          "[8] Datasheet Victron Quattro/MultiPlus-II 48V rev. 2024",
}


def inv_eta(p: float) -> float:
    """
    Eficiencia del inversor en función de la fracción de carga p = P_out/P_nom.
    Interpolación lineal sobre la curva normalizada de la familia Victron 48V.
    p: fracción de carga [0, 1]
    Retorna: eficiencia [-]
    """
    import numpy as np
    p_clipped = max(0.0, min(1.0, p))
    return float(np.interp(p_clipped, INV["eta_curve_p"], INV["eta_curve_eta"]))


# ===========================================================================
# 5. PARÁMETROS ECONÓMICOS  [Fuentes: 3, 4, 6, 10, 11, 12 — IRENA/BNEF/NREL/EPRI/HOMER]
# ===========================================================================
ECON = {
    # ---------------------------------------------------------------------------
    # CAPEX (coste total instalado, USD)
    # ---------------------------------------------------------------------------
    # CAPEX PV: 750 USD/kWp (escenario base)
    # Desglose: módulo ~220 USD/kWp + estructura ~100 USD/kWp + BOS+cableado ~70 USD/kWp
    #           + ingeniería+logística ZNI ~200 USD/kWp + instalación ~160 USD/kWp
    # Base: IRENA 2024 media global utility-scale 691 USD/kW → ajuste prima
    #       small-scale (<100 kWp, 800–1.200 USD/kW) + desglose logístico rural.
    # Rango sensibilidad: 500–1.100 USD/kWp
    "capex_pv_USD_kWp":     750.0,  # [USD/kWp]  Módulo+estructura+BOS+logística+instalación [3]

    # CAPEX BESS: 300 USD/kWh (escenario base)
    # Base: BNEF 2024 turnkey BESS system: 165–169 USD/kWh (utility-scale).
    # Prima small-scale (factor ~1,7x): módulo Victron LFP puesto en Colombia
    # incluye IVA+arancel+transporte. NREL ATB 2024 moderate (4h): ~319 USD/kWh.
    # Rango sensibilidad: 200–450 USD/kWh
    "capex_bess_USD_kWh":   300.0,  # [USD/kWh]  Módulo LFP+BMS+instalación DC    ~ [4,10,11]

    # CAPEX inversor/PCS: 200 USD/kW (escenario base)
    # Base: Victron Quattro 48V precio catálogo importado Colombia → ~150–180 USD/kW
    # (hardware) + instalación+BOS eléctrico ~30–50 USD/kW.
    # IRENA rango small-medium (10–100 kW): 80–150 USD/kW (solo hardware mercados
    # desarrollados). HOMER Pro default off-grid inverter: 100–200 USD/kW.
    # Rango sensibilidad: 100–350 USD/kW
    "capex_inv_USD_kW":     200.0,  # [USD/kW]   Inversor bidireccional instalado  ~ [3,8,12]

    # CAPEX generador diésel: 500 USD/kW (escenario base — mantenido)
    # Base: HOMER Pro default + Caterpillar/Cummins distribuidores Colombia.
    # Rango sensibilidad: 400–900 USD/kW (hasta 900 en ZNI con logística extrema)
    "capex_diesel_USD_kW":  500.0,  # [USD/kW]   GD adquisición+instalación        ~ [12]

    # ---------------------------------------------------------------------------
    # OPEX anual (USD/año — referenciado a la magnitud del componente)
    # ---------------------------------------------------------------------------
    # O&M PV: 15 USD/kWp/año (escenario base)
    # Base: IRENA 2024 input LCOE non-OECD: 10,95 USD/kWp/año.
    # Prima por pequeña escala y zona remota (~+4 USD): limpieza mensual,
    # inspección eléctrica semestral, termografía anual, seguros menores.
    # Rango sensibilidad: 8–25 USD/kWp/año
    "opex_pv_USD_kWp_yr":   15.0,   # [USD/kWp/año] Limpieza+inspección+seguros    ~ [3]

    # O&M BESS: 5 USD/kWh/año (escenario base)
    # Base: EPRI 2022 utility-scale BESS MSA: 2–6 USD/kW/año.
    # Convertido a USD/kWh: 6 USD/kW/yr ÷ 4h ≈ 1,5 USD/kWh/yr (utility-scale 4h).
    # Factor small-scale off-grid (~3x): inspección BMS manual, limpieza,
    # calibración sensores, reemplazo fusibles/conectores, desplazamiento técnico.
    # NREL ATB 2024: FOM = 4% CAPEX/kW/yr → ~12 USD/kW/yr → ~3 USD/kWh/yr (4h).
    # Rango sensibilidad: 2–10 USD/kWh/año
    "opex_bess_USD_kWh_yr": 5.0,    # [USD/kWh/año] Mantenimiento BMS+revisión     ~ [4,11]

    # O&M inversor: 5 USD/kW/año (escenario base)
    # Base: HOMER Pro default off-grid inverter: 5 USD/kW/yr.
    # Victron Quattro (~10 kW/unidad): mantenimiento preventivo ~200 USD/año/unidad
    # + correctivo amortizado ~150 USD/año → para 15–30 kW instalados: ~5–7 USD/kW/yr.
    # Rango sensibilidad: 3–15 USD/kW/año
    "opex_inv_USD_kW_yr":   5.0,    # [USD/kW/año]  Preventivo+correctivo Victron  ~ [8,12]

    # O&M diésel: 0,40 USD/h de operación (escenario base)
    # Base: regla HOMER Pro «0,02 USD/kWh_generado» (estándar industria).
    #   Para GD 15 kW: 0,02 × 15 = 0,30 USD/h (operación a plena carga)
    #   Factor logístico ZNI Colombia (×1,30): transporte repuestos, técnico in situ
    #   → 0,30 × 1,30 ≈ 0,39 → redondeado a 0,40 USD/h
    # NOTA: Este valor es INDEPENDIENTE del coste de combustible (calculado aparte).
    # Incluye: cambios de aceite, filtros, correas, revisiones programadas.
    # Rango sensibilidad: 0,25–0,70 USD/h (según accesibilidad del sitio)
    "opex_diesel_USD_h":    0.40,   # [USD/h_op]    O&M GD (sin combustible)        ~ [12]

    # ---------------------------------------------------------------------------
    # Combustible
    # ---------------------------------------------------------------------------
    "diesel_price_USD_L":   1.30,   # [USD/L] Precio diésel puesto en sitio      ✓ [Cap. 7 / GlobalPetrolPrices]
    # Rango análisis sensibilidad: 0.60 – 2.50 USD/L
    # (incluye sobrecoste de transporte fluvial/terrestre a ZNI)

    # ---------------------------------------------------------------------------
    # Parámetros financieros
    # ---------------------------------------------------------------------------
    "WACC":             0.10,       # [-]   Tasa de descuento real (10 %)         ✓ [Cap. 4]
    "T_years":          25,         # [años] Horizonte de vida del proyecto        ✓ [Cap. 4]
    "residual_value":   0.0,        # [-]   Valor residual al año 25 (conserv.)   ~

    # ---------------------------------------------------------------------------
    # Vida útil de componentes → determina años de reemplazo
    # ---------------------------------------------------------------------------
    # Criterio: reemplazo al MISMO CAPEX (enfoque conservador).
    # El reemplazo ocurre al inicio del año indicado (flujo de caja negativo).
    # Si vida_util >= T_years, NO hay reemplazo dentro del horizonte.
    #
    # BESS: vida útil extraída de bess_replacement_year(DoD) → ~6,8 años (DoD 80%)
    #       Se modelan reemplazos sucesivos cada ~7 años dentro de 25 años.
    #       Valor paramétrico ajustable según DoD operacional real de la simulación.
    "lifetime_bess_yr":     7,      # [años] Vida útil BESS (DoD≈80%)  → reemplazos años 7, 14, 21 ~ [BESS.cycles]

    # Inversor/PCS: vida útil estándar Victron Quattro = 10–15 años (garantía 5 años).
    # Se adopta 12 años como valor central conservador → reemplazo en año 12.
    "lifetime_inv_yr":      12,     # [años] Vida útil inversor          → reemplazo año 12          ~ [8]

    # Generador diésel: vida útil con mantenimiento correcto = 15–20 años.
    # Se adopta 15 años → posible reemplazo en año 15 (al límite del horizonte).
    # Si se opera pocas horas/año (respaldo puntual), puede superar los 25 años.
    "lifetime_diesel_yr":   20,     # [años] Vida útil GD               → reemplazo año 20          ~ [12]

    # Módulos PV: garantía de potencia 25–30 años → sin reemplazo en horizonte de 25 años.
    # (la degradación ya está modelada en PV.deg_annual)
    # "lifetime_pv_yr":    25,      # no aplica: sin reemplazo

    # --- Referencia ---
    "_fuente":          "[3] IRENA 2024 (global PV 691 USD/kW; small-scale 800–1200 USD/kW; non-OECD O&M 10.95 USD/kWp/yr). "
                        "[10] BNEF Battery Survey 2024 (turnkey 165–169 USD/kWh). "
                        "[4] NREL ATB 2024 (4h BESS moderate ~319 USD/kWh; FOM 4% CAPEX). "
                        "[11] EPRI 2022 (BESS MSA: 2–6 USD/kW/yr). "
                        "[12] HOMER Pro v2.9 (diesel O&M: 0.02 USD/kWh; inv. default: 5 USD/kW/yr).",
}



def replacement_cashflows(
    E_bess_kWh: float,
    P_inv_kW:   float,
    P_diesel_kW: float,
) -> dict:
    """
    Devuelve los flujos de caja negativos por reemplazo de componentes
    durante el horizonte de vida del proyecto.

    Hipótesis: reemplazo al MISMO CAPEX unitario que la instalación inicial.
    El coste se aplica en el año de inicio del nuevo ciclo de vida.

    Parámetros
    ----------
    E_bess_kWh   : energía total del banco BESS [kWh]
    P_inv_kW     : potencia nominal del inversor [kW]
    P_diesel_kW  : potencia nominal del generador diésel [kW]

    Retorna
    -------
    dict con claves = año (int), valor = coste de reemplazo total ese año [USD]
    (valor positivo → desembolso; se resta al flujo de caja neto)

    Ejemplo de uso en el cálculo del NPV:
        flows = replacement_cashflows(E_bess, P_inv, P_diesel)
        for yr, cost in flows.items():
            npv -= cost / (1 + ECON["WACC"]) ** yr
    """
    T      = ECON["T_years"]
    cashflows: dict[int, float] = {}

    def _add(yr: int, cost: float) -> None:
        """Acumula coste en el año yr si yr < T (no reemplazar en el año de fin)."""
        if 0 < yr < T:
            cashflows[yr] = cashflows.get(yr, 0.0) + cost

    # --- BESS: reemplazos cada lifetime_bess_yr años ---
    life_bess  = ECON["lifetime_bess_yr"]
    cost_bess  = E_bess_kWh * ECON["capex_bess_USD_kWh"]
    yr = life_bess
    while yr < T:
        _add(yr, cost_bess)
        yr += life_bess

    # --- Inversor: un reemplazo en lifetime_inv_yr ---
    life_inv  = ECON["lifetime_inv_yr"]
    cost_inv  = P_inv_kW * ECON["capex_inv_USD_kW"]
    _add(life_inv, cost_inv)

    # --- Generador diésel: un reemplazo en lifetime_diesel_yr ---
    life_diesel = ECON["lifetime_diesel_yr"]
    cost_diesel = P_diesel_kW * ECON["capex_diesel_USD_kW"]
    _add(life_diesel, cost_diesel)

    return cashflows


# ===========================================================================
# 6. PARÁMETROS GLOBALES DEL SISTEMA
# ===========================================================================
SYS = {
    # --- Arquitectura ---
    "V_bus_DC_V":       48.0,     # [V]   Tensión bus DC nominal                  ✓
    "f_grid_Hz":        60.0,     # [Hz]  Frecuencia de red (Colombia)             ✓

    # --- Simulación ---
    "dt_h":             1.0,      # [h]   Paso temporal de simulación (horario)   ✓
    "N_hours":          8760,     # [h]   Horas por año (TMY)                     ✓

    # --- Restricción de fiabilidad ---
    "LPSP_max":         0.05,     # [-]   LPSP máxima admisible (5 %)             ~ [convención]

    # --- Espacio de búsqueda del barrido paramétrico (a definir) ---
    "P_pv_range_kWp":   None,     # [kWp] Rango [min, max, paso] campo PV         ?
    "N_bess_range":     None,     # [-]   Rango [min, max] módulos BESS            ?
}


# ===========================================================================
# RESUMEN DE ESTADO
# ===========================================================================
STATUS = {
    "confirmados_datasheet": [
        "SITE.lat_deg", "SITE.lon_deg", "SITE.alt_m", "SITE.timezone_UTC",
        "PV.P_nom_W", "PV.eta_stc", "PV.gamma_P",
        "PV.deg_year1", "PV.deg_annual",
        "INV.eta_max",
        "BESS.V_nom_V", "BESS.C_nom_Ah", "BESS.RTE",
        "BESS.C_rate_max_charge", "BESS.C_rate_max_discharge",
        "BESS.V_cell_min_V", "BESS.V_cell_max_V",
        "BESS.cycles_at_DoD80", "BESS.cycles_at_DoD70", "BESS.cycles_at_DoD50",
        "DIESEL.P_nom_kW", "DIESEL.P_min_pu",
        "DIESEL.eff_diesel_kWh_L", "DIESEL.ef_CO2_kg_L",
        "ECON.diesel_price_USD_L", "ECON.WACC", "ECON.T_years",
    ],
    "derivados": [
        "PV.tilt_deg", "PV.azimuth_deg",
        "PV.f_soiling", "PV.f_mismatch", "PV.f_wiring_dc",
        "PV.f_connections", "PV.f_LID", "PV.f_nameplate", "PV.f_availability",
        "INV.eta_sim", "INV.eta_curve_p", "INV.eta_curve_eta", "INV.DC_AC_ratio",
        "BESS.E_mod_kWh", "BESS.SoC_min", "BESS.SoC_max", "BESS.DoD_max",
        "BESS.n_cells_series",
        # Parámetros económicos — derivados de fuentes primarias (IRENA/BNEF/NREL/EPRI/HOMER)
        "ECON.capex_pv_USD_kWp",     # 750 USD/kWp  [IRENA 2024 + prima small-scale Colombia]
        "ECON.capex_bess_USD_kWh",   # 300 USD/kWh  [BNEF 2024 + NREL ATB 2024]
        "ECON.capex_inv_USD_kW",     # 200 USD/kW   [Victron catálogo + IRENA]
        "ECON.capex_diesel_USD_kW",  # 500 USD/kW   [HOMER Pro + Caterpillar]
        "ECON.opex_pv_USD_kWp_yr",   # 15 USD/kWp/yr [IRENA 2024 non-OECD]
        "ECON.opex_bess_USD_kWh_yr", # 5 USD/kWh/yr [EPRI 2022 + NREL ATB 2024]
        "ECON.opex_inv_USD_kW_yr",   # 5 USD/kW/yr  [HOMER Pro + Victron]
        "ECON.opex_diesel_USD_h",    # 0.40 USD/h   [HOMER Pro 0.02 USD/kWh × factor ZNI]
        # Vidas útiles → años de reemplazo al mismo CAPEX
        "ECON.lifetime_bess_yr",     # 7 años  → reemplazos años 7, 14, 21
        "ECON.lifetime_inv_yr",      # 12 años → reemplazo año 12
        "ECON.lifetime_diesel_yr",   # 20 años → reemplazo año 20
        "DIESEL.fc_a", "DIESEL.fc_b",   # coeficientes estándar literatura [Nair2026]
    ],
    "pendientes": [
        "SYS.P_pv_range_kWp",                   # → A definir en optimización
        "SYS.N_bess_range",                     # → A definir en optimización
    ],
}


if __name__ == "__main__":
    import numpy as np

    confirmados = len(STATUS["confirmados_datasheet"])
    derivados   = len(STATUS["derivados"])
    pendientes  = len(STATUS["pendientes"])
    total       = confirmados + derivados + pendientes

    print("=" * 55)
    print("  ESTADO DE PARÁMETROS — params.py")
    print("=" * 55)
    print(f"  Confirmados (datasheet/fuente): {confirmados:>3}/{total}")
    print(f"  Derivados (calculados):         {derivados:>3}/{total}")
    print(f"  Pendientes:                     {pendientes:>3}/{total}")
    print()
    print("  EMPLAZAMIENTO")
    print(f"    Lat: {SITE['lat_deg']}°N  |  Lon: {SITE['lon_deg']}°E  "
          f"|  Alt: {SITE['alt_m']} m")
    print()
    print("  GEOMETRIA OPTIMA PV")
    print(f"    Inclinacion (beta_opt) : {PV['tilt_deg']} grados")
    print(f"    Azimut (N=0, sur=180)  : {PV['azimuth_deg']} grados")
    print()
    print("  PÉRDIDAS PV (desglose SAM-style)")
    losses_labels = [
        ("Suciedad",        PV["f_soiling"]),
        ("Mismatch",        PV["f_mismatch"]),
        ("Cableado DC",     PV["f_wiring_dc"]),
        ("Conexiones",      PV["f_connections"]),
        ("LID",             PV["f_LID"]),
        ("Nameplate",       PV["f_nameplate"]),
        ("Disponibilidad",  PV["f_availability"]),
    ]
    total_loss = 0.0
    for label, val in losses_labels:
        print(f"    {label:<18}: {val*100:.1f} %")
        total_loss += val
    derate = pv_derate_factor()
    print(f"    {'-'*30}")
    print(f"    Factor derate total  : {derate:.4f}  ({(1-derate)*100:.1f} % pérdidas)")
    print()
    print("  INVERSOR - Victron Quattro 48V")
    print(f"    eta_max: {INV['eta_max']*100:.0f} %")
    print(f"    eta_sim: {INV['eta_sim']*100:.0f} % (valor simulacion)")
    print(f"    eta(p=0.50): {inv_eta(0.50)*100:.1f} %")
    print(f"    eta(p=1.00): {inv_eta(1.00)*100:.1f} %")
    print()
    print("  BESS — Victron LFP-51.2/100")
    print(f"    Reemplazo (DoD 80%): año {bess_replacement_year(0.80):.1f}")
    print(f"    Reemplazo (DoD 50%): año {bess_replacement_year(0.50):.1f}")
    print()
    print("  DEGRADACIÓN PV")
    print(f"    Factor potencia año  1: {pv_power_factor(1):.4f}")
    print(f"    Factor potencia año 10: {pv_power_factor(10):.4f}")
    print(f"    Factor potencia año 25: {pv_power_factor(25):.4f}")
    print()
    print("  REEMPLAZOS DE COMPONENTES (ejemplo: 4xBESS=20.48 kWh | Inv=10 kW | GD=15 kW)")
    print(f"    Vida util BESS   : {ECON['lifetime_bess_yr']} anyos  -> reemplazos en anyos: "
          + str(list(range(ECON['lifetime_bess_yr'], ECON['T_years'], ECON['lifetime_bess_yr']))))
    print(f"    Vida util Inv.   : {ECON['lifetime_inv_yr']} anyos -> reemplazo en anyo {ECON['lifetime_inv_yr']}")
    print(f"    Vida util Diesel : {ECON['lifetime_diesel_yr']} anyos -> reemplazo en anyo {ECON['lifetime_diesel_yr']}")
    print()
    # Ejemplo con 4 módulos BESS (4 × 5,12 kWh = 20,48 kWh), 10 kW inv, 15 kW diesel
    _E_bess  = 4 * BESS["E_mod_kWh"]          # 20,48 kWh
    _P_inv   = 10.0                             # kW (ejemplo)
    _P_dsl   = DIESEL["P_nom_kW"]              # 15 kW
    flows = replacement_cashflows(_E_bess, _P_inv, _P_dsl)
    print(f"    {'Año':<6} {'Coste reemplazo [USD]':>22}  {'Componentes'}") 
    print(f"    {'-'*52}")
    _comp_labels = {
        ECON["lifetime_bess_yr"]:   "BESS",
        ECON["lifetime_inv_yr"]:    "Inv",
        ECON["lifetime_diesel_yr"]: "Diesel",
        ECON["lifetime_bess_yr"]*2: "BESS×2",
        ECON["lifetime_bess_yr"]*3: "BESS×3",
    }
    wacc = ECON["WACC"]
    total_npv_repl = 0.0
    for yr in sorted(flows.keys()):
        cost = flows[yr]
        pv   = cost / (1 + wacc) ** yr
        total_npv_repl += pv
        label = _comp_labels.get(yr, "varios")
        print(f"    {yr:<6} {cost:>22,.0f}  [{label}]  VAN={pv:,.0f} USD")
    print(f"    {'-'*52}")
    print(f"    {'VAN total reemplazos':.<28}: {total_npv_repl:,.0f} USD")
    print("=" * 55)
