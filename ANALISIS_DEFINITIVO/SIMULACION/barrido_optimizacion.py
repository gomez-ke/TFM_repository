"""
=============================================================================
barrido_optimizacion.py — Barrido Paramétrico Determinista y Pareto (OE1 & OE3)
=============================================================================
Ejecuta la exploración exhaustiva en malla (Grid Search) sobre el espacio
de variables físicas reales:
  - N_bess in [0, 16] módulos Victron LFP de 5.12 kWh (0 a 81.92 kWh)
  - N_pv in [0, 71] módulos JA Solar de 0.565 kWp (0 a 40.115 kWp, 72 valores)
Total: 17 x 72 = 1.224 simulaciones horarias (8.760 h/punto) con PySAM.

Genera:
  1. Tablas CSV:
     - resultados_barrido_malla.csv
     - frente_pareto.csv
     - resumen_escenarios_clave.csv
  2. Figuras PNG en alta resolución (figuras/):
     - heatmap_lcoe.png
     - heatmap_rf.png
     - frente_pareto_lcoe_co2.png
     - despacho_24h_optimo_P1.png
=============================================================================
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
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


def run_parametric_sweep():
    print("==========================================================================")
    print("   BARRIDO PARAMÉTRICO DETERMINISTA Y EXTRACCIÓN DE PARETO (PySAM)")
    print("==========================================================================")

    sim = MicrogridSimulator()

    n_pv_modules = np.arange(0, 72, 1)          # 72 niveles: 0 a 71 módulos JA Solar (0 a 40.115 kWp)
    pv_values = n_pv_modules * params.PV["P_mod_kWp"]
    n_bess_values = np.arange(0, 17, 1)         # 17 valores [0, 1, ..., 16] módulos BESS
    total_runs = len(pv_values) * len(n_bess_values)

    print(f"Dimensiones de malla: {len(pv_values)} (PV: 0..71 módulos de 565W) x {len(n_bess_values)} (BESS) = {total_runs} simulaciones.")
    print("Ejecutando simulación de despacho horario anual (8.760 h por punto)...")

    # Matrices para mapas de calor (filas = BESS, columnas = PV)
    mat_lcoe = np.zeros((len(n_bess_values), len(pv_values)))
    mat_rf = np.zeros((len(n_bess_values), len(pv_values)))
    mat_co2 = np.zeros((len(n_bess_values), len(pv_values)))
    mat_van = np.zeros((len(n_bess_values), len(pv_values)))

    E_demand_annual_kWh = float(np.sum(sim.demand_kw))
    records = []

    for i, n_b in enumerate(n_bess_values):
        for j, (n_mod, p_pv) in enumerate(zip(n_pv_modules, pv_values)):
            res = sim.simular_despacho(P_pv_kw=p_pv, N_bess=n_b, estrategia='LF')

            mat_lcoe[i, j] = res['lcoe_USD_kwh']
            mat_rf[i, j] = res['renewable_fraction_pct']
            mat_co2[i, j] = res['co2_tons']
            mat_van[i, j] = res['van_USD']

            tac_USD_ano = res['lcoe_USD_kwh'] * E_demand_annual_kWh
            ie_kg_kWh = (res['co2_tons'] * 1000.0) / E_demand_annual_kWh

            records.append({
                'N_pv_mod': int(n_mod),
                'P_pv_kWp': round(p_pv, 3),
                'N_bess': n_b,
                'E_bess_kWh': res['E_bess_kwh'],
                'LCOE_USD_kWh': res['lcoe_USD_kwh'],
                'TAC_USD_ano': round(tac_USD_ano, 2),
                'IE_kg_kWh': ie_kg_kWh,
                'RF_pct': res['renewable_fraction_pct'],
                'CO2_t_ano': res['co2_tons'],
                'Fuel_L_ano': res['fuel_liters'],
                'Hours_DG_ano': res['hours_dg'],
                'Curtailment_kWh': res['curtailment_kwh'],
                'CAPEX_USD': res['total_capex_USD'],
                'OPEX_USD_ano': res['opex_annual_USD'],
                'VAN_USD': res['van_USD'],
                'Payback_Simple_anos': res['payback_simple_years'],
            })

    df_results = pd.DataFrame(records)
    csv_mesh = os.path.join(SCRIPT_DIR, 'resultados_barrido_malla.csv')
    df_results.to_csv(csv_mesh, index=False)
    print(f"\n[DATOS GUARDADOS] Resultados de malla completa guardados en:\n  {csv_mesh}")

    # --------------------------------------------------------------------------
    # 2. Extracción del Frente de Pareto Analítico (LCOE vs IE / CO2)
    # --------------------------------------------------------------------------
    # Un punto A domina a B si LCOE(A) <= LCOE(B) y CO2(A) <= CO2(B) con al menos una desigualdad estricta.
    pareto_pts = []
    points = df_results[['LCOE_USD_kWh', 'CO2_t_ano', 'IE_kg_kWh', 'TAC_USD_ano', 'P_pv_kWp', 'N_pv_mod', 'N_bess', 'E_bess_kWh', 'RF_pct', 'CAPEX_USD', 'OPEX_USD_ano', 'VAN_USD']].to_dict('records')

    for pt in points:
        lcoe_a = pt['LCOE_USD_kWh']
        co2_a = pt['CO2_t_ano']
        dominated = False
        for other in points:
            lcoe_b = other['LCOE_USD_kWh']
            co2_b = other['CO2_t_ano']
            if (lcoe_b <= lcoe_a and co2_b <= co2_a) and (lcoe_b < lcoe_a or co2_b < co2_a):
                dominated = True
                break
        if not dominated:
            pareto_pts.append(pt)

    df_pareto = pd.DataFrame(pareto_pts).sort_values(by='LCOE_USD_kWh').reset_index(drop=True)
    csv_pareto = os.path.join(SCRIPT_DIR, 'frente_pareto.csv')
    df_pareto.to_csv(csv_pareto, index=False)
    print(f"[DATOS GUARDADOS] Frente de Pareto analítico ({len(df_pareto)} puntos no dominados) guardado en:\n  {csv_pareto}")

    # --------------------------------------------------------------------------
    # 3. Selección de Escenarios Clave (Caso Base + 3 Óptimos de Pareto)
    # --------------------------------------------------------------------------
    # Caso Base (100% Diésel)
    row_base = df_results[(df_results['P_pv_kWp'] == 0.0) & (df_results['N_bess'] == 0)].iloc[0]

    # P1: Mínimo LCOE absoluto (Minimización Económica Pura)
    row_p1 = df_results.loc[df_results['LCOE_USD_kWh'].idxmin()]

    # P2: Compromiso Multiobjetivo Ponderado (Barrera psicológica RF >= 99%, w=0.35/0.65)
    df_rf99 = df_results[df_results['RF_pct'] >= 99.0]
    row_p2 = df_rf99.loc[df_rf99['LCOE_USD_kWh'].idxmin()]

    # P3: Mínimas Emisiones Absolutas (Minimización Ambiental Extrema de la frontera)
    row_p3 = df_results.loc[df_results['CO2_t_ano'].idxmin()]

    escenarios = [
        {'Escenario': 'Caso Base (100% Diésel)', **row_base.to_dict()},
        {'Escenario': 'P1 (Mínimo LCOE)', **row_p1.to_dict()},
        {'Escenario': 'P2 (Compromiso RF >= 99%)', **row_p2.to_dict()},
        {'Escenario': 'P3 (Mínimas Emisiones)', **row_p3.to_dict()},
    ]
    df_escenarios = pd.DataFrame(escenarios)
    csv_esc = os.path.join(SCRIPT_DIR, 'resumen_escenarios_clave.csv')
    df_escenarios.to_csv(csv_esc, index=False)
    print(f"[DATOS GUARDADOS] Resumen de escenarios clave guardado en:\n  {csv_esc}")

    print("\n" + "=" * 120)
    print("   MATRIZ COMPARATIVA DE ESCENARIOS CLAVE")
    print("=" * 120)
    cols_show = ['Escenario', 'N_pv_mod', 'P_pv_kWp', 'N_bess', 'E_bess_kWh', 'LCOE_USD_kWh', 'TAC_USD_ano', 'OPEX_USD_ano', 'IE_kg_kWh', 'CO2_t_ano', 'Hours_DG_ano', 'CAPEX_USD']
    print(df_escenarios[cols_show].to_string(index=False))
    print("=" * 120)

    # --------------------------------------------------------------------------
    # 4. Generar Gráficas de Mapas de Calor 2D
    # --------------------------------------------------------------------------
    sns.set_theme(style="white")

    # Heatmap LCOE
    fig, ax = plt.subplots(figsize=(10, 7))
    bess_labels = [f"{n*5.12:.1f}" for n in n_bess_values]
    pv_labels = [f"{m*0.565:.1f}" if m % 10 == 0 else "" for m in n_pv_modules]

    sns.heatmap(
        mat_lcoe,
        xticklabels=pv_labels,
        yticklabels=bess_labels,
        cmap="viridis_r",
        cbar_kws={'label': 'LCOE (USD/kWh)'},
        ax=ax
    )
    ax.invert_yaxis()
    ax.set_title("Coste Nivelado de la Energía (LCOE en USD/kWh) en el Espacio de Dimensionamiento", fontsize=12, fontweight='bold')
    ax.set_xlabel("Potencia fotovoltaica instalada (kWp)", fontsize=11)
    ax.set_ylabel("Capacidad total BESS (kWh)", fontsize=11)
    plt.yticks(rotation=0)
    plt.tight_layout()
    fig_lcoe = os.path.join(FIG_DIR, 'heatmap_lcoe.png')
    plt.savefig(fig_lcoe, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"[FIGURA GENERADA] Heatmap LCOE guardado en:\n  {fig_lcoe}")

    # Heatmap Fracción Renovable
    fig, ax = plt.subplots(figsize=(10, 7))
    sns.heatmap(
        mat_rf,
        xticklabels=pv_labels,
        yticklabels=bess_labels,
        cmap="YlGnBu",
        cbar_kws={'label': 'Fracción Renovable (%)'},
        ax=ax
    )
    ax.invert_yaxis()
    ax.set_title("Fracción Renovable (%) en el Espacio de Dimensionamiento", fontsize=12, fontweight='bold')
    ax.set_xlabel("Potencia fotovoltaica instalada (kWp)", fontsize=11)
    ax.set_ylabel("Capacidad total BESS (kWh)", fontsize=11)
    plt.yticks(rotation=0)
    plt.tight_layout()
    fig_rf = os.path.join(FIG_DIR, 'heatmap_rf.png')
    plt.savefig(fig_rf, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"[FIGURA GENERADA] Heatmap Fracción Renovable guardado en:\n  {fig_rf}")

    # --------------------------------------------------------------------------
    # 5. Generar Gráfica del Frente de Pareto (Doble Panel: Global + Zoom)
    # --------------------------------------------------------------------------
    sns.set_theme(style="whitegrid")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Panel 1: Espacio Global (1.224 configuraciones)
    ax1.scatter(df_results['IE_kg_kWh'], df_results['LCOE_USD_kWh'], color='#b0bec5', alpha=0.35, s=15, label=f'Espacio Global ({len(df_results):,} configuraciones)')
    ax1.plot(df_pareto['IE_kg_kWh'], df_pareto['LCOE_USD_kWh'], color='#d32f2f', linewidth=2.0, label='Frontera de Pareto (41 puntos)')

    # Caso Base Diésel
    ie_base = row_base['IE_kg_kWh']
    lcoe_base = row_base['LCOE_USD_kWh']
    ax1.scatter(ie_base, lcoe_base, color='#b71c1c', marker='X', s=150, zorder=7, label='Caso Base (100% Diésel)')
    ax1.annotate("Caso Base (100% Diésel)\n2,31 kg CO2/kWh | $1,31/kWh\n(54,59 t CO2/año)", 
                 (ie_base, lcoe_base), 
                 textcoords="offset points", xytext=(-110, -42), 
                 fontsize=8.5, fontweight='bold', color='#b71c1c',
                 arrowprops=dict(arrowstyle="->", color='#b71c1c', lw=1.2),
                 bbox=dict(boxstyle="round,pad=0.25", fc="#ffebee", ec="#b71c1c", alpha=0.85))

    # Recuadro indicando la región de zoom hacia el Panel 2
    rect_x, rect_y, rect_w, rect_h = -0.005, 0.380, 0.095, 0.130
    rect = patches.Rectangle((rect_x, rect_y), rect_w, rect_h, linewidth=2.0, edgecolor="#0277bd", facecolor="#e1f5fe", alpha=0.45, linestyle="--", zorder=6)
    ax1.add_patch(rect)
    ax1.text(rect_x + 0.02, rect_y + rect_h + 0.03, "Zona de Detalle\n(Ampliación Panel b)", color="#01579b", fontsize=8.5, fontweight="bold")

    ax1.set_title("(a) Espacio Global de Búsqueda (1.224 configuraciones)", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Intensidad de Emisiones de CO2 (kg CO2 / kWh)", fontsize=10.5)
    ax1.set_ylabel("Coste Nivelado de la Energía - LCOE (USD / kWh)", fontsize=10.5)
    ax1.set_xlim(-0.08, 2.45)
    ax1.set_ylim(0.35, 1.40)
    ax1.legend(loc="upper center", frameon=True, fontsize=8.5)

    # Panel 2: Detalle del Frente de Pareto y Escenarios Clave
    mask_zoom = (df_results['IE_kg_kWh'] <= 0.095) & (df_results['LCOE_USD_kWh'] <= 0.52)
    df_zoom = df_results[mask_zoom]
    ax2.scatter(df_zoom['IE_kg_kWh'], df_zoom['LCOE_USD_kWh'], color='#cfd8dc', alpha=0.55, s=25, label='Configuraciones en zona')
    ax2.plot(df_pareto['IE_kg_kWh'], df_pareto['LCOE_USD_kWh'], color='#d32f2f', linewidth=2.5, linestyle='-', zorder=4, label='Frontera de Pareto')
    ax2.scatter(df_pareto['IE_kg_kWh'], df_pareto['LCOE_USD_kWh'], color='#d32f2f', s=40, zorder=5)

    p1_lbl = f"P1: Mínimo LCOE ({row_p1['N_pv_mod']:.0f} mod = {row_p1['P_pv_kWp']:.2f} kWp, {row_p1['N_bess']:.0f} BESS = {row_p1['E_bess_kWh']:.1f} kWh)"
    p2_lbl = f"P2: Compromiso RF >= 99% ({row_p2['N_pv_mod']:.0f} mod = {row_p2['P_pv_kWp']:.2f} kWp, {row_p2['N_bess']:.0f} BESS = {row_p2['E_bess_kWh']:.1f} kWh)"
    p3_lbl = f"P3: Mínimas Emisiones ({row_p3['N_pv_mod']:.0f} mod = {row_p3['P_pv_kWp']:.2f} kWp, {row_p3['N_bess']:.0f} BESS = {row_p3['E_bess_kWh']:.1f} kWh)"

    # P1 (Mínimo LCOE)
    ax2.scatter(row_p1['IE_kg_kWh'], row_p1['LCOE_USD_kWh'], color='#2e7d32', s=160, zorder=6, marker='o', label=p1_lbl)
    ax2.annotate("P1 (Mínimo LCOE)\n$0,3944/kWh | 0,0756 kg/kWh\n(45 mod PV + 12 BESS | 1,79 t/año)", 
                 (row_p1['IE_kg_kWh'], row_p1['LCOE_USD_kWh']), 
                 textcoords="offset points", xytext=(-65, -38), 
                 fontsize=8.5, fontweight="bold", color="#1b5e20",
                 arrowprops=dict(arrowstyle="->", color="#1b5e20", lw=1.2),
                 bbox=dict(boxstyle="round,pad=0.25", fc="#e8f5e9", ec="#2e7d32", alpha=0.9))

    # P2 (Compromiso RF >= 99%)
    ax2.scatter(row_p2['IE_kg_kWh'], row_p2['LCOE_USD_kWh'], color='#0288d1', s=160, zorder=6, marker='s', label=p2_lbl)
    ax2.annotate("P2 (Compromiso RF >= 99%)\n$0,4195/kWh | 0,0127 kg/kWh\n(55 mod PV + 14 BESS | 0,30 t/año)", 
                 (row_p2['IE_kg_kWh'], row_p2['LCOE_USD_kWh']), 
                 textcoords="offset points", xytext=(18, -18), 
                 fontsize=8.5, fontweight="bold", color="#01579b",
                 arrowprops=dict(arrowstyle="->", color="#01579b", lw=1.2),
                 bbox=dict(boxstyle="round,pad=0.25", fc="#e1f5fe", ec="#0288d1", alpha=0.9))

    # P3 (Mínimas Emisiones)
    ax2.scatter(row_p3['IE_kg_kWh'], row_p3['LCOE_USD_kWh'], color='#7b1fa2', s=160, zorder=6, marker='^', label=p3_lbl)
    ax2.annotate("P3 (Mínimas Emisiones)\n$0,4928/kWh | 0,0047 kg/kWh\n(71 mod PV + 16 BESS | 0,11 t/año)", 
                 (row_p3['IE_kg_kWh'], row_p3['LCOE_USD_kWh']), 
                 textcoords="offset points", xytext=(18, -55), 
                 fontsize=8.5, fontweight="bold", color="#4a148c",
                 arrowprops=dict(arrowstyle="->", color="#4a148c", lw=1.2),
                 bbox=dict(boxstyle="round,pad=0.25", fc="#f3e5f5", ec="#7b1fa2", alpha=0.9))

    ax2.set_title("(b) Detalle de la Frontera de Pareto y Soluciones Clave", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Intensidad de Emisiones de CO2 (kg CO2 / kWh)", fontsize=10.5)
    ax2.set_ylabel("Coste Nivelado de la Energía - LCOE (USD / kWh)", fontsize=10.5)
    ax2.set_xlim(-0.005, 0.088)
    ax2.set_ylim(0.380, 0.510)
    ax2.legend(loc="upper right", frameon=True, fontsize=8)

    plt.tight_layout()
    fig_pareto = os.path.join(FIG_DIR, 'frente_pareto_lcoe_co2.png')
    plt.savefig(fig_pareto, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"[FIGURA GENERADA] Frente de Pareto guardado en:\n  {fig_pareto}")

    # --------------------------------------------------------------------------
    # 6. Despacho Horario Representativo de 24 Horas para P1
    # --------------------------------------------------------------------------
    print("\nGenerando curva de despacho horario 24h para el escenario óptimo P1...")
    res_p1_hourly = sim.simular_despacho(P_pv_kw=row_p1['P_pv_kWp'], N_bess=int(row_p1['N_bess']), return_hourly=True)
    h_data = res_p1_hourly['hourly']

    # Seleccionar un día de verano / soleado representativo (ejemplo: día 15 de enero: horas 336 a 360)
    d_start = 14 * 24
    d_end = 15 * 24
    hours_24 = np.arange(24)

    fig, ax1 = plt.subplots(figsize=(12, 6))

    ax1.plot(hours_24, h_data['demand'][d_start:d_end], color='#212121', linewidth=2.2, label='Demanda Comunitaria (kW)')
    ax1.plot(hours_24, h_data['pv_gen'][d_start:d_end], color='#fbc02d', linewidth=2.0, linestyle='--', label='Generación Solar FV (kW)')
    ax1.plot(hours_24, h_data['diesel'][d_start:d_end], color='#d32f2f', linewidth=2.0, label='Generación Diésel (kW)')
    ax1.plot(hours_24, h_data['bess_dis'][d_start:d_end], color='#388e3c', linewidth=2.0, label='Descarga BESS (kW)')
    ax1.plot(hours_24, h_data['bess_ch'][d_start:d_end], color='#0288d1', linewidth=1.5, linestyle=':', label='Carga BESS (kW)')

    ax1.set_xlabel('Hora del Día (h)', fontsize=11)
    ax1.set_ylabel('Potencia Activa (kW)', fontsize=11)
    ax1.set_xticks(range(0, 24, 2))
    ax1.set_xlim(0, 23)
    ax1.set_ylim(0, max(h_data['pv_gen'][d_start:d_end].max(), 16.0))
    ax1.grid(True, linestyle='--', alpha=0.5)

    # Eje secundario para SoC de la batería
    ax2 = ax1.twinx()
    ax2.plot(hours_24, h_data['soc'][d_start:d_end] * 100.0, color='#7b1fa2', linewidth=1.8, linestyle='-.', label='Estado de Carga - SoC (%)')
    ax2.set_ylabel('SoC de Batería (%)', color='#7b1fa2', fontsize=11)
    ax2.tick_params(axis='y', labelcolor='#7b1fa2')
    ax2.set_ylim(0, 100)

    # Leyendas combinadas
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', frameon=True, fontsize=9)

    ax1.set_title(f"Perfil de Despacho Horario 24h para el Escenario Óptimo P1 ({row_p1['N_pv_mod']:.0f} paneles = {row_p1['P_pv_kWp']:.2f} kWp PV + {row_p1['E_bess_kWh']:.1f} kWh BESS)\nDía Soleado Representativo (15 de Enero)", fontsize=12, fontweight='bold')
    plt.tight_layout()
    fig_dispatch = os.path.join(FIG_DIR, 'despacho_24h_optimo_P1.png')
    plt.savefig(fig_dispatch, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"[FIGURA GENERADA] Despacho 24h guardado en:\n  {fig_dispatch}")


if __name__ == "__main__":
    run_parametric_sweep()
