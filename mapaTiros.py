import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.patches as patches

# ==========================================
# 1. CONFIGURACIÓN E INTELIGENCIA DINÁMICA (WHITELIST)
# ==========================================
carpeta_datos = './mapas_tiros'
umbral_usg = 10.0
umbral_eff = 10.0
umbral_pts = 12.0 # NUEVO: Filtro para "Chuckers" (Tiradores ineficientes de alto volumen)

print("Iniciando Motor Visual de Mapas de Tiro y Momentum...\n")

equipos_interes = [
    "CLARIDAD", "BURZACO", "ATENEO", "HURACAN", "HURACÁN", 
    "TEMPERLEY", "GALICIA", "INDIOS LIGA PROXIMA B"
]

equipos_detectados = {}
for archivo in os.listdir(carpeta_datos):
    if archivo.endswith('.json') or archivo.endswith('.txt'):
        try:
            with open(os.path.join(carpeta_datos, archivo), 'r', encoding='utf-8') as f:
                data = json.load(f)
                p = data.get("partido", {})
                
                def validar_equipo(id_eq, nombre_eq):
                    if not nombre_eq: return
                    nombre_upper = nombre_eq.upper()
                    for eq_blanco in equipos_interes:
                        if eq_blanco in nombre_upper or nombre_upper in eq_blanco:
                            equipos_detectados[id_eq] = nombre_eq
                            break

                if "idlocal" in p: validar_equipo(p["idlocal"], p.get("local"))
                if "idvisitante" in p: validar_equipo(p["idvisitante"], p.get("visitante"))
        except: pass

if not equipos_detectados:
    print("[!] No se encontraron equipos de tu lista de interés en mapas_tiros.")
    exit()

print("RADARES VISUALES ACTIVOS (Solo rivales directos):")
lista_equipos = list(equipos_detectados.items())
for i, (eq_id, eq_nom) in enumerate(lista_equipos):
    print(f" [{i+1}] {eq_nom}")

try:
    seleccion = int(input("\n¿A qué equipo deseas generar los mapas y el Momentum?: ")) - 1
    id_objetivo = lista_equipos[seleccion][0]
    nombre_objetivo = lista_equipos[seleccion][1]
except:
    print("[!] Selección inválida. Saliendo.")
    exit()

nombre_archivo_limpio = "".join(x for x in nombre_objetivo if x.isalnum() or x in " _-")
archivo_excel = f'{nombre_archivo_limpio}_Scouting_Total.xlsx'

try:
    df_adv = pd.read_excel(archivo_excel, sheet_name='Métricas Avanzadas')
    # FILTRO COMBINADO: Si es de élite (USG y EFF) O si simplemente anota muchos puntos (Chuckers)
    condicion_elite = (df_adv['USG%'] >= umbral_usg) & (df_adv['EFF'] >= umbral_eff)
    condicion_volumen = (df_adv['PTS_PROMEDIO'] >= umbral_pts)
    jugadores_elite = df_adv[condicion_elite | condicion_volumen]['JUGADOR'].tolist()
    print(f"\nFiltro aplicado. Jugadores a mapear de {nombre_objetivo}: {len(jugadores_elite)}")
except Exception as e:
    print(f"[!] Error leyendo el Excel. ¿Ejecutaste el main.py para este equipo primero? Error: {e}")
    exit()

# ==========================================
# 2. EXTRACCIÓN DE COORDENADAS Y MOMENTUM
# ==========================================
datos_tiros = []
total_partidos = 0
datos_momentum = {
    1: {"pts_fav": 0, "pts_con": 0, "fga": 0, "fgm": 0},
    2: {"pts_fav": 0, "pts_con": 0, "fga": 0, "fgm": 0},
    3: {"pts_fav": 0, "pts_con": 0, "fga": 0, "fgm": 0},
    4: {"pts_fav": 0, "pts_con": 0, "fga": 0, "fgm": 0}
}

