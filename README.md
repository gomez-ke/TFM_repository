# Optimización de una Microrred Híbrida Renovable con Almacenamiento (FV-BESS-Diésel)

Repositorio oficial con los algoritmos, modelos matemáticos y rutinas de simulación horaria desarrollados para el Trabajo de Fin de Máster:

* **Título:** Optimización de una microrred híbrida con generación renovable mediante simulación energética
* **Máster:** Máster Universitario en Energías Renovables y Sostenibilidad Energética
* **Institución:** Universidad Europea Miguel de Cervantes (UEMC)
* **Autor:** Kevin Gómez Mantilla
* **Tutor:** Ismael Lozano Gabarre

---

## Estructura del Repositorio

El código de simulación y los datos definitivos se organizan en el directorio `ANALISIS_DEFINITIVO/`:

* **`DEMANDA/`**: Tratamiento y escalado continuo del perfil de carga horaria comunitaria para 20 viviendas (8.760 horas/año) mediante `crear_perfil_comunidad.py`.
* **`RECURSO_SOLAR/`**: Ingesta del archivo meteorológico TMY (`tmy_ESTUDIO_TFM.epw`, ERA5/PVGIS) y modelación de la generación fotovoltaica unitaria de referencia en PySAM (`PVWattsv8`) mediante `analisis_recurso_solar_colombia.py`.
* **`SIMULACION/`**: Núcleo analítico de simulación tecno-económica y despacho:
  * `params.py`: Única fuente de verdad paramétrica (especificaciones de catálogo y parámetros económicos).
  * `despacho_pysam.py`: Simulador horario del balance en nudo AC con regímenes de operación y restricción técnica anti-*wet stacking* (30 % de carga mínima diésel con derivación a batería).
  * `comparar_despacho.py`: Simulación comparativa entre estrategias *Load Following* (LF) y *Cycle Charging* (CC).
  * `barrido_optimizacion.py`: Optimización exhaustiva en malla determinista ($17 \times 72 = 1.224$ configuraciones) y extracción de la frontera de Pareto bi-objetivo (LCOE vs. CO₂).
  * `analisis_sensibilidad.py`: Flujos de caja descontados a 25 años (DCF), reposición de activos y análisis de sensibilidad (diagrama de Tornado).
  * `generar_diagrama_flujo.py`: Generación del diagrama de arquitectura metodológica en cuatro fases.

---

## Requisitos e Instalación

El proyecto está desarrollado en **Python 3.11** (compatible con Python $\ge 3.10$).

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/gomez-ke/TFM_repository.git
   cd TFM_repository
   ```

2. Crear y activar un entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate       # En Linux / macOS
   # venv\Scripts\activate        # En Windows
   ```

3. Instalar dependencias científicas:
   ```bash
   pip install -r requirements.txt
   ```

---

## Ejecución

Para ejecutar la optimización completa en malla determinista (1.224 casos anuales):
```bash
cd ANALISIS_DEFINITIVO/SIMULACION
python barrido_optimizacion.py
```
