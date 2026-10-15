"""
=============================================================================
analisis_sensibilidad.py — Evaluación Financiera y Sensibilidad (OE3 & OE4)
=============================================================================
Realiza la evaluación financiera detallada a 25 años para el escenario
óptimo P1 (45 módulos = 25.425 kWp PV + 61.44 kWh BESS = 12 módulos Victron) y el análisis
de sensibilidad sobre las variables críticas:
  - Precio del diésel: [0.60, 2.50] USD/L
  - CAPEX BESS: [200, 450] USD/kWh
  - CAPEX PV: [500, 1100] USD/kWp
  - Tasa WACC: [6%, 14%]

Genera:
  1. Tablas CSV:
     - flujos_caja_25anos_P1.csv
     - resumen_sensibilidad_tornado.csv
  2. Figuras PNG en alta resolución (figuras/):
     - flujos_caja_acumulados_P1.png
     - sensibilidad_tornado.png
     - sensibilidad_cruzada_diesel_bess.png
=============================================================================
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

# Importar simulador y parámetros
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)
from despacho_pysam import MicrogridSimulator
import params

PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
FIG_DIR = os.path.join(PROJECT_ROOT, 'figuras')
os.makedirs(FIG_DIR, exist_ok=True)


def calculate_irr(cash_flows, guess=0.10):
    """Calcula la Tasa Interna de Retorno (TIR) numérica."""
    try:
        import numpy_financial as npf
        return npf.irr(cash_flows)
    except ImportError:
        # Resolver con scipy
        from scipy.optimize import root_scalar
        def npv_f(r):
            return sum(cf / ((1.0 + r) ** i) for i, cf in enumerate(cash_flows))
        res = root_scalar(npv_f, bracket=[-0.5, 2.0], method='brentq')
        return res.root if res.converged else np.nan


def run_financial_and_sensitivity_analysis():
    print("==========================================================================")
    print("   EVALUACIÓN FINANCIERA DETALLADA Y ANÁLISIS DE SENSIBILIDAD (OE3 & OE4)")
    print("==========================================================================")

    sim = MicrogridSimulator()

    # Cargar escenario óptimo P1 (determinado en el barrido: 45 módulos JA Solar = 25.425 kWp, 12 módulos BESS = 61.44 kWh)
    P_pv_p1 = round(45 * params.PV["P_mod_kWp"], 3)  # 25.425 kWp
    N_bess_p1 = 12
    res_p1 = sim.simular_despacho(P_pv_kw=P_pv_p1, N_bess=N_bess_p1, estrategia='LF')

    # --------------------------------------------------------------------------
    # 1. Tabla Anual de Flujos de Caja a 25 Años
    # --------------------------------------------------------------------------
    T = params.ECON["T_years"]  # 25
    wacc = params.ECON["WACC"]  # 0.10
    delta_capex = res_p1['delta_capex_USD']
    delta_opex_base = res_p1['delta_opex_annual_USD']

    base_capex = params.DIESEL["P_nom_kW"] * params.ECON["capex_diesel_USD_kW"]  # 7500 USD
    base_opex = res_p1['base_opex_annual_USD']  # 29983.92 USD
    base_repl_flows = {params.ECON["lifetime_diesel_yr"]: base_capex}

    hybrid_capex = res_p1['total_capex_USD']  # 49238.25 USD
    hybrid_opex = res_p1['opex_annual_USD']  # 1776.77 USD
    repl_hybrid_flows = params.replacement_cashflows(res_p1['E_bess_kwh'], P_pv_p1 / params.INV["DC_AC_ratio"], params.DIESEL["P_nom_kW"])

    cash_flow_table = []
    cf_vector_for_irr = [-delta_capex]  # Año 0
    cum_simple = -delta_capex
    cum_disc = -delta_capex

    cum_diesel_simple = -base_capex
    cum_diesel_disc = -base_capex

    cum_hybrid_simple = -hybrid_capex
    cum_hybrid_disc = -hybrid_capex

    # Fila Año 0
    cash_flow_table.append({
        'Ano': 0,
        'Flujo_Diesel_Neto_USD': -base_capex,
        'Flujo_Diesel_Acum_Simple_USD': cum_diesel_simple,
        'Flujo_Diesel_Acum_Disc_USD': cum_diesel_disc,
        'Flujo_Hibrido_Neto_USD': -hybrid_capex,
        'Flujo_Hibrido_Acum_Simple_USD': cum_hybrid_simple,
        'Flujo_Hibrido_Acum_Disc_USD': cum_hybrid_disc,
        'Inversion_Inicial_USD': -delta_capex,
        'Ahorro_OPEX_USD': 0.0,
        'Reemplazo_Hibrido_USD': 0.0,
        'Reemplazo_Base_USD': 0.0,
        'Flujo_Neto_USD': -delta_capex,
        'Flujo_Descontado_USD': -delta_capex,
        'Flujo_Acumulado_Simple_USD': cum_simple,
        'Flujo_Acumulado_Descontado_USD': cum_disc,
    })

    for y in range(1, T + 1):
        repl_h = repl_hybrid_flows.get(y, 0.0)
        repl_b = base_repl_flows.get(y, 0.0)

        # Diésel puro
        flujo_diesel_neto = -base_opex - repl_b
        flujo_diesel_disc = flujo_diesel_neto / ((1.0 + wacc) ** y)
        cum_diesel_simple += flujo_diesel_neto
        cum_diesel_disc += flujo_diesel_disc

        # Híbrido puro
        flujo_hybrid_neto = -hybrid_opex - repl_h
        flujo_hybrid_disc = flujo_hybrid_neto / ((1.0 + wacc) ** y)
        cum_hybrid_simple += flujo_hybrid_neto
        cum_hybrid_disc += flujo_hybrid_disc

        # Diferencial (Incremental)
        flujo_neto = delta_opex_base - repl_h + repl_b
        flujo_disc = flujo_neto / ((1.0 + wacc) ** y)
        cum_simple += flujo_neto
        cum_disc += flujo_disc
        cf_vector_for_irr.append(flujo_neto)

        cash_flow_table.append({
            'Ano': y,
            'Flujo_Diesel_Neto_USD': flujo_diesel_neto,
            'Flujo_Diesel_Acum_Simple_USD': cum_diesel_simple,
            'Flujo_Diesel_Acum_Disc_USD': cum_diesel_disc,
            'Flujo_Hibrido_Neto_USD': flujo_hybrid_neto,
            'Flujo_Hibrido_Acum_Simple_USD': cum_hybrid_simple,
            'Flujo_Hibrido_Acum_Disc_USD': cum_hybrid_disc,
            'Inversion_Inicial_USD': 0.0,
            'Ahorro_OPEX_USD': delta_opex_base,
            'Reemplazo_Hibrido_USD': -repl_h,
            'Reemplazo_Base_USD': repl_b,
            'Flujo_Neto_USD': flujo_neto,
            'Flujo_Descontado_USD': flujo_disc,
            'Flujo_Acumulado_Simple_USD': cum_simple,
            'Flujo_Acumulado_Descontado_USD': cum_disc,
        })

    df_cf = pd.DataFrame(cash_flow_table)
    csv_cf = os.path.join(SCRIPT_DIR, 'flujos_caja_25anos_P1.csv')
    df_cf.to_csv(csv_cf, index=False)
    print(f"\n[DATOS GUARDADOS] Tabla de flujos de caja a 25 años exportada a:\n  {csv_cf}")

    # Calcular TIR
    tir = calculate_irr(cf_vector_for_irr)

    print("\n--- RESUMEN FINANCIERO ESCENARIO P1 vs 100% DIÉSEL ---")
    print(f"  Inversión Inicial Adicional (Delta CAPEX): {delta_capex:,.2f} USD")
    print(f"  Ahorro Operativo Anual (Delta OPEX):       {delta_opex_base:,.2f} USD/año")
    print(f"  Valor Actual Neto (VAN a 25 años, 10%):     {res_p1['van_USD']:,.2f} USD")
    print(f"  Tasa Interna de Retorno (TIR):             {tir * 100:.2f} %")
    print(f"  Payback Simple:                            {res_p1['payback_simple_years']:.2f} años")
    print(f"  Payback Descontado (al 10% WACC):          {res_p1['payback_discounted_years']:.2f} años")
    print(f"  LCOE P1:                                   {res_p1['lcoe_USD_kwh']:.4f} USD/kWh (vs Base: {res_p1['base_lcoe_USD_kwh']:.4f} USD/kWh)")

    # --------------------------------------------------------------------------
    # 2. Gráfica de Flujos de Caja Acumulados (Payback de P1)
    # --------------------------------------------------------------------------
    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(8.2, 4.3))

    ax.plot(df_cf['Ano'], df_cf['Flujo_Acumulado_Simple_USD'] / 1000.0, marker='o', markersize=5.5,
            color='#1f77b4', linewidth=2.4, label=f'Flujo Incremental Simple (Payback = {res_p1["payback_simple_years"]:.2f} años)')
    ax.plot(df_cf['Ano'], df_cf['Flujo_Acumulado_Descontado_USD'] / 1000.0, marker='s', markersize=5.5,
            color='#2ca02c', linewidth=2.4, label=f'Flujo Incremental Descontado (Payback = {res_p1["payback_discounted_years"]:.2f} años)')
    ax.axhline(0, color='#d32f2f', linestyle='--', linewidth=1.5, alpha=0.85, label='Umbral de Amortización (Net Zero)')

    for yr in [7, 12, 14, 20, 21]:
        ax.axvline(yr, color='#757575', linestyle=':', alpha=0.6)
        ax.text(yr, -36, f"Año {yr}", rotation=90, fontsize=9.5, fontweight='bold', color='#424242', ha='right')

    ax.set_title("Recuperación de la Inversión (Payback) y Curva de Flujos de Caja - P1", fontsize=12.5, fontweight='bold')
    ax.set_xlabel("Año del Proyecto (Horizonte 25 años)", fontsize=11.5, fontweight='bold')
    ax.set_ylabel("Flujo Neto Incremental (Miles de USD)", fontsize=11.5, fontweight='bold')
    ax.set_xlim(0, 25)
    ax.set_xticks(range(0, 26, 2))
    ax.tick_params(axis='both', which='major', labelsize=10.5)
    ax.legend(loc='upper left', frameon=True, fontsize=10.5)

    plt.tight_layout()
    fig_cf = os.path.join(FIG_DIR, 'flujos_caja_acumulados_P1.png')
    plt.savefig(fig_cf, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"[FIGURA GENERADA] Curva de Payback guardada en:\n  {fig_cf}")

    # --------------------------------------------------------------------------
    # 3. Análisis de Sensibilidad Unidimensional (Diagrama de Tornado)
    # --------------------------------------------------------------------------
    print("\nEjecutando análisis de sensibilidad unidimensional (Tornado)...")
    base_lcoe = res_p1['lcoe_USD_kwh']
    base_van = res_p1['van_USD']

    # Definición de rangos de variación para cada parámetro clave [Min, Base, Max]
    sens_vars = {
        'Precio Combustible Diésel': {
            'param': 'diesel_price_USD_L',
            'range': [0.60, 1.30, 2.50],
            'unit': 'USD/L',
            'type': 'fuel_price'
        },
        'CAPEX Banco Baterías (BESS)': {
            'param': 'capex_bess_USD_kWh',
            'range': [200.0, 300.0, 450.0],
            'unit': 'USD/kWh',
            'type': 'capex_bess'
        },
        'CAPEX Campo Solar (PV)': {
            'param': 'capex_pv_USD_kWp',
            'range': [500.0, 750.0, 1100.0],
            'unit': 'USD/kWp',
            'type': 'capex_pv'
        },
        'Tasa de Descuento (WACC)': {
            'param': 'WACC',
            'range': [0.06, 0.10, 0.14],
            'unit': '%',
            'type': 'wacc'
        },
    }

    tornado_data = []

    for label, info in sens_vars.items():
        val_min, val_base, val_max = info['range']

        # Evaluar en MIN
        orig_val = params.ECON[info['param']]
        params.ECON[info['param']] = val_min
        res_min = sim.simular_despacho(P_pv_kw=P_pv_p1, N_bess=N_bess_p1, estrategia='LF')

        # Evaluar en MAX
        params.ECON[info['param']] = val_max
        res_max = sim.simular_despacho(P_pv_kw=P_pv_p1, N_bess=N_bess_p1, estrategia='LF')

        # Restaurar valor base
        params.ECON[info['param']] = orig_val

        # Delta en LCOE
        lcoe_low = res_min['lcoe_USD_kwh']
        lcoe_high = res_max['lcoe_USD_kwh']
        delta_lcoe_low = (lcoe_low - base_lcoe) / base_lcoe * 100.0
        delta_lcoe_high = (lcoe_high - base_lcoe) / base_lcoe * 100.0
        swing = abs(lcoe_high - lcoe_low)

        tornado_data.append({
            'Variable': label,
            'Valor_Min': val_min,
            'Valor_Max': val_max,
            'LCOE_Min': lcoe_low,
            'LCOE_Max': lcoe_high,
            'Delta_LCOE_Min_pct': delta_lcoe_low,
            'Delta_LCOE_Max_pct': delta_lcoe_high,
            'Swing_USD': swing,
        })

    df_tornado = pd.DataFrame(tornado_data).sort_values(by='Swing_USD', ascending=True)
    csv_tornado = os.path.join(SCRIPT_DIR, 'resumen_sensibilidad_tornado.csv')
    df_tornado.to_csv(csv_tornado, index=False)
    print(f"[DATOS GUARDADOS] Tabla de sensibilidad Tornado exportada a:\n  {csv_tornado}")

    # Gráfico de Tornado
    fig, ax = plt.subplots(figsize=(10, 5.5))
    y_pos = np.arange(len(df_tornado))

    # Barras horizontales (Izquierda: valor mínimo, Derecha: valor máximo)
    ax.barh(y_pos, df_tornado['Delta_LCOE_Min_pct'], align='center', color='#2ca02c', alpha=0.85, label='Límite Inferior (Favorable)')
    ax.barh(y_pos, df_tornado['Delta_LCOE_Max_pct'], align='center', color='#d62728', alpha=0.85, label='Límite Superior (Desfavorable)')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(df_tornado['Variable'], fontsize=11)
    ax.axvline(0, color='black', linewidth=1.0)
    ax.set_xlabel("Variación Relativa del LCOE respecto al Caso Central (%)", fontsize=11)
    ax.set_title(f"Diagrama de Tornado: Sensibilidad del LCOE ante Incertidumbres Críticas\n(Escenario Óptimo P1: LCOE Base = {base_lcoe:.4f} USD/kWh)", fontsize=12, fontweight='bold')
    ax.legend(loc='lower right', frameon=True, fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.5)

    # Anotaciones numéricas
    for i, (_, row) in enumerate(df_tornado.iterrows()):
        ax.text(row['Delta_LCOE_Min_pct'] - 0.5, i, f"{row['LCOE_Min']:.3f} $", va='center', ha='right', fontsize=9, fontweight='bold')
        ax.text(row['Delta_LCOE_Max_pct'] + 0.5, i, f"{row['LCOE_Max']:.3f} $", va='center', ha='left', fontsize=9, fontweight='bold')

    plt.tight_layout()
    fig_tornado = os.path.join(FIG_DIR, 'sensibilidad_tornado.png')
    plt.savefig(fig_tornado, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"[FIGURA GENERADA] Diagrama de Tornado guardado en:\n  {fig_tornado}")

    # --------------------------------------------------------------------------
    # 4. Sensibilidad Cruzada Bidimensional: Diésel vs BESS
    # --------------------------------------------------------------------------
    print("\nCalculando matriz de sensibilidad cruzada: Precio Diésel vs CAPEX BESS...")
    fuel_prices = np.linspace(0.60, 2.50, 10)     # 10 niveles de precio diésel
    bess_costs = np.linspace(200.0, 450.0, 9)     # 9 niveles de CAPEX BESS

    mat_sens_lcoe = np.zeros((len(bess_costs), len(fuel_prices)))

    orig_fuel = params.ECON["diesel_price_USD_L"]
    orig_bess = params.ECON["capex_bess_USD_kWh"]

    for i, b_cost in enumerate(bess_costs):
        for j, f_price in enumerate(fuel_prices):
            params.ECON["capex_bess_USD_kWh"] = b_cost
            params.ECON["diesel_price_USD_L"] = f_price
            r_sens = sim.simular_despacho(P_pv_kw=P_pv_p1, N_bess=N_bess_p1, estrategia='LF')
            mat_sens_lcoe[i, j] = r_sens['lcoe_USD_kwh']

    # Restaurar parámetros originales
    params.ECON["diesel_price_USD_L"] = orig_fuel
    params.ECON["capex_bess_USD_kWh"] = orig_bess

    fig, ax = plt.subplots(figsize=(10, 6.5))
    x_labels = [f"{p:.2f}" for p in fuel_prices]
    y_labels = [f"{b:.0f}" for b in bess_costs]

    sns.heatmap(
        mat_sens_lcoe,
        xticklabels=x_labels,
        yticklabels=y_labels,
        cmap="YlOrRd",
        annot=True,
        fmt=".3f",
        cbar_kws={'label': 'LCOE P1 (USD/kWh)'},
        ax=ax
    )
    ax.invert_yaxis()
    ax.set_title("Sensibilidad Cruzada del LCOE (USD/kWh): Precio Diésel vs. CAPEX BESS (P1)", fontsize=12, fontweight='bold')
    ax.set_xlabel("Precio del Combustible Diésel puesto en Sitio (USD / Litro)", fontsize=11)
    ax.set_ylabel("CAPEX del Banco BESS LiFePO4 (USD / kWh)", fontsize=11)
    plt.tight_layout()
    fig_cross = os.path.join(FIG_DIR, 'sensibilidad_cruzada_diesel_bess.png')
    plt.savefig(fig_cross, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"[FIGURA GENERADA] Sensibilidad cruzada guardada en:\n  {fig_cross}")
    print("=" * 74)


if __name__ == "__main__":
    run_financial_and_sensitivity_analysis()
