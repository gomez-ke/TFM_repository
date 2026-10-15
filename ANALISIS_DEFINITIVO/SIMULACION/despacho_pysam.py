"""
=============================================================================
despacho_pysam.py — Motor de simulación energética y despacho horario en PySAM
=============================================================================
Caso de estudio: Comunidad rural aislada (20 viviendas), Cundinamarca-Meta, Colombia.
Trabajo Fin de Máster — Metodología de simulación con PySAM (NREL).

Este módulo implementa:
  1. Simulación fotovoltaica horaria de alta fidelidad con PySAM (Pvwattsv8)
     a partir del archivo climático TMY (EPW).
  2. Balance de potencias instantáneo en nudo AC (Kirchhoff).
  3. Lógicas de despacho:
     - 'LF' (Load Following): Diésel solo cubre déficit residual, con restricción
       anti-wet stacking (cota mínima 30% = 4.5 kW) y desvío de potencia sobrante a BESS.
     - 'CC' (Cycle Charging): Diésel opera a plena potencia nominal (15 kW) recargando BESS.
  4. Evaluación financiera completa a 25 años con flujos de reemplazo de componentes:
     - BESS (años 7, 14, 21), Inversor (año 12), Grupo Diésel (año 20).
     - LCOE, VAN, TIR y Payback frente al escenario base 100% diésel.
=============================================================================
"""

import os
import sys
import numpy as np
import pandas as pd
import PySAM.Pvwattsv8 as pv_mod

# Importar parámetros auditados del proyecto
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)
import params

# Rutas estándar del proyecto
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
DEMAND_PATH = os.path.join(PROJECT_ROOT, 'ANALISIS_DEFINITIVO', 'DEMANDA', 'demanda_20_viviendas.csv')
EPW_PATH = os.path.join(PROJECT_ROOT, 'ANALISIS_DEFINITIVO', 'RECURSO_SOLAR', 'tmy_ESTUDIO_TFM.epw')