for nombre_archivo in os.listdir(carpeta_datos):
    if nombre_archivo.endswith('.json') or nombre_archivo.endswith('.txt'):
        ruta_completa = os.path.join(carpeta_datos, nombre_archivo)
        
        with open(ruta_completa, 'r', encoding='utf-8') as archivo:
            try: datos_partido = json.load(archivo)
            except: continue
            
            p = datos_partido.get("partido", {})
            local_id = p.get("idlocal")
            visitante_id = p.get("idvisitante")
            
            if local_id != id_objetivo and visitante_id != id_objetivo:
                continue
            
            total_partidos += 1
            is_local = (local_id == id_objetivo)
            
            for per in p.get("periodos", []):
                q = per.get("periodo")
                if q in [1, 2, 3, 4]:
                    p_loc = per.get("tanteo_periodo_local", 0)
                    p_vis = per.get("tanteo_periodo_visitante", 0)
                    if is_local:
                        datos_momentum[q]['pts_fav'] += p_loc
                        datos_momentum[q]['pts_con'] += p_vis
                    else:
                        datos_momentum[q]['pts_fav'] += p_vis
                        datos_momentum[q]['pts_con'] += p_loc
            
            mapa = datos_partido.get("mapadetiro", {})
            tiros = mapa.get("tiros", [])
            
            mapa_nombres = {}
            for j in mapa.get("jugadoreslocales", []) + mapa.get("jugadoresvisitantes", []):
                mapa_nombres[str(j.get("componente_id"))] = j.get("nombre")

            for tiro in tiros:
                if tiro.get("equipo_id") == id_objetivo:
                    q = tiro.get("numero_periodo")
                    if q in [1, 2, 3, 4]:
                        datos_momentum[q]['fga'] += 1
                        if tiro.get("metido") == 1:
                            datos_momentum[q]['fgm'] += 1

                    str_x = str(tiro.get("posicion_x", "0")).replace('%', '')
                    str_y = str(tiro.get("posicion_y", "0")).replace('%', '')
                    try:
                        x_raw = float(str_x)
                        y_raw = float(str_y)
                    except ValueError: continue
                    
                    if x_raw > 50:
                        x = 100 - x_raw
                        y = 100 - y_raw
                    else:
                        x = x_raw
                        y = y_raw
                    
                    comp_id = str(tiro.get("componente_id"))
                    datos_tiros.append({
                        "JUGADOR": mapa_nombres.get(comp_id, "Desconocido"),
                        "X": x, "Y": y,
                        "RESULTADO": "Anotado" if tiro.get("metido") == 1 else "Fallado",
                        "TIPO": "3P" if "3P" in str(tiro.get("accion_tipo", "")) else "2P"
                    })

if not datos_tiros:
    print(f"[!] No se encontraron datos para {nombre_objetivo}.")
    exit()

df_tiros = pd.DataFrame(datos_tiros)

