import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Backend sin GUI (compatible con entornos sin pantalla)
import matplotlib.pyplot as plt
import seaborn as sns

import PySAM.Pvwattsv8 as pv

# Directorio base del script (independiente del directorio de ejecución)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# → C:\Users\kgome\TFM\ANALISIS_DEFINITIVO\RECURSO_SOLAR\

def analyze_solar_resource():
    print("==========================================================================")
    print("   ANÁLISIS DEL RECURSO SOLAR: COLOMBIA (CUNDINAMARCA - META)")
    print("==========================================================================")

    # --------------------------------------------------------------------------
    # 1. Localizar y cargar el archivo EPW (mismo directorio que el script)
    # --------------------------------------------------------------------------
    epw_path = os.path.join(SCRIPT_DIR, 'tmy_ESTUDIO_TFM.epw')
    if not os.path.exists(epw_path):
        print(f"Error: No se encuentra el archivo EPW en: {epw_path}")
        print("Asegúrate de que 'tmy_ESTUDIO_TFM.epw' está en la misma carpeta que este script.")
        return

    # --------------------------------------------------------------------------
    # 2. Simular generación con PySAM para 1 kWp de referencia
    # --------------------------------------------------------------------------
    pv_model = pv.default('PVWattsNone')
    pv_model.SolarResource.solar_resource_file = epw_path
    pv_model.SystemDesign.system_capacity = 1.0  # 1 kWp de referencia
    pv_model.SystemDesign.tilt = 10.0             # Inclinación constructiva UPME/DNP (10°)
    pv_model.SystemDesign.azimuth = 180.0         # Orientación Sur geográfico (180°)
    pv_model.execute()

    gen_hourly_kw   = np.array(pv_model.Outputs.gen)   # 8760 valores en kWh/h
    annual_gen_kwh  = gen_hourly_kw.sum()
    capacity_factor = pv_model.Outputs.capacity_factor

    # --------------------------------------------------------------------------
    # 3. Leer datos meteorológicos del EPW
    # Formato EPW estándar (EnergyPlus): 8 filas de cabecera, luego datos horarios
    # Columna 2: Month, 3: Day, 4: Hour, 7: DryBulb Temp (°C)
    # Columna 14: GHI (W/m²), 15: DNI (W/m²), 16: DHI (W/m²)
    # NOTA: pandas usa índice base-0, por lo que col 2→[1], 14→[13], etc.
    # --------------------------------------------------------------------------
    df_epw = pd.read_csv(epw_path, skiprows=8, header=None)

    # Verificación del número de columnas para detectar formatos EPW no estándar
    n_cols = df_epw.shape[1]
    if n_cols < 16:
        print(f"Advertencia: El EPW tiene solo {n_cols} columnas. Formato no estándar.")
        return

    months   = df_epw[1].values   # Mes (1-12)
    temp_c   = df_epw[6].values   # Temperatura de bulbo seco (°C)
    ghi_wm2  = df_epw[13].values  # Irradiancia Global Horizontal (W/m²)
    dni_wm2  = df_epw[14].values  # Irradiancia Directa Normal (W/m²)
    dhi_wm2  = df_epw[15].values  # Irradiancia Difusa Horizontal (W/m²)

    # --------------------------------------------------------------------------
    # 4. Totales y Promedios Anuales
    # --------------------------------------------------------------------------
    annual_ghi_kwh_m2    = ghi_wm2.sum() / 1000.0
    daily_avg_ghi_kwh_m2 = annual_ghi_kwh_m2 / 365.0

    print(f"Coordenadas: Lat 4.24° N, Lon -73.78° W (Cordillera Oriental, Cundinamarca–Meta)")
    print(f"Altitud: 2.548 m s.n.m.")
    print(f"GHI Anual Acumulada:               {annual_ghi_kwh_m2:,.2f} kWh/m²/año")
    print(f"HSP Promedio Diario (GHI/día):      {daily_avg_ghi_kwh_m2:.2f} kWh/m²/día")
    print(f"Temperatura Promedio Anual:         {temp_c.mean():.1f} °C")
    print(f"  (Mínima: {temp_c.min():.1f} °C  |  Máxima: {temp_c.max():.1f} °C)")
    print(f"Generación Unitaria (1 kWp):        {annual_gen_kwh:,.2f} kWh/kWp/año")
    print(f"Factor de Planta (Capacity Factor): {capacity_factor:.2f} %")

    # --------------------------------------------------------------------------
    # 5. Tabla Mensual de Radiación, Temperatura y Generación
    # --------------------------------------------------------------------------
    df_hourly = pd.DataFrame({
        'Month':   months,
        'GHI_Wh':  ghi_wm2,
        'DNI_Wh':  dni_wm2,
        'DHI_Wh':  dhi_wm2,
        'Temp_C':  temp_c,
        'Gen_kWh': gen_hourly_kw
    })

    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    months_names  = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                     'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

    monthly_summary = []
    for m in range(1, 13):
        df_m   = df_hourly[df_hourly['Month'] == m]
        days_m = days_in_month[m - 1]

        monthly_summary.append({
            'Mes':                   months_names[m - 1],
            'GHI (kWh/m²/día)':     round((df_m['GHI_Wh'].sum() / 1000.0) / days_m, 2),
            'DNI (kWh/m²/día)':     round((df_m['DNI_Wh'].sum() / 1000.0) / days_m, 2),
            'DHI (kWh/m²/día)':     round((df_m['DHI_Wh'].sum() / 1000.0) / days_m, 2),
            'Temp_Media (°C)':      round(df_m['Temp_C'].mean(), 1),
            'Gen_1kWp (kWh/mes)':   round(df_m['Gen_kWh'].sum(), 1)
        })

    df_monthly = pd.DataFrame(monthly_summary)

    print("\n--------------------------------------------------------------------------")
    print("   TABLA PROMEDIOS MENSUALES DEL RECURSO SOLAR Y GENERACIÓN")
    print("--------------------------------------------------------------------------")
    print(df_monthly.to_string(index=False))

    # Totales / resumen anual al pie de la tabla
    print("-" * 80)
    print(f"  TOTAL ANUAL:  GHI={annual_ghi_kwh_m2:.1f} kWh/m²  |  "
          f"Gen={annual_gen_kwh:.1f} kWh/kWp  |  "
          f"Temp.media={temp_c.mean():.1f} °C")

    # Guardar CSV en la misma carpeta
    csv_out = os.path.join(SCRIPT_DIR, 'resumen_recurso_solar_colombia.csv')
    df_monthly.to_csv(csv_out, index=False)
    print(f"\n[DATOS GUARDADOS] CSV exportado a: {csv_out}")

    # --------------------------------------------------------------------------
    # 6. Gráficas del Recurso Solar
    # --------------------------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    hours_arr = np.arange(1, 8761)

    # --- Subplot 1: Irradiancia GHI Horaria Anual ---
    axes[0, 0].plot(hours_arr, ghi_wm2, color='#e377c2', linewidth=0.4, alpha=0.7)
    axes[0, 0].set_title('Irradiancia Horizontal Global Horaria (GHI - 8.760 h)',
                          fontsize=11, fontweight='bold')
    axes[0, 0].set_xlabel('Hora del Año')
    axes[0, 0].set_ylabel('GHI (W/m²)')
    axes[0, 0].grid(True, linestyle='--', alpha=0.5)

    # --- Subplot 2: Comparativa Mensual GHI / DNI / DHI ---
    x     = np.arange(12)
    width = 0.25
    axes[0, 1].bar(x - width, df_monthly['GHI (kWh/m²/día)'], width,
                   label='GHI (Global)',  color='#ff7f0e')
    axes[0, 1].bar(x,         df_monthly['DNI (kWh/m²/día)'], width,
                   label='DNI (Directa)', color='#2ca02c')
    axes[0, 1].bar(x + width, df_monthly['DHI (kWh/m²/día)'], width,
                   label='DHI (Difusa)',  color='#1f77b4')
    axes[0, 1].set_xticks(x)
    axes[0, 1].set_xticklabels(months_names)
    axes[0, 1].set_title('Radiación Promedio Diaria por Componente y Mes (kWh/m²/día)',
                          fontsize=11, fontweight='bold')
    axes[0, 1].set_ylabel('kWh/m²/día')
    axes[0, 1].legend()
    axes[0, 1].grid(True, linestyle='--', alpha=0.5)

    # --- Subplot 3: Distribución de Temperatura Mensual (Boxplot) ---
    sns.boxplot(x='Month', y='Temp_C', data=df_hourly, ax=axes[1, 0],
                hue='Month', palette='YlOrRd', legend=False)
    axes[1, 0].set_xticks(range(12))
    axes[1, 0].set_xticklabels(months_names)
    axes[1, 0].set_title('Distribución de Temperatura Ambiente Mensual (°C)',
                          fontsize=11, fontweight='bold')
    axes[1, 0].set_xlabel('Mes')           # ← corregido de 'Month' a 'Mes'
    axes[1, 0].set_ylabel('Temperatura (°C)')
    axes[1, 0].grid(True, linestyle='--', alpha=0.5)

    # --- Subplot 4: Generación Fotovoltaica Mensual (1 kWp referencia) ---
    axes[1, 1].plot(months_names, df_monthly['Gen_1kWp (kWh/mes)'],
                    marker='o', color='#d62728', linewidth=2.0)
    axes[1, 1].fill_between(range(12), df_monthly['Gen_1kWp (kWh/mes)'],
                             color='#d62728', alpha=0.2)
    axes[1, 1].set_xticks(range(12))
    axes[1, 1].set_xticklabels(months_names)
    axes[1, 1].set_title('Generación Mensual de Referencia (1 kWp Instalado)',
                          fontsize=11, fontweight='bold')
    axes[1, 1].set_xlabel('Mes')
    axes[1, 1].set_ylabel('Generación (kWh/mes)')
    axes[1, 1].grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()

    out_fig = os.path.join(SCRIPT_DIR, 'recurso_solar_colombia.png')
    plt.savefig(out_fig, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"[GRÁFICO GENERADO] Figura guardada en: {out_fig}")

if __name__ == "__main__":
    analyze_solar_resource()
