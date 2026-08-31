import os
import json
import pandas as pd
import numpy as np

# ==========================================
# CONFIGURACIÓN INICIAL Y AUTODETECCIÓN FILTRADA (WHITELIST)
# ==========================================
carpeta_datos = './datos_crudos'

print("Iniciando Sistema Maestro de Scouting y Datos...\n")

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
    print("[!] No se encontraron equipos de tu lista de interés en los archivos.")
    exit()

print("RADARES ACTIVOS (Solo rivales directos):")
lista_equipos = list(equipos_detectados.items())
for i, (eq_id, eq_nom) in enumerate(lista_equipos):
    print(f" [{i+1}] {eq_nom}")

try:
    seleccion = int(input("\nIngresa el NÚMERO del equipo a escanear: ")) - 1
    id_objetivo = lista_equipos[seleccion][0]
    nombre_objetivo = lista_equipos[seleccion][1]
except:
    print("[!] Selección inválida. Saliendo.")
    exit()

nombre_archivo_limpio = "".join(x for x in nombre_objetivo if x.isalnum() or x in " _-")
nombre_salida = f'{nombre_archivo_limpio}_Scouting_Total.xlsx'

print(f"\n=> Iniciando extracción táctica y cálculo de Ratings de: {nombre_objetivo}...\n")

datos_jugadores = []
datos_equipo = []

# ==========================================
# 1. EXTRACCIÓN GLOBAL, CONTEXTO Y RATINGS
# ==========================================
contador_jornada = 1
for nombre_archivo in os.listdir(carpeta_datos):
    if nombre_archivo.endswith('.json') or nombre_archivo.endswith('.txt'):
        ruta_completa = os.path.join(carpeta_datos, nombre_archivo)
        
        with open(ruta_completa, 'r', encoding='utf-8') as archivo:
            try: datos_partido = json.load(archivo)
            except: continue
            
            partido = datos_partido.get("partido", {})
            local_id = partido.get("idlocal")
            visitante_id = partido.get("idvisitante")
            
            if local_id != id_objetivo and visitante_id != id_objetivo:
                continue
            
            if local_id == id_objetivo:
                equipo_rival_nombre = partido.get("visitante", "Desconocido")
                resultado = f"{partido.get('tanteo_local', 0)} - {partido.get('tanteo_visitante', 0)}"
            else:
                equipo_rival_nombre = partido.get("local", "Desconocido")
                resultado = f"{partido.get('tanteo_visitante', 0)} - {partido.get('tanteo_local', 0)}"
            
            estadisticas = datos_partido.get("estadisticas", {})
            lista_local = estadisticas.get("estadisticasequipolocal", [])
            lista_visitante = estadisticas.get("estadisticasequipovisitante", [])
            
            if len(lista_local) > 0 and lista_local[0].get("idequipo") == id_objetivo:
                equipo_objetivo, equipo_rival = lista_local, lista_visitante
            else:
                equipo_objetivo, equipo_rival = lista_visitante, lista_local

            totales_objetivo = next((p for p in equipo_objetivo if p.get("nombre") == "TOTALES"), {})
            totales_rival = next((p for p in equipo_rival if p.get("nombre") == "TOTALES"), {})

            if not totales_objetivo or not totales_rival: continue

            tm_fga = totales_objetivo.get("tiro2p", 0) + totales_objetivo.get("tiro3p", 0)
            tm_fta = totales_objetivo.get("tiro1p", 0)
            tm_tov = totales_objetivo.get("perdidas", 0)
            tm_orb = totales_objetivo.get("reboteofensivo", 0)
            tm_pts = totales_objetivo.get("puntos", 0)

            opp_fga = totales_rival.get("tiro2p", 0) + totales_rival.get("tiro3p", 0)
            opp_fta = totales_rival.get("tiro1p", 0)
            opp_tov = totales_rival.get("perdidas", 0)
            opp_orb = totales_rival.get("reboteofensivo", 0)
            opp_pts = totales_rival.get("puntos", 0)

            tm_poss = tm_fga - tm_orb + tm_tov + (0.44 * tm_fta)
            opp_poss = opp_fga - opp_orb + opp_tov + (0.44 * opp_fta)
            
            pace = (tm_poss + opp_poss) / 2
            ortg = (tm_pts / tm_poss) * 100 if tm_poss > 0 else 0
            drtg = (opp_pts / opp_poss) * 100 if opp_poss > 0 else 0
            net_rtg = ortg - drtg

            tm_min_ms = totales_objetivo.get("milisegundos_jugados", 0)
            opp_drb = totales_rival.get("rebotedefensivo", 0)

            for jugador in equipo_objetivo:
                if jugador.get("nombre") == "TOTALES":
                    datos_equipo.append({
                        "JORNADA": f"Partido {contador_jornada}", "RESULTADO": resultado, "EQUIPO RIVAL": equipo_rival_nombre,
                        "PUNTOS": tm_pts, 
                        "PACE": round(pace, 1), "ORtg": round(ortg, 1), "DRtg": round(drtg, 1), "NET_RTG": round(net_rtg, 1),
                        "2P_ENCESTES": jugador.get("canasta2p", 0), "2P_INTENTOS": jugador.get("tiro2p", 0),
                        "3P_ENCESTES": jugador.get("canasta3p", 0), "3P_INTENTOS": jugador.get("tiro3p", 0),
                        "TL_ENCESTES": jugador.get("canasta1p", 0), "TL_INTENTOS": jugador.get("tiro1p", 0),
                        "REB_DEF": jugador.get("rebotedefensivo", 0), "REB_OFE": tm_orb, "REB_TOT": jugador.get("rebotes", 0),
                        "ASISTENCIAS": jugador.get("asistencias", 0), "RECUPEROS": jugador.get("recuperaciones", 0), "PERDIDAS": tm_tov,
                        "FAL_COMETIDAS": jugador.get("faltascometidas", 0), "FAL_RECIBIDAS": jugador.get("faltasrecibidas", 0), "VALORACION": jugador.get("valoracion", 0)
                    })
                    contador_jornada += 1
                else:
                    jug_ext = jugador.copy()
                    jug_ext['Tm_MIN_MS'] = tm_min_ms
                    jug_ext['Tm_FGA'] = tm_fga
                    jug_ext['Tm_FTA'] = tm_fta
                    jug_ext['Tm_TOV'] = tm_tov
                    jug_ext['Tm_ORB'] = tm_orb
                    jug_ext['Opp_DRB'] = opp_drb
                    jug_ext['Opp_Poss'] = opp_poss
                    datos_jugadores.append(jug_ext)