# ==========================================
# 3. MOTORES VISUALES (CANCHA Y GRÁFICOS)
# ==========================================
def dibujar_media_cancha():
    fig, ax = plt.subplots(figsize=(8.4, 9.0))
    ax.set_facecolor('#f4f4f4')
    ax.set_xlim(0, 50)
    ax.set_ylim(0, 100)
    
    ax.plot([0, 50], [0, 0], color='black', lw=2, zorder=3)
    ax.plot([0, 50], [100, 100], color='black', lw=2, zorder=3)
    ax.plot([0, 0], [0, 100], color='black', lw=2, zorder=3)
    ax.plot([50, 50], [0, 100], color='black', lw=2, zorder=3)
    
    x_hoop = 5.625
    x_backboard = 4.286
    
    ax.plot([x_backboard, x_backboard], [44, 56], color='black', lw=2, zorder=3)
    aro = patches.Ellipse((x_hoop, 50), width=1.607, height=3.0, fill=False, color='#e65c00', lw=2, zorder=3)
    ax.add_patch(aro)
    
    pintura = patches.Rectangle((0, 33.666), 20.714, 32.667, linewidth=2, edgecolor='black', facecolor='none', zorder=3)
    ax.add_patch(pintura)
    
    zona_rest = patches.Arc((x_hoop, 50), 8.929, 16.667, angle=0, theta1=-90, theta2=90, color='black', lw=2, zorder=3)
    ax.add_patch(zona_rest)
    
    tl_ext = patches.Arc((20.714, 50), 12.857, 24.0, angle=0, theta1=-90, theta2=90, color='black', lw=2, zorder=3)
    tl_int = patches.Arc((20.714, 50), 12.857, 24.0, angle=0, theta1=90, theta2=270, color='black', lw=2, linestyle='dashed', zorder=3)
    ax.add_patch(tl_ext)
    ax.add_patch(tl_int)
    
    x_intersect = 10.679
    ax.plot([0, x_intersect], [6.0, 6.0], color='black', lw=2, zorder=3) 
    ax.plot([0, x_intersect], [94.0, 94.0], color='black', lw=2, zorder=3) 
    
    t = np.linspace(np.radians(-77.877), np.radians(77.877), 100)
    x_arc = x_hoop + (48.214 / 2) * np.cos(t)
    y_arc = 50 + (90.0 / 2) * np.sin(t)
    ax.plot(x_arc, y_arc, color='black', lw=2, zorder=3)
    
    circulo_central = patches.Arc((50, 50), 12.857, 24.0, angle=0, theta1=90, theta2=270, color='black', lw=2, zorder=3)
    ax.add_patch(circulo_central)
    
    ax.set_xticks([])
    ax.set_yticks([])
    return fig, ax

def generar_grafico_momentum(datos_mom, total_pj, titulo, nombre_archivo):
    cuartos = ['1Q', '2Q', '3Q', '4Q']
    diferenciales = []
    efectividad_fg = []
    
    for q in [1, 2, 3, 4]:
        net = (datos_mom[q]['pts_fav'] - datos_mom[q]['pts_con']) / total_pj if total_pj > 0 else 0
        diferenciales.append(net)
        
        fga = datos_mom[q]['fga']
        fgm = datos_mom[q]['fgm']
        pct = (fgm / fga * 100) if fga > 0 else 0
        efectividad_fg.append(pct)

    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.set_facecolor('#f9f9f9')
    
    colores = ['#33cc33' if val >= 0 else '#ff4d4d' for val in diferenciales]
    barras = ax1.bar(cuartos, diferenciales, color=colores, alpha=0.85, width=0.5, edgecolor='black')
    ax1.set_ylabel('Diferencial de Puntos Promedio (+ / -)', fontweight='bold', fontsize=11)
    ax1.axhline(0, color='black', lw=1.5)
    
    for barra in barras:
        yval = barra.get_height()
        ax1.text(barra.get_x() + barra.get_width()/2, yval + (0.5 if yval>=0 else -1.2), 
                 f'{round(yval, 1)}', ha='center', va='bottom', fontweight='bold')

    ax2 = ax1.twinx()
    ax2.plot(cuartos, efectividad_fg, color='#0044cc', marker='o', lw=3, markersize=8, label='Efectividad de Tiro (FG%)')
    ax2.set_ylabel('Efectividad Ofensiva (FG%)', color='#0044cc', fontweight='bold', fontsize=11)
    ax2.set_ylim(0, max(efectividad_fg) + 15 if max(efectividad_fg) else 100)
    
    for i, txt in enumerate(efectividad_fg):
        ax2.annotate(f"{round(txt, 1)}%", (cuartos[i], efectividad_fg[i] + 1.5), color='#0044cc', fontweight='bold', ha='center')

    plt.title(f"{titulo}\n(Muestra: {total_pj} partidos procesados)", fontsize=14, fontweight='bold', pad=15)
    
    ruta_salida = f"./Mapas_Tiro/{nombre_archivo}.png"
    plt.savefig(ruta_salida, dpi=300, bbox_inches='tight')
    plt.close()