class MicrogridSimulator:
    """Simulador horario de microrred híbrida FV-BESS-Diésel con PySAM."""

    def __init__(self, demand_csv=DEMAND_PATH, epw_file=EPW_PATH):
        self.demand_csv = demand_csv
        self.epw_file = epw_file
        
        # Cargar y verificar demanda
        if not os.path.exists(self.demand_csv):
            raise FileNotFoundError(f"Archivo de demanda no encontrado: {self.demand_csv}")
        df_dem = pd.read_csv(self.demand_csv, header=None)
        self.demand_kw = df_dem[0].values / 1000.0  # Convertir W a kW
        self.annual_demand_kwh = float(self.demand_kw.sum())
        
        # Generar perfil solar unitario de referencia (1 kWp) con PySAM
        self.pv_unit_hourly_kw = self._simular_pv_unitario_pysam()
        self.annual_pv_unit_kwh = float(self.pv_unit_hourly_kw.sum())

    def _simular_pv_unitario_pysam(self) -> np.ndarray:
        """
        Ejecuta PySAM.Pvwattsv8 para 1 kWp de referencia en el emplazamiento TMY.
        Configura la geometría calculada (Anexo B) y los factores de pérdida de params.py.
        """
        if not os.path.exists(self.epw_file):
            raise FileNotFoundError(f"Archivo EPW no encontrado: {self.epw_file}")

        model = pv_mod.default('PVWattsNone')
        model.SolarResource.solar_resource_file = self.epw_file
        model.SystemDesign.system_capacity = 1.0  # 1 kWp de referencia
        model.SystemDesign.tilt = params.PV["tilt_deg"]  # 10.0° criterio constructivo UPME/DNP
        model.SystemDesign.azimuth = params.PV["azimuth_deg"]  # 180.0° Sur
        
        # Factor de pérdidas global del sistema (derate)
        derate_factor = params.pv_derate_factor()
        model.SystemDesign.losses = (1.0 - derate_factor) * 100.0  # ~11.56%
        
        # Inversor
        model.SystemDesign.inv_eff = params.INV["eta_sim"] * 100.0  # 94.0%
        model.SystemDesign.dc_ac_ratio = params.INV["DC_AC_ratio"]   # 1.20
        
        model.execute()
        return np.array(model.Outputs.gen)  # Array de 8.760 horas [kW]

    def simular_despacho(
        self,
        P_pv_kw: float,
        N_bess: int,
        estrategia: str = 'LF',
        P_diesel_kw: float = None,
        return_hourly: bool = False
    ) -> dict:
        """
        Simula el despacho horario completo (8.760 horas) para una configuración dada.

        Parámetros:
        -----------
        P_pv_kw     : Potencia pico fotovoltaica instalada [kWp]
        N_bess      : Número de módulos de batería Victron LFP de 5.12 kWh en paralelo
        estrategia  : 'LF' (Load Following) o 'CC' (Cycle Charging)
        P_diesel_kw : Potencia nominal diésel [kW] (por defecto params.DIESEL['P_nom_kW'] = 15 kW)
        return_hourly: Si True, incluye series horarias en el resultado
        """
        if P_diesel_kw is None:
            P_diesel_kw = params.DIESEL["P_nom_kW"]

        # Componentes y capacidades
        E_bess_kwh = params.bess_bank_energy_kWh(N_bess)
        P_bess_max_kw = params.bess_bank_power_kW(N_bess) if N_bess > 0 else 0.0

        # Eficiencias de BESS e Inversor
        eta_inv = params.INV["eta_sim"]       # 0.94
        eta_bess_one_way = np.sqrt(params.BESS["RTE"])  # sqrt(0.92) ≈ 0.959166

        soc_min_abs = E_bess_kwh * params.BESS["SoC_min"]  # 20%
        soc_max_abs = E_bess_kwh * params.BESS["SoC_max"]  # 95%
        soc_t = E_bess_kwh * params.BESS["SoC_0"]          # 50% inicial

        # Generación solar horaria en nudo AC
        P_pv_hourly = self.pv_unit_hourly_kw * P_pv_kw

        # Diésel
        P_dg_min = P_diesel_kw * params.DIESEL["P_min_pu"]  # 4.5 kW (30% cota anti-wet stacking)
        fc_a = params.DIESEL["fc_a"]
        fc_b = params.DIESEL["fc_b"]
        ef_co2 = params.DIESEL["ef_CO2_kg_L"]

        # Variables acumuladoras
        tot_pv_gen = float(P_pv_hourly.sum())
        tot_pv_used = 0.0
        tot_curtailment = 0.0
        tot_diesel_kwh = 0.0
        tot_fuel_liters = 0.0
        tot_co2_kg = 0.0
        tot_hours_dg = 0
        tot_starts_dg = 0
        tot_bess_discharge_kwh = 0.0
        tot_bess_charge_kwh = 0.0
        unmet_load_kwh = 0.0

        dg_running_prev = False
        cc_charging_cycle = False  # Estado para Cycle Charging

        if return_hourly:
            h_pv_gen = P_pv_hourly
            h_pv_used = np.zeros(8760)
            h_bess_dis = np.zeros(8760)
            h_bess_ch = np.zeros(8760)
            h_soc = np.zeros(8760)
            h_dg = np.zeros(8760)
            h_curt = np.zeros(8760)
            h_fuel = np.zeros(8760)

        for t in range(8760):
            p_dem = self.demand_kw[t]
            p_pv = P_pv_hourly[t]
            net_load = p_dem - p_pv  # >0: déficit, <=0: superávit solar

            p_pv_used = 0.0
            p_bess_dis_ac = 0.0
            p_bess_ch_ac = 0.0
            p_dg = 0.0
            p_curt = 0.0
            p_unmet = 0.0

            if net_load <= 0:
                # =========================================================
                # Régimen 1: Superávit Solar
                # =========================================================
                excess = -net_load
                p_pv_used = p_dem
                cc_charging_cycle = False  # Si hay superávit solar, se apaga diésel en CC

                if N_bess > 0 and soc_t < soc_max_abs:
                    # Capacidad máxima de recarga admisible por SoC y C-rate
                    e_room = soc_max_abs - soc_t
                    max_ch_dc = min(P_bess_max_kw, e_room / eta_bess_one_way)
                    max_ch_ac = max_ch_dc / eta_inv
                    
                    p_bess_ch_ac = min(excess, max_ch_ac)
                    e_stored = p_bess_ch_ac * eta_inv * eta_bess_one_way
                    soc_t += e_stored
                    p_pv_used += p_bess_ch_ac
                    p_curt = excess - p_bess_ch_ac
                else:
                    p_curt = excess

            else:
                # =========================================================
                # Régimen 2: Déficit Renovable
                # =========================================================
                p_pv_used = p_pv
                deficit = net_load

                if estrategia == 'CC' and cc_charging_cycle:
                    # En CC, si el ciclo diésel ya está activo, el diésel genera a plena carga
                    # hasta que la batería alcance soc_max o 80% SoC
                    p_dg_target = P_diesel_kw
                    p_dg = p_dg_target
                    
                    if p_dg >= deficit:
                        p_surplus = p_dg - deficit
                        # Intentar inyectar excedente diésel a la batería
                        if N_bess > 0 and soc_t < soc_max_abs:
                            e_room = soc_max_abs - soc_t
                            max_ch_dc = min(P_bess_max_kw, e_room / eta_bess_one_way)
                            max_ch_ac = max_ch_dc / eta_inv
                            p_bess_ch_ac = min(p_surplus, max_ch_ac)
                            e_stored = p_bess_ch_ac * eta_inv * eta_bess_one_way
                            soc_t += e_stored
                            p_curt = p_surplus - p_bess_ch_ac
                            if soc_t >= 0.80 * E_bess_kwh:
                                cc_charging_cycle = False  # Fin del ciclo CC
                        else:
                            p_curt = p_surplus
                            cc_charging_cycle = False
                    else:
                        p_unmet = deficit - p_dg

                else:
                    # Prioridad 1: Descargar BESS para cubrir déficit
                    if N_bess > 0 and soc_t > soc_min_abs:
                        e_avail = soc_t - soc_min_abs
                        max_dis_dc = min(P_bess_max_kw, e_avail * eta_bess_one_way)
                        max_dis_ac = max_dis_dc * eta_inv
                        
                        p_bess_dis_ac = min(deficit, max_dis_ac)
                        e_drawn = p_bess_dis_ac / (eta_inv * eta_bess_one_way)
                        soc_t -= e_drawn
                        remaining_def = deficit - p_bess_dis_ac
                    else:
                        remaining_def = deficit

                    # Prioridad 2: Generador Diésel para déficit residual
                    if remaining_def > 1e-4:
                        if estrategia == 'LF':
                            # Load Following: Diésel genera lo necesario respetando carga mínima
                            p_dg = max(remaining_def, P_dg_min)
                            if p_dg > P_diesel_kw:
                                p_unmet = p_dg - P_diesel_kw
                                p_dg = P_diesel_kw
                            
                            # Si generó más de lo necesario por anti-wet stacking, derivar a BESS
                            surplus_dg = p_dg - remaining_def
                            if surplus_dg > 1e-4 and N_bess > 0 and soc_t < soc_max_abs:
                                e_room = soc_max_abs - soc_t
                                max_ch_dc = min(P_bess_max_kw, e_room / eta_bess_one_way)
                                max_ch_ac = max_ch_dc / eta_inv
                                ch_dg_ac = min(surplus_dg, max_ch_ac)
                                e_stored = ch_dg_ac * eta_inv * eta_bess_one_way
                                soc_t += e_stored
                                p_bess_ch_ac += ch_dg_ac
                                p_curt = surplus_dg - ch_dg_ac
                            elif surplus_dg > 1e-4:
                                p_curt = surplus_dg

                        elif estrategia == 'CC':
                            # Cycle Charging: Se inicia ciclo diésel a plena carga nominal
                            p_dg = P_diesel_kw
                            cc_charging_cycle = True
                            surplus_dg = p_dg - remaining_def
                            if surplus_dg > 0 and N_bess > 0 and soc_t < soc_max_abs:
                                e_room = soc_max_abs - soc_t
                                max_ch_dc = min(P_bess_max_kw, e_room / eta_bess_one_way)
                                max_ch_ac = max_ch_dc / eta_inv
                                ch_dg_ac = min(surplus_dg, max_ch_ac)
                                e_stored = ch_dg_ac * eta_inv * eta_bess_one_way
                                soc_t += e_stored
                                p_bess_ch_ac += ch_dg_ac
                                p_curt = surplus_dg - ch_dg_ac
                            elif surplus_dg > 0:
                                p_curt = surplus_dg

            # Combustible y emisiones
            fuel_t = (fc_a * P_diesel_kw + fc_b * p_dg) if p_dg > 0 else 0.0
            co2_t = fuel_t * ef_co2

            # Arranques
            dg_running = (p_dg > 0)
            if dg_running and not dg_running_prev:
                tot_starts_dg += 1
            if dg_running:
                tot_hours_dg += 1
            dg_running_prev = dg_running

            # Acumuladores
            tot_pv_used += p_pv_used
            tot_curtailment += p_curt
            tot_diesel_kwh += p_dg
            tot_fuel_liters += fuel_t
            tot_co2_kg += co2_t
            tot_bess_discharge_kwh += p_bess_dis_ac
            tot_bess_charge_kwh += p_bess_ch_ac
            unmet_load_kwh += p_unmet

            if return_hourly:
                h_pv_used[t] = p_pv_used
                h_bess_dis[t] = p_bess_dis_ac
                h_bess_ch[t] = p_bess_ch_ac
                h_soc[t] = (soc_t / E_bess_kwh) if N_bess > 0 else 0.0
                h_dg[t] = p_dg
                h_curt[t] = p_curt
                h_fuel[t] = fuel_t

        # Ciclos equivalentes anuales BESS
        dod_eff = params.BESS["DoD_max"]  # 0.80
        cycles_annual = (tot_bess_discharge_kwh / (E_bess_kwh * dod_eff * eta_inv)) if N_bess > 0 else 0.0

        # Fracción Renovable (RF %)
        rf_pct = max(0.0, (1.0 - (tot_diesel_kwh / self.annual_demand_kwh))) * 100.0

        # Cómputo Económico a 25 años
        econ_metrics = self.calcular_metricas_economicas(
            P_pv_kw=P_pv_kw,
            N_bess=N_bess,
            P_diesel_kw=P_diesel_kw,
            fuel_liters_annual=tot_fuel_liters,
            hours_dg_annual=tot_hours_dg,
            unmet_kwh=unmet_load_kwh
        )

        res = {
            'P_pv_kw': P_pv_kw,
            'N_bess': N_bess,
            'E_bess_kwh': E_bess_kwh,
            'estrategia': estrategia,
            'annual_demand_kwh': self.annual_demand_kwh,
            'pv_gen_kwh': tot_pv_gen,
            'pv_used_kwh': tot_pv_used,
            'curtailment_kwh': tot_curtailment,
            'diesel_gen_kwh': tot_diesel_kwh,
            'fuel_liters': tot_fuel_liters,
            'co2_tons': tot_co2_kg / 1000.0,
            'hours_dg': tot_hours_dg,
            'starts_dg': tot_starts_dg,
            'bess_discharge_kwh': tot_bess_discharge_kwh,
            'bess_charge_kwh': tot_bess_charge_kwh,
            'bess_cycles': cycles_annual,
            'renewable_fraction_pct': rf_pct,
            'unmet_load_kwh': unmet_load_kwh,
            **econ_metrics
        }

        if return_hourly:
            res['hourly'] = {
                'demand': self.demand_kw,
                'pv_gen': h_pv_gen,
                'pv_used': h_pv_used,
                'bess_dis': h_bess_dis,
                'bess_ch': h_bess_ch,
                'soc': h_soc,
                'diesel': h_dg,
                'curtailment': h_curt,
                'fuel_liters': h_fuel,
            }

        return res

    def calcular_metricas_economicas(
        self,
        P_pv_kw: float,
        N_bess: int,
        P_diesel_kw: float,
        fuel_liters_annual: float,
        hours_dg_annual: int,
        unmet_kwh: float = 0.0
    ) -> dict:
        """Calcula CAPEX, OPEX anual, LCC, LCOE, VAN y Payback frente al caso base."""
        E_bess_kwh = params.bess_bank_energy_kWh(N_bess)
        P_inv_kw = (P_pv_kw / params.INV["DC_AC_ratio"]) if P_pv_kw > 0 else 0.0

        # CAPEX inicial
        capex_pv = P_pv_kw * params.ECON["capex_pv_USD_kWp"]
        capex_bess = E_bess_kwh * params.ECON["capex_bess_USD_kWh"]
        capex_inv = P_inv_kw * params.ECON["capex_inv_USD_kW"]
        capex_dg = P_diesel_kw * params.ECON["capex_diesel_USD_kW"]
        total_capex = capex_pv + capex_bess + capex_inv + capex_dg

        # OPEX anual base (sin combustible)
        opex_pv = P_pv_kw * params.ECON["opex_pv_USD_kWp_yr"]
        opex_bess = E_bess_kwh * params.ECON["opex_bess_USD_kWh_yr"]
        opex_inv = P_inv_kw * params.ECON["opex_inv_USD_kW_yr"]
        opex_dg = hours_dg_annual * params.ECON["opex_diesel_USD_h"]
        opex_fuel = fuel_liters_annual * params.ECON["diesel_price_USD_L"]
        total_opex_annual = opex_pv + opex_bess + opex_inv + opex_dg + opex_fuel

        # Flujos de reemplazo de componentes (params.replacement_cashflows)
        wacc = params.ECON["WACC"]  # 0.10
        T = params.ECON["T_years"]   # 25
        repl_flows = params.replacement_cashflows(E_bess_kwh, P_inv_kw, P_diesel_kw)

        # Coste de Ciclo de Vida Descontado (LCC)
        npv_opex = sum(total_opex_annual / ((1.0 + wacc) ** y) for y in range(1, T + 1))
        npv_repl = sum(cost / ((1.0 + wacc) ** yr) for yr, cost in repl_flows.items())
        total_lcc = total_capex + npv_opex + npv_repl

        # Factor de anualización de energía descontada
        npv_energy = sum(self.annual_demand_kwh / ((1.0 + wacc) ** y) for y in range(1, T + 1))
        lcoe = total_lcc / npv_energy

        # =========================================================
        # Escenario Base 100% Diésel de Referencia
        # =========================================================
        # Generador diésel operando 8.760 h para cubrir la demanda
        base_P_dg = params.DIESEL["P_nom_kW"]
        base_capex = base_P_dg * params.ECON["capex_diesel_USD_kW"]  # 7.500 USD
        
        # En el escenario base, el diésel genera p_dem en cada hora (respetando carga mínima 4.5 kW)
        base_fuel_hourly = np.where(
            self.demand_kw >= 4.5,
            params.DIESEL["fc_a"] * base_P_dg + params.DIESEL["fc_b"] * self.demand_kw,
            params.DIESEL["fc_a"] * base_P_dg + params.DIESEL["fc_b"] * 4.5
        )
        base_fuel_liters = float(base_fuel_hourly.sum())
        base_opex_fuel = base_fuel_liters * params.ECON["diesel_price_USD_L"]
        base_opex_maint = 8760 * params.ECON["opex_diesel_USD_h"]
        base_opex_annual = base_opex_fuel + base_opex_maint

        # Reemplazo de generador base en año 20
        base_repl_flows = {params.ECON["lifetime_diesel_yr"]: base_capex}
        base_npv_opex = sum(base_opex_annual / ((1.0 + wacc) ** y) for y in range(1, T + 1))
        base_npv_repl = sum(cost / ((1.0 + wacc) ** yr) for yr, cost in base_repl_flows.items())
        base_lcc = base_capex + base_npv_opex + base_npv_repl
        base_lcoe = base_lcc / npv_energy

        # =========================================================
        # Métricas de Rentabilidad Frente al Caso Base
        # =========================================================
        delta_capex = total_capex - base_capex
        delta_opex_annual = base_opex_annual - total_opex_annual

        # Flujos de caja netos anuales (Ahorros OPEX - Reemplazos híbrido + Reemplazos base)
        annual_net_cashflows = []
        for y in range(1, T + 1):
            repl_hybrid = repl_flows.get(y, 0.0)
            repl_base_yr = base_repl_flows.get(y, 0.0)
            net_cf = delta_opex_annual - repl_hybrid + repl_base_yr
            annual_net_cashflows.append(net_cf)

        # VAN (NPV)
        van = sum(cf / ((1.0 + wacc) ** y) for y, cf in enumerate(annual_net_cashflows, start=1)) - delta_capex

        # Payback Simple y Descontado
        cum_cf_simple = -delta_capex
        payback_simple = None
        for y, cf in enumerate(annual_net_cashflows, start=1):
            cum_cf_simple += cf
            if cum_cf_simple >= 0 and payback_simple is None:
                payback_simple = y - (cum_cf_simple / cf)
                break

        cum_cf_disc = -delta_capex
        payback_disc = None
        for y, cf in enumerate(annual_net_cashflows, start=1):
            disc_cf = cf / ((1.0 + wacc) ** y)
            cum_cf_disc += disc_cf
            if cum_cf_disc >= 0 and payback_disc is None:
                payback_disc = y - (cum_cf_disc / disc_cf)
                break

        return {
            'total_capex_USD': total_capex,
            'capex_pv_USD': capex_pv,
            'capex_bess_USD': capex_bess,
            'capex_inv_USD': capex_inv,
            'capex_dg_USD': capex_dg,
            'opex_annual_USD': total_opex_annual,
            'opex_fuel_annual_USD': opex_fuel,
            'opex_maint_dg_annual_USD': opex_dg,
            'total_lcc_USD': total_lcc,
            'lcoe_USD_kwh': lcoe,
            'base_lcoe_USD_kwh': base_lcoe,
            'base_fuel_liters': base_fuel_liters,
            'base_opex_annual_USD': base_opex_annual,
            'base_lcc_USD': base_lcc,
            'delta_capex_USD': delta_capex,
            'delta_opex_annual_USD': delta_opex_annual,
            'van_USD': van,
            'payback_simple_years': payback_simple if payback_simple else 25.0,
            'payback_discounted_years': payback_disc if payback_disc else 25.0,
        }