if not datos_jugadores:
    print(f"[!] Error crítico: No se extrajeron datos para {nombre_objetivo}.")
    exit()

# ==========================================
# 2. PROCESAMIENTO DEL EQUIPO (PROMEDIOS Y TIERS)
# ==========================================
df_equipo = pd.DataFrame(datos_equipo)
df_equipo["2P_PORCENTAJE"] = (df_equipo["2P_ENCESTES"] / df_equipo["2P_INTENTOS"]).fillna(0).round(3)
df_equipo["3P_PORCENTAJE"] = (df_equipo["3P_ENCESTES"] / df_equipo["3P_INTENTOS"]).fillna(0).round(3)
df_equipo["TL_PORCENTAJE"] = (df_equipo["TL_ENCESTES"] / df_equipo["TL_INTENTOS"]).fillna(0).round(3)

cols_eq = [
    "JORNADA", "RESULTADO", "EQUIPO RIVAL", "PUNTOS", 
    "PACE", "ORtg", "DRtg", "NET_RTG",
    "2P_ENCESTES", "2P_INTENTOS", "2P_PORCENTAJE",
    "3P_ENCESTES", "3P_INTENTOS", "3P_PORCENTAJE", "TL_ENCESTES", "TL_INTENTOS", "TL_PORCENTAJE",
    "REB_DEF", "REB_OFE", "REB_TOT", "ASISTENCIAS", "RECUPEROS", "PERDIDAS", "FAL_COMETIDAS", "FAL_RECIBIDAS", "VALORACION"
]
df_equipo = df_equipo[cols_eq]

# Inyección matemática de la fila de Promedio de Equipo
cols_numeric_eq = [c for c in cols_eq if c not in ["JORNADA", "RESULTADO", "EQUIPO RIVAL", "2P_PORCENTAJE", "3P_PORCENTAJE", "TL_PORCENTAJE"]]
promedios_eq = df_equipo[cols_numeric_eq].mean().round(1).to_dict()
promedios_eq["JORNADA"] = "PROMEDIO GLOBAL"
promedios_eq["RESULTADO"] = "-"
promedios_eq["EQUIPO RIVAL"] = "-"

