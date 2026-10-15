"""
=============================================================================
comparar_despacho.py — Análisis y Comparativa de Lógicas de Despacho (OE2)
=============================================================================
Compara cuantitativamente las estrategias 'Load Following' (LF) frente a
'Cycle Charging' (CC) sobre el caso de estudio de 20 viviendas en Colombia.

Genera:
  1. Tabla comparativa CSV: resumen_comparativa_despacho.csv
  2. Gráfica comparativa PNG de alta resolución: figuras/comparativa_despacho_lf_vs_cc.png
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


def run_dispatch_comparison():
    print("==========================================================================")
    print("   COMPARATIVA DE ESTRATEGIAS DE DESPACHO: LOAD FOLLOWING vs CYCLE CHARGING")
    print("==========================================================================")

    sim = MicrogridSimulator()

    # Configuraciones representativas de evaluación (números enteros de módulos JA Solar de 565 W):
    # (Nombre, PV_kWp, N_bess_modulos)
    configs = [
        ("Configuración Baja (27 mod = 15.3 kWp PV, 4 BESS = 20.5 kWh)", round(27 * params.PV["P_mod_kWp"], 3), 4),
        ("Configuración Media (44 mod = 24.9 kWp PV, 8 BESS = 41.0 kWh)", round(44 * params.PV["P_mod_kWp"], 3), 8),
        ("Configuración Alta (62 mod = 35.0 kWp PV, 12 BESS = 61.4 kWh)", round(62 * params.PV["P_mod_kWp"], 3), 12),
    ]

    records = []

    for name, pv_kw, n_bess in configs:
        print(f"\n--- Evaluando: {name} ---")
        res_lf = sim.simular_despacho(P_pv_kw=pv_kw, N_bess=n_bess, estrategia='LF')
        res_cc = sim.simular_despacho(P_pv_kw=pv_kw, N_bess=n_bess, estrategia='CC')

        for strat, res in [('Load Following (LF)', res_lf), ('Cycle Charging (CC)', res_cc)]:
            records.append({
                'Configuracion': name,
                'Estrategia': strat,
                'PV_kWp': pv_kw,
                'BESS_kWh': res['E_bess_kwh'],
                'Combustible_L_ano': round(res['fuel_liters'], 1),
                'Emisiones_tCO2_ano': round(res['co2_tons'], 2),
                'Fraccion_Renovable_pct': round(res['renewable_fraction_pct'], 2),
                'Horas_Diesel_ano': res['hours_dg'],
                'Arranques_Diesel': res['starts_dg'],
                'Vertidos_Solares_kWh': round(res['curtailment_kwh'], 1),
                'Ciclos_BESS_ano': round(res['bess_cycles'], 1),
                'LCOE_USD_kWh': round(res['lcoe_USD_kwh'], 4),
                'VAN_USD': round(res['van_USD'], 2),
            })

    df_comp = pd.DataFrame(records)
    csv_out = os.path.join(SCRIPT_DIR, 'resumen_comparativa_despacho.csv')
    df_comp.to_csv(csv_out, index=False)
    print(f"\n[DATOS GUARDADOS] Tabla comparativa exportada a:\n  {csv_out}")

    # Mostrar tabla en consola
    print("\n" + "=" * 95)
    print(df_comp[['Configuracion', 'Estrategia', 'Combustible_L_ano', 'Fraccion_Renovable_pct', 'Vertidos_Solares_kWh', 'LCOE_USD_kWh']].to_string(index=False))
    print("=" * 95)

    # --------------------------------------------------------------------------
    # Generar Gráfica Comparativa en Figuras
    # --------------------------------------------------------------------------
    sns.set_theme(style="whitegrid", font="sans-serif")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Paleta de colores
    palette = {'Load Following (LF)': '#1f77b4', 'Cycle Charging (CC)': '#ff7f0e'}

    labels_x = ['15.3 kWp + 20.5 kWh', '24.9 kWp + 41.0 kWh', '35.0 kWp + 61.4 kWh']
    df_comp['Config_Short'] = df_comp['Configuracion'].apply(
        lambda x: '15.3 kWp + 20.5 kWh' if 'Baja' in x else ('24.9 kWp + 41.0 kWh' if 'Media' in x else '35.0 kWp + 61.4 kWh')
    )

    # Subplot 1: Consumo de Combustible Diésel
    sns.barplot(data=df_comp, x='Config_Short', y='Combustible_L_ano', hue='Estrategia', palette=palette, ax=axes[0, 0])
    axes[0, 0].set_title('Consumo Anual de Diésel (L/año)', fontsize=12, fontweight='bold')
    axes[0, 0].set_xlabel('')
    axes[0, 0].set_ylabel('Litros de Diésel / año')
    axes[0, 0].grid(True, linestyle='--', alpha=0.5)

    # Subplot 2: Vertidos Solares (Curtailment)
    sns.barplot(data=df_comp, x='Config_Short', y='Vertidos_Solares_kWh', hue='Estrategia', palette=palette, ax=axes[0, 1])
    axes[0, 1].set_title('Energía Renovable Vertida / Desperdiciada (kWh/año)', fontsize=12, fontweight='bold')
    axes[0, 1].set_xlabel('')
    axes[0, 1].set_ylabel('Vertidos Solares (kWh/año)')
    axes[0, 1].grid(True, linestyle='--', alpha=0.5)

    # Subplot 3: Fracción Renovable (%)
    sns.barplot(data=df_comp, x='Config_Short', y='Fraccion_Renovable_pct', hue='Estrategia', palette=palette, ax=axes[1, 0])
    axes[1, 0].set_title('Fracción Renovable (%)', fontsize=12, fontweight='bold')
    axes[1, 0].set_xlabel('Capacidad de Planta (PV + BESS)')
    axes[1, 0].set_ylabel('Fracción Renovable (%)')
    axes[1, 0].set_ylim(0, 100)
    axes[1, 0].grid(True, linestyle='--', alpha=0.5)

    # Subplot 4: Coste Nivelado de la Energía (LCOE)
    sns.barplot(data=df_comp, x='Config_Short', y='LCOE_USD_kWh', hue='Estrategia', palette=palette, ax=axes[1, 1])
    axes[1, 1].set_title('Coste Nivelado de la Energía - LCOE (USD/kWh)', fontsize=12, fontweight='bold')
    axes[1, 1].set_xlabel('Capacidad de Planta (PV + BESS)')
    axes[1, 1].set_ylabel('LCOE (USD/kWh)')
    axes[1, 1].grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    fig_out = os.path.join(FIG_DIR, 'comparativa_despacho_lf_vs_cc.png')
    plt.savefig(fig_out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"[GRÁFICO GENERADO] Figura guardada con éxito en:\n  {fig_out}")


if __name__ == "__main__":
    run_dispatch_comparison()