if __name__ == "__main__":
    print("=" * 65)
    print("  VERIFICACIÓN DEL MOTOR DE DESPACHO PySAM (despacho_pysam.py)")
    print("=" * 65)
    
    sim = MicrogridSimulator()
    print(f"Demanda Anual Cargada: {sim.annual_demand_kwh:,.2f} kWh/año")
    print(f"Generación Solar Unitaria PySAM: {sim.annual_pv_unit_kwh:,.2f} kWh/kWp/año")
    print()

    # Caso 1: Caso Base 100% Diésel
    print("[1/3] Evaluando Escenario Base 100% Diésel...")
    res_base = sim.simular_despacho(P_pv_kw=0.0, N_bess=0, estrategia='LF')
    print(f"  CAPEX Base: {res_base['total_capex_USD']:,.2f} USD")
    print(f"  Combustible Base: {res_base['fuel_liters']:,.2f} L/año")
    print(f"  Emisiones Base: {res_base['co2_tons']:,.2f} tCO2/año")
    print(f"  LCOE Base: {res_base['lcoe_USD_kwh']:.4f} USD/kWh")
    print()

    # Caso 2: Híbrido preliminar con Load Following (ejemplo: 25 kWp PV + 8 BESS = 40.96 kWh)
    print("[2/3] Evaluando Híbrido con Load Following (LF)...")
    res_lf = sim.simular_despacho(P_pv_kw=25.0, N_bess=8, estrategia='LF')
    print(f"  Fracción Renovable: {res_lf['renewable_fraction_pct']:.2f} %")
    print(f"  Combustible: {res_lf['fuel_liters']:,.2f} L/año (Ahorro: {(1 - res_lf['fuel_liters']/res_base['fuel_liters'])*100:.1f} %)")
    print(f"  Emisiones: {res_lf['co2_tons']:,.2f} tCO2/año")
    print(f"  Horas Diésel: {res_lf['hours_dg']:,} h/año (de 8.760 h)")
    print(f"  LCOE: {res_lf['lcoe_USD_kwh']:.4f} USD/kWh (Reducción: {(1 - res_lf['lcoe_USD_kwh']/res_base['lcoe_USD_kwh'])*100:.1f} %)")
    print(f"  VAN (25 años, 10% WACC): {res_lf['van_USD']:,.2f} USD")
    print(f"  Payback Simple: {res_lf['payback_simple_years']:.2f} años")
    print()

    # Caso 3: Mismo híbrido con Cycle Charging (CC)
    print("[3/3] Evaluando Híbrido con Cycle Charging (CC)...")
    res_cc = sim.simular_despacho(P_pv_kw=25.0, N_bess=8, estrategia='CC')
    print(f"  Fracción Renovable: {res_cc['renewable_fraction_pct']:.2f} %")
    print(f"  Combustible: {res_cc['fuel_liters']:,.2f} L/año")
    print(f"  Vertidos Solares (Curtailment): {res_cc['curtailment_kwh']:,.2f} kWh/año (vs LF: {res_lf['curtailment_kwh']:,.2f} kWh/año)")
    print(f"  LCOE: {res_cc['lcoe_USD_kwh']:.4f} USD/kWh")
    print("=" * 65)