# Recálculo seguro de porcentajes para no promediar promedios
promedios_eq["2P_PORCENTAJE"] = round(promedios_eq["2P_ENCESTES"] / promedios_eq["2P_INTENTOS"], 3) if promedios_eq["2P_INTENTOS"] > 0 else 0
promedios_eq["3P_PORCENTAJE"] = round(promedios_eq["3P_ENCESTES"] / promedios_eq["3P_INTENTOS"], 3) if promedios_eq["3P_INTENTOS"] > 0 else 0
promedios_eq["TL_PORCENTAJE"] = round(promedios_eq["TL_ENCESTES"] / promedios_eq["TL_INTENTOS"], 3) if promedios_eq["TL_INTENTOS"] > 0 else 0

df_promedio = pd.DataFrame([promedios_eq])
df_equipo = pd.concat([df_equipo, df_promedio], ignore_index=True)

# Evaluación Táctica del Equipo
def tier_pace(v): return "Alto" if v >= 76 else "Medio" if v >= 68 else "Bajo"
def tier_ortg(v): return "Excelente" if v >= 100 else "Promedio" if v >= 90 else "Pobre"
def tier_drtg(v): return "Excelente" if v <= 90 else "Promedio" if v <= 100 else "Pobre" 

df_equipo.insert(5, 'RITMO', df_equipo['PACE'].apply(tier_pace))
df_equipo.insert(7, 'NIVEL_OFE', df_equipo['ORtg'].apply(tier_ortg))
df_equipo.insert(9, 'NIVEL_DEF', df_equipo['DRtg'].apply(tier_drtg))

def pintar_equipo(v):
    colores = {
        "Alto": "#ff9933", "Medio": "#ffcc00", "Bajo": "#99ccff",
        "Excelente": "#33cc33", "Promedio": "#ffcc00", "Pobre": "#ff4d4d"
    }
    bg = colores.get(v, "")
    if bg: return f"background-color: {bg}; color: {'white' if bg in ['#33cc33', '#ff4d4d'] else 'black'}; font-weight: bold;"
    return ""

styled_equipo = df_equipo.style.apply(lambda col: [pintar_equipo(v) for v in col], subset=['RITMO', 'NIVEL_OFE', 'NIVEL_DEF'])

# ==========================================
# 3. PROCESAMIENTO DE JUGADORES
# ==========================================
df_jug = pd.DataFrame(datos_jugadores)
cols_num = ['puntos', 'canasta2p', 'tiro2p', 'canasta3p', 'tiro3p', 'canasta1p', 'tiro1p', 'rebotedefensivo', 'reboteofensivo', 'rebotes', 'asistencias', 'recuperaciones', 'perdidas', 'faltascometidas', 'faltasrecibidas', 'taponescometidos', 'milisegundos_jugados', 'valoracion']
for col in cols_num: df_jug[col] = pd.to_numeric(df_jug[col], errors='coerce').fillna(0)

df_dorsales = df_jug.groupby('nombre')['dorsal'].apply(lambda x: ', '.join(sorted(set([str(d).strip() for d in x if str(d).strip() != ''])))).reset_index(name='DORSAL')
df_pj = df_jug.groupby('nombre').size().reset_index(name='PJ')
df_totales = df_jug.groupby('nombre')[cols_num].sum().reset_index()

df_master = pd.merge(df_pj, df_totales, on='nombre')
df_master = pd.merge(df_dorsales, df_master, on='nombre')

df_master.rename(columns={
    'nombre': 'JUGADOR', 'puntos': 'PUNTOS', 
    'canasta2p': '2P_ENCESTES', 'tiro2p': '2P_INTENTOS',
    'canasta3p': '3P_ENCESTES', 'tiro3p': '3P_INTENTOS',
    'canasta1p': 'TL_ENCESTES', 'tiro1p': 'TL_INTENTOS',
    'rebotedefensivo': 'REB_DEF', 'reboteofensivo': 'REB_OFE', 'rebotes': 'REB_TOT', 
    'asistencias': 'ASISTENCIAS', 'recuperaciones': 'RECUPEROS', 'perdidas': 'PERDIDAS', 
    'faltascometidas': 'FAL_COMETIDAS', 'faltasrecibidas': 'FAL_RECIBIDAS', 'valoracion': 'VALORACION'
}, inplace=True)

