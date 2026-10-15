import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Directorio base: la carpeta DEMANDA donde vive este script y todos sus archivos
# Todos los archivos de entrada y salida se guardan en esta misma carpeta
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# → C:\Users\kgome\TFM\ANALISIS_DEFINITIVO\DEMANDA\

def generate_community_profile():
    print("==========================================================================")
    print("   GENERACIÓN Y VERIFICACIÓN DEL PERFIL DE DEMANDA (20 VIVIENDAS)")
    print("==========================================================================")

    # --------------------------------------------------------------------------
    # 1. Cargar archivo CSV de la vivienda base (mismo directorio que el script)
    # --------------------------------------------------------------------------
    csv_original = os.path.join(SCRIPT_DIR, 'CSV_vivienda.csv')
    if not os.path.exists(csv_original):
        print(f"Error: No se encuentra {csv_original}")
        return

    df_orig = pd.read_csv(csv_original, header=None)
    data_orig = df_orig[0].values  # Valores originales (W)

    annual_energy_orig_kwh = data_orig.sum() / 1000.0
    print(f"Energía Anual Original (CSV_vivienda): {annual_energy_orig_kwh:,.2f} kWh")

    # --------------------------------------------------------------------------
    # 2. Definir el Consumo Teórico Objetivo (Tabla Capítulo 7_analisis.tex)
    # --------------------------------------------------------------------------
    daily_energy_per_house_wh = 3238.3    # Wh/día por vivienda
    annual_energy_per_house_kwh = (daily_energy_per_house_wh * 365) / 1000.0  # 1.181,98 kWh/año
    target_annual_community_kwh = 20 * annual_energy_per_house_kwh             # 23.639,59 kWh/año

    print(f"Energía Anual Objetivo por Vivienda: {annual_energy_per_house_kwh:,.2f} kWh/año")
    print(f"Energía Anual Objetivo Comunidad (20 Viviendas): {target_annual_community_kwh:,.2f} kWh/año")

    # --------------------------------------------------------------------------
    # 3. Calcular Factor de Escala Exacto y aplicar escalado
    # --------------------------------------------------------------------------
    scale_factor = target_annual_community_kwh / annual_energy_orig_kwh
    print(f"\nFactor de Escala Aplicado: {scale_factor:.6f}")

    # Aplicar escalado (manteniendo unidades en Vatios W para compatibilidad con SAM)
    data_scaled_w = data_orig * scale_factor
    data_scaled_kw = data_scaled_w / 1000.0  # Convertir a kW para gráficas y métricas

    # --------------------------------------------------------------------------
    # 4. Guardar el perfil escalado en la misma carpeta DEMANDA
    # --------------------------------------------------------------------------
    csv_scaled_path = os.path.join(SCRIPT_DIR, 'demanda_20_viviendas.csv')
    df_scaled = pd.DataFrame(data_scaled_w)
    df_scaled.to_csv(csv_scaled_path, header=False, index=False)
    print(f"\n[ARCHIVO CREADO] Perfil escalado guardado en: {csv_scaled_path}")

    # --------------------------------------------------------------------------
    # 5. Verificaciones Numéricas de Integridad y Coherencia
    # --------------------------------------------------------------------------
    calc_annual_community_kwh = data_scaled_kw.sum()
    calc_daily_community_kwh  = calc_annual_community_kwh / 365.0
    calc_daily_house_wh       = (calc_daily_community_kwh / 20.0) * 1000.0
    calc_annual_house_kwh     = calc_annual_community_kwh / 20.0

    peak_power_kw = data_scaled_kw.max()
    min_power_kw  = data_scaled_kw.min()
    mean_power_kw = data_scaled_kw.mean()
    load_factor   = mean_power_kw / peak_power_kw  # Esperado entre 0.25 y 0.45 para uso residencial

    error_percentage = abs(calc_annual_community_kwh - target_annual_community_kwh) / target_annual_community_kwh * 100.0

    print("\n--------------------------------------------------------------------------")
    print("   TABLA DE VERIFICACIÓN NUMÉRICA (COMPROBACIÓN DE COHERENCIA)")
    print("--------------------------------------------------------------------------")
    print(f"{'Métrica':<42} | {'Teórico (Tabla 7)':<20} | {'Calculado (CSV)':<15}")
    print("-" * 82)
    print(f"{'Consumo Diario / Vivienda (Wh/día)':<42} | {daily_energy_per_house_wh:<20.1f} | {calc_daily_house_wh:<15.1f}")
    print(f"{'Consumo Anual / Vivienda (kWh/año)':<42} | {annual_energy_per_house_kwh:<20.2f} | {calc_annual_house_kwh:<15.2f}")
    print(f"{'Consumo Diario Comunidad (kWh/día)':<42} | {target_annual_community_kwh/365:<20.2f} | {calc_daily_community_kwh:<15.2f}")
    print(f"{'Consumo Anual Comunidad (kWh/año)':<42} | {target_annual_community_kwh:<20.2f} | {calc_annual_community_kwh:<15.2f}")
    print(f"{'Consumo Anual Comunidad (MWh/año)':<42} | {target_annual_community_kwh/1000:<20.2f} | {calc_annual_community_kwh/1000:<15.2f}")
    print(f"{'Potencia de Pico Coincidente (kW)':<42} | {'~13.1 kW (F_s=0.55)':<20} | {peak_power_kw:<15.2f}")
    print(f"{'Potencia Promedio (kW)':<42} | {'--':<20} | {mean_power_kw:<15.2f}")
    print(f"{'Potencia Mínima (kW)':<42} | {'--':<20} | {min_power_kw:<15.2f}")
    print(f"{'Factor de Carga (esperado 0.25-0.45)':<42} | {'0.25 – 0.45':<20} | {load_factor:<15.4f}")
    print("-" * 82)
    print(f"Error Relativo de Ajuste: {error_percentage:.6f}% (¡CUADRE PERFECTO!)")

    # --------------------------------------------------------------------------
    # 6. Generar Gráficas del Perfil de la Comunidad
    # --------------------------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    hours = np.arange(1, 8761)

    # --- Subplot 1: Perfil Anual Completo (8.760 horas) ---
    axes[0, 0].plot(hours, data_scaled_kw, color='#1f77b4', linewidth=0.5, alpha=0.8)
    axes[0, 0].set_title('Perfil de Demanda Anual (Comunidad 20 Viviendas - 8.760 h)', fontsize=11, fontweight='bold')
    axes[0, 0].set_xlabel('Hora del Año')
    axes[0, 0].set_ylabel('Demanda (kW)')
    axes[0, 0].grid(True, linestyle='--', alpha=0.5)

    # --- Subplot 2: Curva de Duración de Carga ---
    sorted_kw = np.sort(data_scaled_kw)[::-1]
    axes[0, 1].plot(hours, sorted_kw, color='#d62728', linewidth=1.5)
    axes[0, 1].fill_between(hours, sorted_kw, color='#d62728', alpha=0.2)
    axes[0, 1].set_title('Curva de Duración de Carga de la Comunidad', fontsize=11, fontweight='bold')
    axes[0, 1].set_xlabel('Horas acumuladas')
    axes[0, 1].set_ylabel('Demanda (kW)')
    axes[0, 1].grid(True, linestyle='--', alpha=0.5)

    # --- Subplot 3: Perfil Horario Promedio por Temporada ---
    # Zona ecuatorial: no hay invierno/verano térmico → se comparan temporada seca y húmeda
    hours_day = np.arange(24)

    # Temporada seca – Enero (mes 1: horas 0 a 743 → 31 días × 24h)
    january_data = data_scaled_kw[0:744].reshape(-1, 24)
    day_dry = january_data.mean(axis=0)   # Promedio de los 31 días

    # Temporada húmeda – Julio (mes 7: horas 4344 a 5087 → 31 días × 24h)
    july_data = data_scaled_kw[4344:5088].reshape(-1, 24)
    day_wet = july_data.mean(axis=0)

    axes[1, 0].plot(hours_day, day_dry, marker='o', color='#2ca02c', linewidth=2,
                    label='Temporada Seca – Enero (promedio 31 días)')
    axes[1, 0].plot(hours_day, day_wet, marker='s', color='#ff7f0e', linewidth=2,
                    label='Temporada Húmeda – Julio (promedio 31 días)')
    axes[1, 0].set_title('Perfil Horario Diario Promedio por Temporada\n(Zona Ecuatorial Cundinamarca–Meta)', fontsize=11, fontweight='bold')
    axes[1, 0].set_xlabel('Hora del Día (0 - 23h)')
    axes[1, 0].set_ylabel('Demanda (kW)')
    axes[1, 0].set_xticks(range(0, 24, 2))
    axes[1, 0].legend(fontsize=9)
    axes[1, 0].grid(True, linestyle='--', alpha=0.5)

    # --- Subplot 4: Distribución Mensual de Demanda (Boxplot) ---
    # Asignación de mes a cada hora usando los días reales de cada mes
    days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    month_labels = np.zeros(8760, dtype=int)
    hour = 0
    for m, days in enumerate(days_per_month, start=1):
        n_hours = days * 24
        month_labels[hour:hour + n_hours] = m
        hour += n_hours

    df_hourly = pd.DataFrame({'Demand_kW': data_scaled_kw, 'Month': month_labels})
    months_names = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    sns.boxplot(x='Month', y='Demand_kW', data=df_hourly, ax=axes[1, 1],
                hue='Month', palette='Blues', legend=False)
    axes[1, 1].set_xticks(range(12))
    axes[1, 1].set_xticklabels(months_names)
    axes[1, 1].set_title('Distribución Mensual de Demanda (Comunidad 20 Viviendas)', fontsize=11, fontweight='bold')
    axes[1, 1].set_xlabel('Mes')
    axes[1, 1].set_ylabel('Demanda (kW)')
    axes[1, 1].grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()

    # Guardar figura en la misma carpeta DEMANDA
    out_fig = os.path.join(SCRIPT_DIR, 'demanda_comunidad_20viviendas.png')
    plt.savefig(out_fig, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"[GRÁFICO GENERADO] Imagen guardada en: {out_fig}")

if __name__ == "__main__":
    generate_community_profile()