# ==========================================
# 4. EXPORTACIÓN DE RESULTADOS
# ==========================================
if not os.path.exists('./Mapas_Tiro'):
    os.makedirs('./Mapas_Tiro')

def generar_mapa_general(df_datos, titulo, nombre_archivo):
    fig, ax = dibujar_media_cancha()
    anotados = df_datos[df_datos['RESULTADO'] == 'Anotado']
    fallados = df_datos[df_datos['RESULTADO'] == 'Fallado']
    t_intentos = len(df_datos)
    t_anotados = len(anotados)
    efectividad = round((t_anotados / t_intentos) * 100, 1) if t_intentos > 0 else 0
    
    ax.scatter(anotados['X'], anotados['Y'], color='#00ff00', marker='o', s=90, edgecolors='black', label='Anotado', zorder=5)
    ax.scatter(fallados['X'], fallados['Y'], color='#ff0000', marker='X', s=90, label='Fallado', zorder=5)
    
    plt.title(f"{titulo}\nVolumen: {t_intentos} Tiros | Efectividad: {efectividad}%", fontsize=14, fontweight='bold', pad=15)
    plt.legend(loc='upper right', facecolor='white', framealpha=1)
    ruta_salida = f"./Mapas_Tiro/{nombre_archivo}.png"
    plt.savefig(ruta_salida, dpi=300, bbox_inches='tight')
    plt.close()

def generar_mapa_volumen(df_datos, titulo, nombre_archivo):
    fig, ax = dibujar_media_cancha()
    anotados = df_datos[df_datos['RESULTADO'] == 'Anotado']
    t_intentos = len(df_datos)
    t_anotados = len(anotados)
    efectividad = round((t_anotados / t_intentos) * 100, 1) if t_intentos > 0 else 0
    
    if len(anotados) > 2:
        sns.kdeplot(x=anotados['X'], y=anotados['Y'], fill=True, cmap="inferno", alpha=0.85, ax=ax, thresh=0.05, levels=15, zorder=2)
    
    plt.title(f"{titulo}\nAciertos: {t_anotados} (sobre {t_intentos} intentos | {efectividad}%)", fontsize=14, fontweight='bold', pad=15)
    ruta_salida = f"./Mapas_Tiro/{nombre_archivo}.png"
    plt.savefig(ruta_salida, dpi=300, bbox_inches='tight')
    plt.close()

print("\nGenerando Batería de Mapas Visuales y Tendencias...")

generar_grafico_momentum(datos_momentum, total_partidos, f"MATCH MOMENTUM (NET RATING): {nombre_objetivo}", f"0_{nombre_archivo_limpio}_Momentum")

generar_mapa_general(df_tiros, f"MAPA DE TIROS GENERAL: {nombre_objetivo}", f"1_{nombre_archivo_limpio}_General_Scatter")
generar_mapa_volumen(df_tiros, f"ZONAS DE ANOTACIÓN (GRADIENTE): {nombre_objetivo}", f"1_{nombre_archivo_limpio}_Volumen_Termico")

for jugador in jugadores_elite:
    tiros_jugador = df_tiros[df_tiros['JUGADOR'] == jugador]
    if len(tiros_jugador) > 0:
        nombre_limpio_jugador = jugador.replace(',', '').replace(' ', '_')
        generar_mapa_general(tiros_jugador, f"MAPA DE TIROS: {jugador}", f"2_{nombre_archivo_limpio}_Scatter_{nombre_limpio_jugador}")
        generar_mapa_volumen(tiros_jugador, f"ZONAS DE ANOTACIÓN: {jugador}", f"2_{nombre_archivo_limpio}_Termico_{nombre_limpio_jugador}")

print("\nÉXITO. Tu sistema de Scouting Operativo está completo.")