df_master["2P_PORCENTAJE"] = (df_master["2P_ENCESTES"] / df_master["2P_INTENTOS"]).fillna(0).round(3)
df_master["3P_PORCENTAJE"] = (df_master["3P_ENCESTES"] / df_master["3P_INTENTOS"]).fillna(0).round(3)
df_master["TL_PORCENTAJE"] = (df_master["TL_ENCESTES"] / df_master["TL_INTENTOS"]).fillna(0).round(3)

df_master['FGA'] = df_master['2P_INTENTOS'] + df_master['3P_INTENTOS']
df_master['FGM'] = df_master['2P_ENCESTES'] + df_master['3P_ENCESTES']

df_adv_tot = df_jug.groupby('nombre')[['Tm_MIN_MS', 'Tm_FGA', 'Tm_FTA', 'Tm_TOV', 'Tm_ORB', 'Opp_DRB', 'Opp_Poss']].sum().reset_index()
df_adv_tot.rename(columns={'nombre': 'JUGADOR'}, inplace=True)
df_master = pd.merge(df_master, df_adv_tot, on='JUGADOR')

df_master['EFF'] = (df_master['PUNTOS'] + df_master['REB_TOT'] + df_master['ASISTENCIAS'] + df_master['RECUPEROS'] + df_master['taponescometidos']) - ((df_master['FGA'] - df_master['FGM']) + (df_master['TL_INTENTOS'] - df_master['TL_ENCESTES']) + df_master['PERDIDAS'])
df_master['AST/TOV'] = np.where(df_master['PERDIDAS'] == 0, df_master['ASISTENCIAS'], df_master['ASISTENCIAS'] / df_master['PERDIDAS'])

df_master['Tm_MIN_Eq'] = df_master['Tm_MIN_MS'] / 5
num_usg = (df_master['FGA'] + 0.44 * df_master['TL_INTENTOS'] + df_master['PERDIDAS']) * df_master['Tm_MIN_Eq']
den_usg = df_master['milisegundos_jugados'] * (df_master['Tm_FGA'] + 0.44 * df_master['Tm_FTA'] + df_master['Tm_TOV'])
df_master['USG%'] = np.where(den_usg == 0, 0, 100 * (num_usg / den_usg))

num_orb = df_master['REB_OFE'] * df_master['Tm_MIN_Eq']
den_orb = df_master['milisegundos_jugados'] * (df_master['Tm_ORB'] + df_master['Opp_DRB'])
df_master['ORB%'] = np.where(den_orb == 0, 0, 100 * (num_orb / den_orb))

num_stl = df_master['RECUPEROS'] * df_master['Tm_MIN_Eq']
den_stl = df_master['milisegundos_jugados'] * df_master['Opp_Poss']
df_master['STL%'] = np.where(den_stl == 0, 0, 100 * (num_stl / den_stl))

def ms_a_minutos(ms): return f"{int(ms / 1000) // 60:02d}:{int(ms / 1000) % 60:02d}"
df_master['MINUTOS_TOTALES'] = df_master['milisegundos_jugados'].apply(ms_a_minutos)
df_master['MINUTOS_PROMEDIO'] = (df_master['milisegundos_jugados'] / df_master['PJ']).apply(ms_a_minutos)

# ==========================================
# 4. PREPARACIÓN DE PESTAÑAS (DATA FRAMES)
# ==========================================
cols_comunes = ['JUGADOR', 'DORSAL', 'PJ']
cols_stats = [
    'PUNTOS', '2P_ENCESTES', '2P_INTENTOS', '2P_PORCENTAJE', 
    '3P_ENCESTES', '3P_INTENTOS', '3P_PORCENTAJE', 
    'TL_ENCESTES', 'TL_INTENTOS', 'TL_PORCENTAJE', 
    'REB_DEF', 'REB_OFE', 'REB_TOT', 
    'ASISTENCIAS', 'RECUPEROS', 'PERDIDAS', 'FAL_COMETIDAS', 'FAL_RECIBIDAS', 'VALORACION'
]

df_vista_totales = df_master[cols_comunes + ['MINUTOS_TOTALES'] + cols_stats].copy()
df_vista_promedios = df_master[cols_comunes + ['MINUTOS_PROMEDIO'] + cols_stats].copy()

cols_a_promediar = [c for c in cols_stats if 'PORCENTAJE' not in c]
for col in cols_a_promediar: 
    df_vista_promedios[col] = (df_vista_promedios[col] / df_vista_promedios['PJ']).round(1)

