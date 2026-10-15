"""
=============================================================================
generar_diagrama_flujo.py — Diagrama de Flujo Metodológico Integrado del TFM
=============================================================================
Genera una figura vectorial de alta resolución (300 DPI) que ilustra la
arquitectura modular completa de la simulación tecno-económica en 4 Fases:
  1. Ingesta de datos de entrada y modelado solar base (TMY + PySAM)
  2. Simulador analítico de despacho en nudo AC (Load Following anti-wet-stacking)
  3. Optimización determinista en malla (Grid Search 1.224 casos + Frente de Pareto)
  4. Evaluación financiera a 25 años y análisis de sensibilidad (DCF + Sensibilidad)
Diseñado con texto sintético de alta legibilidad alineado con el Capítulo 6.
=============================================================================
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
FIG_DIR = os.path.join(PROJECT_ROOT, 'figuras')
os.makedirs(FIG_DIR, exist_ok=True)
OUT_PATH = os.path.join(FIG_DIR, 'diagrama_flujo_metodologico.png')

def plot_methodological_flowchart():
    fig = plt.figure(figsize=(16, 10.8), dpi=300)
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10.8)
    ax.axis('off')

    # Paleta de colores sobria y profesional
    c_input = '#1E3A8A'     # Azul marino elegante
    c_disp  = '#0D9488'     # Verde azulado / Teal
    c_opt   = '#D97706'     # Ámbar oscuro / Naranja
    c_fin   = '#059669'     # Esmeralda finanzas y viabilidad
    c_text_dark = '#0F172A'
    c_arrow = '#334155'     # Gris pizarra oscuro

    # Función auxiliar para dibujar tarjetas modulares amplias y legibles
    def draw_card(x, y, w, h, header_bg, title, subtitle, items, border_color='#94A3B8'):
        # Sombra suave
        shadow = patches.FancyBboxPatch((x + 0.08, y - 0.08), w, h,
                                       boxstyle="round,pad=0.10,rounding_size=0.22",
                                       fc='#E2E8F0', ec='none', zorder=1)
        ax.add_patch(shadow)

        # Caja principal blanca
        box = patches.FancyBboxPatch((x, y), w, h,
                                    boxstyle="round,pad=0.10,rounding_size=0.22",
                                    fc='#FFFFFF', ec=border_color, lw=2.0, zorder=2)
        ax.add_patch(box)

        # Encabezado con color temático
        header_h = 0.72
        header_box = patches.FancyBboxPatch((x, y + h - header_h), w, header_h,
                                           boxstyle="round,pad=0.10,rounding_size=0.22",
                                           fc=header_bg, ec=header_bg, lw=0, zorder=3)
        ax.add_patch(header_box)

        # Parche rectangular para unión perfecta del encabezado
        mid_strip = patches.Rectangle((x - 0.10, y + h - header_h), w + 0.20, 0.32,
                                      fc=header_bg, ec=header_bg, zorder=3)
        ax.add_patch(mid_strip)

        # Título del encabezado (fuente grande y clara)
        ax.text(x + w / 2, y + h - header_h / 2 + 0.03, title,
                ha='center', va='center', color='white', fontsize=12.2, fontweight='bold', zorder=4)

        # Subtítulo descriptivo
        if subtitle:
            ax.text(x + 0.35, y + h - header_h - 0.30, subtitle,
                    ha='left', va='center', color=header_bg, fontsize=10.2, fontweight='bold', fontstyle='italic', zorder=4)

        # Viñetas de texto (4 ítems concisos, espaciado generoso, fuente grande 10.8 pt)
        start_y = y + h - header_h - 0.68
        step_y = 0.60
        for i, item in enumerate(items):
            cur_y = start_y - i * step_y
            ax.plot(x + 0.35, cur_y, marker='s', markersize=5.8, color=header_bg, zorder=4)
            ax.text(x + 0.58, cur_y, item, ha='left', va='center',
                    color=c_text_dark, fontsize=10.8, zorder=4)

    # Función para flechas conectoras de flujo
    def draw_arrow(x1, y1, x2, y2, label=None, label_pos=(0, 0), connectionstyle="arc3,rad=0", color=c_arrow):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=2.4, mutation_scale=18,
                                    connectionstyle=connectionstyle),
                    zorder=5)
        if label:
            lx = (x1 + x2) / 2 + label_pos[0]
            ly = (y1 + y2) / 2 + label_pos[1]
            ax.text(lx, ly, label, ha='center', va='center', fontsize=9.6,
                    color=color, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.25", fc='#F8FAFC', ec=color, lw=1.2), zorder=6)

    # -------------------------------------------------------------------------
    # ENCABEZADO PRINCIPAL DE LA FIGURA
    # -------------------------------------------------------------------------
    ax.text(8.0, 10.35, "ARQUITECTURA METODOLÓGICA DE LA SIMULACIÓN Y OPTIMIZACIÓN",
            ha='center', va='center', fontsize=16.0, fontweight='bold', color='#0F172A')
    ax.text(8.0, 9.95, "Flujo computacional integrado en 4 Fases: Ingesta PySAM + Despacho AC + Grid Search + Finanzas DCF",
            ha='center', va='center', fontsize=11.2, color='#475569', fontstyle='italic')

    # Coordenadas y dimensiones de las tarjetas (espacio central de 2.20 para flechas limpias)
    card_w = 6.10
    card_h = 3.90
    x_left = 0.85
    x_right = 9.05
    y_top = 5.25
    y_bot = 0.65

    # -------------------------------------------------------------------------
    # DIBUJO DE LAS TARJETAS (4 FASES SINTÉTICAS)
    # -------------------------------------------------------------------------

    # FASE 1: Ingesta de Datos de Entrada (Superior Izquierda)
    draw_card(
        x=x_left, y=y_top, w=card_w, h=card_h,
        header_bg=c_input,
        title="FASE 1: INGESTA DE DATOS DE ENTRADA",
        subtitle="Datos climatológicos, demanda comunitaria y motor PySAM",
        items=[
            "Series TMY (PVGIS EPW, 8.760 h) y demanda de 20 viviendas.",
            "Base de parámetros centralizada en params.py (JA Solar y Victron).",
            "PySAM Pvwattsv8: transposición Perez y pérdidas de sistema.",
            "Generación unitaria normalizada anual P_pv,norm(t)."
        ], border_color=c_input
    )

    # FASE 2: Simulador Analítico de Despacho en Nudo AC (Superior Derecha)
    draw_card(
        x=x_right, y=y_top, w=card_w, h=card_h,
        header_bg=c_disp,
        title="FASE 2: SIMULADOR DE DESPACHO EN NUDO AC",
        subtitle="Balance dinámico horario y control anti-wet stacking",
        items=[
            "Balance de potencia activa: P_neto(t) = P_pv(t) - P_dem(t).",
            "Prioridad BESS: recarga en superávit y descarga en déficit.",
            "Restricción técnica diésel: carga mínima 30% (4,5 kW).",
            "Derivación de excedente térmico (4,5 kW - P_def) a batería."
        ], border_color=c_disp
    )

    # FASE 3: Optimización Determinista en Malla y Frente de Pareto (Inferior Derecha)
    draw_card(
        x=x_right, y=y_bot, w=card_w, h=card_h,
        header_bg=c_opt,
        title="FASE 3: OPTIMIZACIÓN DETERMINISTA Y PARETO",
        subtitle="Barrido paramétrico en malla (Grid Search) sobre catálogo real",
        items=[
            "Malla discreta: 17 BESS × 72 PV (1.224 configuraciones reales).",
            "Simulación horaria anual vectorizada en < 20 segundos.",
            "Filtro de dominancia de Pareto bi-objetivo: Min LCOE vs Min CO2.",
            "Identificación de soluciones clave: P1 (LCOE), P2 y P3."
        ], border_color=c_opt
    )

    # FASE 4: Evaluación Financiera a 25 Años (Inferior Izquierda)
    draw_card(
        x=x_left, y=y_bot, w=card_w, h=card_h,
        header_bg=c_fin,
        title="FASE 4: EVALUACIÓN FINANCIERA A 25 AÑOS",
        subtitle="Flujos descontados (DCF) y análisis de sensibilidad macroeconómica",
        items=[
            "Flujos netos a 25 años (WACC 10%) frente a caso base diésel.",
            "Cronograma de reemplazo: BESS (7, 14, 21), Inversor (12) y Diésel.",
            "Indicadores de bancabilidad: LCOE, VAN, TIR y Payback.",
            "Análisis de sensibilidad: diésel, BESS, inversión FV y WACC."
        ], border_color=c_fin
    )

    # -------------------------------------------------------------------------
    # CONECTORES Y FLECHAS DE FLUJO (con separación limpia respecto a las tarjetas)
    # -------------------------------------------------------------------------

    # 1 -> 2: Horizontal superior
    draw_arrow(x1=x_left + card_w + 0.12, y1=y_top + card_h * 0.50,
               x2=x_right - 0.12, y2=y_top + card_h * 0.50,
               label="Series horarias y P_pv,norm(t)", label_pos=(0, 0.30), color=c_input)

    # 2 -> 3: Vertical derecho descendente
    draw_arrow(x1=x_right + card_w * 0.50, y1=y_top - 0.12,
               x2=x_right + card_w * 0.50, y2=y_bot + card_h + 0.12,
               label="Bucle de despacho 8.760 h", label_pos=(0.42, 0), color=c_disp)

    # 3 -> 4: Horizontal inferior
    draw_arrow(x1=x_right - 0.12, y1=y_bot + card_h * 0.50,
               x2=x_left + card_w + 0.12, y2=y_bot + card_h * 0.50,
               label="Frontera de Pareto (P1, P2, P3)", label_pos=(0, 0.30), color=c_opt)

    # Guardar figura
    plt.tight_layout()
    plt.savefig(OUT_PATH, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Diagrama de flujo metodológico generado con éxito en: {OUT_PATH}")

if __name__ == '__main__':
    plot_methodological_flowchart()