cols_adv_base = ['JUGADOR', 'DORSAL', 'PJ', 'MINUTOS_PROMEDIO', 'PUNTOS', '2P_PORCENTAJE', '3P_PORCENTAJE', 'TL_PORCENTAJE', 'REB_DEF', 'REB_OFE', 'REB_TOT', 'ASISTENCIAS', 'RECUPEROS', 'PERDIDAS', 'EFF', 'USG%', 'ORB%', 'STL%', 'AST/TOV']
df_adv = df_master[cols_adv_base].copy()

for col in ['PUNTOS', 'REB_DEF', 'REB_OFE', 'REB_TOT', 'ASISTENCIAS', 'RECUPEROS', 'PERDIDAS', 'EFF']: 
    df_adv[col] = (df_adv[col] / df_adv['PJ']).round(1)
    
for col in ['USG%', 'ORB%', 'STL%']: df_adv[col] = df_adv[col].round(1)
df_adv['AST/TOV'] = df_adv['AST/TOV'].round(2)

def tier_ast_tov(v): return "Elite" if v>=3.5 else "Excellent" if v>=2.75 else "Good" if v>=2.0 else "Average" if v>=1.5 else "Below Avg" if v>=1.0 else "Poor"
def tier_orb(v): return "Elite" if v>=13.0 else "Excellent" if v>=10.0 else "Above Avg" if v>=7.0 else "Average" if v>=4.0 else "Below Avg" if v>=2.0 else "Low"
def tier_eff(v): return "Elite" if v>=30.0 else "All-Star" if v>=25.0 else "Starter" if v>=20.0 else "Above Avg" if v>=15.0 else "Average" if v>=10.0 else "Below Avg" if v>=5.0 else "Poor"
def tier_usg(v): return "Elite" if v>=30.0 else "High" if v>=25.0 else "Above Avg" if v>=20.0 else "Average" if v>=15.0 else "Below Avg" if v>=10.0 else "Low"
def tier_stl(v): return "Elite" if v>=3.0 else "Excellent" if v>=2.5 else "Above Avg" if v>=2.0 else "Average" if v>=1.5 else "Below Avg" if v>=1.0 else "Poor"

df_adv['T_EFF'] = df_adv['EFF'].apply(tier_eff)
df_adv['T_USG%'] = df_adv['USG%'].apply(tier_usg)
df_adv['T_ORB%'] = df_adv['ORB%'].apply(tier_orb)
df_adv['T_STL%'] = df_adv['STL%'].apply(tier_stl)
df_adv['T_AST/TOV'] = df_adv['AST/TOV'].apply(tier_ast_tov)

df_adv.rename(columns={'PUNTOS': 'PTS_PROMEDIO'}, inplace=True)
cols_ordenadas = ['JUGADOR', 'DORSAL', 'PJ', 'MINUTOS_PROMEDIO', 'PTS_PROMEDIO'] + [c for c in df_adv.columns if c not in ['JUGADOR', 'DORSAL', 'PJ', 'MINUTOS_PROMEDIO', 'PTS_PROMEDIO']]
df_adv = df_adv[cols_ordenadas]

def pintar_celda(v):
    colores = {"Elite": "#9933ff", "Excellent": "#33cc33", "All-Star": "#33cc33", "Starter": "#99ff99", "High": "#33cc33", "Above Avg": "#99ff99", "Good": "#99ff99", "Average": "#ffcc00", "Below Avg": "#ff9933", "Poor": "#ff4d4d", "Low": "#ff4d4d"}
    color_fondo = colores.get(v, "")
    if color_fondo: return f"background-color: {color_fondo}; color: {'white' if color_fondo in ['#9933ff', '#33cc33', '#ff4d4d'] else 'black'};"
    return ""

styled_adv = df_adv.style.apply(lambda col: [pintar_celda(v) for v in col], subset=['T_EFF', 'T_USG%', 'T_ORB%', 'T_AST/TOV', 'T_STL%'])

# ==========================================
# 5. EXPORTACIÓN A EXCEL 
# ==========================================
with pd.ExcelWriter(nombre_salida, engine='openpyxl') as writer:
    styled_equipo.to_excel(writer, sheet_name="Rendimiento Equipo", index=False)
    df_vista_totales.to_excel(writer, sheet_name="Totales Jugadores", index=False)
    df_vista_promedios.to_excel(writer, sheet_name="Promedios Jugadores", index=False)
    styled_adv.to_excel(writer, sheet_name="Métricas Avanzadas", index=False)

print(f"ÉXITO. El sistema ha generado '{nombre_salida}'.")