import pandas as pd
import numpy as np
import os
import random
import re
from catboost import CatBoostClassifier

nombre_modelo = 'modelo_final.cbm'
if not os.path.exists(nombre_modelo): raise FileNotFoundError(f"ERROR: Falta '{nombre_modelo}'.")

modelo_final = CatBoostClassifier()
modelo_final.load_model(nombre_modelo)
features_esperadas = modelo_final.feature_names_
indices_cat = modelo_final.get_cat_feature_indices()
columnas_categoricas = [features_esperadas[i] for i in indices_cat]
columnas_numericas = [c for c in features_esperadas if c not in columnas_categoricas]

df_predecir = pd.read_csv('dataset_predecir.csv', sep=';', encoding='utf-8-sig', low_memory=False)
col_orden = next((c for c in df_predecir.columns if 'orden' in c.lower()), 'orden_ejercicio')
col_counter = next((c for c in df_predecir.columns if 'counter' in c.lower()), 'counter')

for col in ['cantidad_otra_unidad', 'tipo_otra_unidad', 'kmh_s1', 'series_circuito', 'formato_circuito', 'minutos_circuito', 'hour_date', 'por_lado', 'color_goma', 'Confianza_IA', 'Alerta_Monitor']:
    if col not in df_predecir.columns: df_predecir[col] = ''

df_predecir['hour_date'] = df_predecir['hour_date'].astype(str).replace(['', 'nan', 'None'], 'Completado (Histórico)')

def purgar_tipos_circuito(row):
    tipo, circ = str(row.get('tipo_circuito', '')).strip(), str(row.get('circuito', '')).lower()
    if tipo in ['nan', 'None', '', 'Desconocido', 'Complementario', 'Sin circuito']:
        if any(pal in circ for pal in ['activ', 'calent', 'movil']): return 'Activación'
        if any(pal in circ for pal in ['metab', 'aer', 'cardio', 'emom', 'amrap']): return 'Metabólico'
        return 'Fuerza'
    return tipo

df_predecir['tipo_circuito'] = df_predecir.apply(purgar_tipos_circuito, axis=1)

sesiones_futuras = []

for cliente_id, df_cliente in df_predecir.groupby('customer_id'):
    max_cnt = pd.to_numeric(df_cliente[col_counter], errors='coerce').max()
    df_u = df_cliente[pd.to_numeric(df_cliente[col_counter], errors='coerce') == max_cnt].copy()

    nuevo_cnt = int(max_cnt + 1)
    df_u[col_counter], df_u['hour_date'] = nuevo_cnt, 'Por programar (IA)'
    if 'id' in df_u.columns: df_u['id'] = 'Por generar'

    patron_metabolico = r'(?i)(?:metab|aer[oó]bico|cardio|metcon|emom|amrap|full\s*body|finisher)'
    tiene_cardio = df_u.get('tipo_circuito', pd.Series(dtype=str)).astype(str).str.contains(patron_metabolico, regex=True).any() or \
                   df_u.get('formato_circuito', pd.Series(dtype=str)).astype(str).str.contains(patron_metabolico, regex=True).any() or \
                   df_u.get('circuito', pd.Series(dtype=str)).astype(str).str.contains(patron_metabolico, regex=True).any()

    if not tiene_cardio:
        X_temp = df_u.copy()
        for col in features_esperadas:
            if col not in X_temp.columns: X_temp[col] = 'Desconocido' if col in columnas_categoricas else 0.0
        for col in columnas_categoricas: X_temp[col] = X_temp[col].fillna('Desconocido').astype(str).str.replace(r'\.0$', '', regex=True)
        for col in columnas_numericas: X_temp[col] = pd.to_numeric(X_temp[col], errors='coerce').fillna(0.0)

        preds_snc = np.argmax(modelo_final.predict_proba(X_temp[features_esperadas]), axis=1)
        score_snc = np.mean(preds_snc)

        ia_recomienda_cardio = score_snc >= 0.5

        if ia_recomienda_cardio:
            nums = df_u['circuito'].astype(str).str.extract(r'(?i)circuito\s*(\d+)')[0].dropna().astype(int)
            next_circ = int(nums.max() + 1) if not nums.empty else 3
            nombre_dinamico = f"Circuito {next_circ}: Metabólico"

            ejercicios_generados = []

        if score_snc < 0.7:
            maq_opts = [
                {'ej': 'Cinta', 'ou': f'[{random.choice([20, 25, 30, 40])}]', 'tou': 'min', 'vel': str(random.choice([9.0, 10.0, 11.0]))},
                {'ej': 'Bici Estática', 'ou': f'[{random.choice([20, 25, 30, 40])}]', 'tou': 'min', 'vel': str(random.choice([20.0, 22.0, 25.0]))},
                {'ej': 'Elíptica', 'ou': f'[{random.choice([15, 20, 25])}]', 'tou': 'min', 'vel': str(random.choice([10.0, 12.0, 14.0]))},
                {'ej': 'Remo Ergómetro', 'ou': f'[{random.choice([10, 12, 15])}]', 'tou': 'min', 'vel': ''}
            ]
            eleccion = random.choice(maq_opts)
            mins = eleccion['ou'].strip('[]')
            ejercicios_generados.append(eleccion)
            msg_ia, formato, series = "PREDICCIÓN FATIGA (LISS)", 'LISS', '1'

        elif score_snc < 1.4:
            msg_ia = "Predicción Estable"
            if random.random() < 0.5:
                mins = str(random.choice([8, 10, 12, 14, 15, 16, 20]))
                formato, series = 'AMRAP', '1'
                num_ej = random.choice([3, 4, 5])

                pool = [
                    {'ej': random.choice(['Airbike', 'Remo Ergómetro', 'SkiErg']), 'ou': f'[{random.choice([10, 12, 15])}]', 'tou': 'kcal'},
                    {'ej': random.choice(['Burpees', 'Mountain Climbers']), 'reps': f'[{random.choice([10, 15, 20])}]'},
                    {'ej': random.choice(['Kettlebell Swings', 'Box Jumps']), 'reps': f'[{random.choice([12, 15])}]', 'peso': '[16]'},
                    {'ej': random.choice(['Sit Ups', 'Russian Twist']), 'reps': f'[{random.choice([15, 20])}]'},
                    {'ej': random.choice(['Zancadas Alternas', 'Sentadilla al aire']), 'reps': f'[{random.choice([16, 20])}]'},
                    {'ej': 'Cinta', 'ou': '[200]', 'tou': 'metros', 'vel': str(random.choice([12.0, 13.0, 14.0]))}
                ]
                random.shuffle(pool)
                for i in range(num_ej): ejercicios_generados.append(pool[i])
            else:
                mins = ''
                formato, series = 'Esquema Descendente', '1'
                esquema = random.choice(['21-15-9', '15-12-9', '30-20-10'])
                nombre_dinamico = f"Circuito {next_circ}: Esquema {esquema}"

                ejercicios_generados.append({'ej': random.choice(['Remo Ergómetro', 'SkiErg', 'Airbike']), 'ou': f'[{esquema}]', 'tou': 'kcal'})
                ejercicios_generados.append({'ej': random.choice(['Burpees', 'Kettlebell Swings', 'Thrusters mancuerna']), 'reps': f'[{esquema}]', 'peso': '[16]'})

        else:
            if random.random() < 0.6:
                num_ej = random.choice([3, 4, 5])
                rondas = random.choice([3, 4, 5])
                mins = str(num_ej * rondas)
                series = str(rondas)
                msg_ia, formato = "Predicción Potencia (EMOM)", 'EMOM'

                pool = [
                    {'ej': random.choice(['SkiErg', 'Airbike', 'Remo Ergómetro']), 'ou': f'[{random.choice([10, 12, 15])}]', 'tou': 'kcal'},
                    {'ej': random.choice(['Burpees', 'Thrusters mancuerna']), 'reps': f'[{random.choice([8, 10, 12])}]', 'peso': '[10]'},
                    {'ej': random.choice(['Box Jumps', 'Kettlebell Swings']), 'reps': f'[{random.choice([10, 15])}]', 'peso': '[20]'},
                    {'ej': random.choice(['Flexiones', 'Dominadas']), 'reps': f'[{random.choice([8, 12])}]'},
                    {'ej': 'Cinta', 'ou': '[200]', 'tou': 'metros', 'vel': str(random.choice([14.0, 15.0, 16.0]))}
                ]
                random.shuffle(pool)
                for i in range(num_ej): ejercicios_generados.append(pool[i])
            else:
                series = str(random.choice([4, 5, 6, 8]))
                mins = str(random.choice([10, 12, 15]))
                msg_ia, formato = "Predicción Potencia (Sprint)", 'Sprint'

                maq = random.choice(['SkiErg', 'Remo Ergómetro', 'Cinta', 'Airbike'])
                if maq == 'Cinta':
                    vel = str(random.choice([14.0, 15.0, 16.0]))
                    ejercicios_generados.append({'ej': 'Cinta', 'ou': '< 30', 'tou': 'seg', 'vel': vel})
                else:
                    dist_tou = 'metros' if maq in ['SkiErg', 'Remo Ergómetro'] else 'kcal'
                    dist_val = random.choice([200, 250, 300]) if dist_tou == 'metros' else random.choice([15, 20])
                    ejercicios_generados.append({'ej': maq, 'ou': f'[{dist_val}]', 'tou': dist_tou})

        filas_meta = []
        for idx, ej in enumerate(ejercicios_generados):
            f = pd.DataFrame(columns=df_u.columns, index=[0])
            f['customer_id'], f[col_counter], f['id'], f['hour_date'] = cliente_id, nuevo_cnt, 'Por generar', 'Por programar (IA)'
            f['circuito'], f['tipo_circuito'], f['formato_circuito'] = nombre_dinamico, 'Metabólico', formato
            f['series_circuito'], f['minutos_circuito'] = series, mins
            f['ejercicio_limpio'], f['cantidad_otra_unidad'], f['tipo_otra_unidad'] = ej.get('ej',''), ej.get('ou',''), ej.get('tou','')
            f['kmh_s1'], f['repeticiones'], f['peso_kg'] = ej.get('vel',''), ej.get('reps','[]'), ej.get('peso','[]')
            f['por_lado'], f['color_goma'], f['Confianza_IA'], f['Alerta_Monitor'] = '', '', '90.0%', msg_ia
            f[col_orden] = str(idx + 1)
            filas_meta.append(f)

        df_u = pd.concat([df_u] + filas_meta, ignore_index=True)

    sesiones_futuras.append(df_u)

df_futuro = pd.concat(sesiones_futuras, ignore_index=True)

for col in features_esperadas:
    if col not in df_futuro.columns: df_futuro[col] = 'Desconocido' if col in columnas_categoricas else 0.0
for col in columnas_categoricas: df_futuro[col] = df_futuro[col].fillna('Desconocido').astype(str).str.replace(r'\.0$', '', regex=True)
for col in columnas_numericas: df_futuro[col] = pd.to_numeric(df_futuro[col], errors='coerce').fillna(0.0)

X_predecir = df_futuro[features_esperadas].copy()
probabilidades = modelo_final.predict_proba(X_predecir)

df_futuro['prediccion_estado'] = np.argmax(probabilidades, axis=1)
df_futuro['Confianza_IA_Str'] = np.max(probabilidades, axis=1) * 100

diccionario_rotacion = {
    'Vertical Pull': ['Dominadas', 'Jalón supino en polea', 'Jalón al pecho con goma'],
    'Horizontal Pull': ['Remo en polea baja', 'Remo unilateral con mancuerna', 'Remo TRX'],
    'Vertical Push': ['Press militar mancuernas', 'Push press', 'Press Arnold'],
    'Horizontal Push': ['Press banca', 'Flexiones con goma', 'Flexiones pies en cajón'],
    'Squat / Knee Dominant': ['Sentadilla goblet', 'Prensa', 'Sentadilla búlgara'],
    'Hip / Glute Dominant': ['Peso muerto rumano', 'Hip thrust', 'Kettlebell swing'],
    'Lunge / Gait': ['Zancadas', 'Step ups en cajón', 'Zancada con goma'],
    'Mobility / Control': ['Bird dog', 'Dead bug', 'Movilidad torácica'],
    'Core': ['Rueda abdominal', 'Press Pallof con polea', 'Plancha abdominal'],
    'Calf / Foot Isolation': ['Elevación de talones', 'Sóleo sentado']
}

def modificar_array(val_str, accion, tipo='peso'):
    if pd.isna(val_str) or str(val_str).strip() in ['', '[]', '[-]', 'nan', 'None']:
        return '[12]' if accion == 'subir' and tipo == 'reps' else ('[8]' if accion == 'bajar' and tipo == 'reps' else '[]')
    nums = re.findall(r'\d+\.?\d*', str(val_str))
    if not nums: return val_str
    primer_num = float(nums[0])
    if tipo == 'peso':
        nuevo_num = round((primer_num * 1.05) / 2.5) * 2.5 if accion == 'subir' else (round((primer_num * 0.90) / 2.5) * 2.5 if accion == 'bajar' else primer_num)
        nuevo_num_str = str(int(nuevo_num)) if nuevo_num.is_integer() else str(nuevo_num)
    else:
        primer_num = int(primer_num)
        nuevo_num_str = str(primer_num + 2) if accion == 'subir' else (str(max(1, primer_num - 2)) if accion == 'bajar' else str(primer_num))
    return str(val_str).replace(nums[0], nuevo_num_str, 1)

def modificar_velocidad(vel_str, accion):
    if pd.isna(vel_str) or str(vel_str).strip() in ['', 'nan', 'None', '0', '0.0']:
        return '10.5' if accion == 'subir' else ('9.5' if accion == 'bajar' else '10.0')
    try:
        vel = float(vel_str)
        return str(min(22.0, round(vel + 0.5, 1))) if accion == 'subir' else (str(round(max(4.0, vel - 0.5), 1)) if accion == 'bajar' else str(min(22.0, vel)))
    except: return '10.0'

def es_maquina_cardio(nombre_ejercicio, material=''):
    ej = str(nombre_ejercicio).lower()
    mat = str(material).lower()
    if any(m in ej for m in ['cinta', 'airbike', 'skierg', 'bici', 'eliptica']): return True
    if 'remo' in ej:
        if any(x in ej for x in ['trx', 'mancuerna', 'barra', 'polea', 'punta', 'abierto']): return False
        if any(x in mat for x in ['trx', 'mancuerna', 'barra', 'polea', 'goma']): return False
        return True 
    return False

def aplicar_motor_ia(fila):
    estado, categoria, ejercicio_actual = fila['prediccion_estado'], str(fila.get('categoria_maestra_1', '')), str(fila.get('ejercicio_limpio', ''))
    peso_str, reps_str, vel_str = str(fila.get('peso_kg', '[]')), str(fila.get('repeticiones', '[]')), str(fila.get('kmh_s1', ''))
    ou_str, goma_str = str(fila.get('cantidad_otra_unidad', '')), str(fila.get('color_goma', ''))
    mat_str = str(fila.get('equipamiento', '')) 
    confianza = float(fila.get('Confianza_IA_Str', 100.0)) if isinstance(fila.get('Confianza_IA_Str'), (int, float, np.float64, np.float32)) else 100.0

    nums_peso = re.findall(r'\d+\.?\d*', peso_str)
    tiene_peso = len(nums_peso) > 0 and float(nums_peso[0]) > 0
    nuevo_peso, nuevas_reps, nueva_vel, nueva_ou, nuevo_ejercicio, motivo, alerta = peso_str, reps_str, vel_str, ou_str, ejercicio_actual, "", ""

    if 'Predicción' in str(fila.get('Alerta_Monitor', '')):
        return pd.Series([nuevo_ejercicio, peso_str, reps_str, nueva_vel, nueva_ou, goma_str, "PREDICCIÓN METABÓLICA", '90.0%', fila['Alerta_Monitor']])

    str_confianza = f"{confianza:.1f}%"
    alerta = "REVISAR (Duda)" if confianza < 60.0 else "OK"

    if es_maquina_cardio(ejercicio_actual, mat_str):
        nuevo_peso, nuevas_reps = '[]', '[]'
        if estado == 2:
            motivo = "PROGRESAR METABÓLICO"
            if 'cinta' in ejercicio_actual.lower(): nueva_vel = modificar_velocidad(vel_str, 'subir')
            else: nueva_ou = modificar_array(ou_str, 'subir', 'reps')
        elif estado == 0:
            motivo = "DESCARGA METABÓLICA"
            if 'cinta' in ejercicio_actual.lower(): nueva_vel = modificar_velocidad(vel_str, 'bajar')
            else: nueva_ou = modificar_array(ou_str, 'bajar', 'reps')
        else: motivo = "MANTENER RITMO"
        return pd.Series([nuevo_ejercicio, nuevo_peso, nuevas_reps, nueva_vel, nueva_ou, goma_str, motivo, str_confianza, alerta])

    if estado == 2:
        if tiene_peso: nuevo_peso, motivo = modificar_array(peso_str, 'subir', 'peso'), "SUBIR CARGA"
        else: nuevas_reps, motivo = modificar_array(reps_str, 'subir', 'reps'), "SUBIR REPETICIONES"
    elif estado == 0:
        if tiene_peso: nuevo_peso, motivo = modificar_array(peso_str, 'bajar', 'peso'), "DESCARGAR SNC"
        else: nuevas_reps, motivo = modificar_array(reps_str, 'bajar', 'reps'), "DESCARGA: -2 Reps"
    else:
        motivo, nuevo_peso, nuevas_reps = "MANTENER CARGA", modificar_array(peso_str, 'mantener', 'peso'), modificar_array(reps_str, 'mantener', 'reps')
        if categoria in diccionario_rotacion:
            opciones_validas = [e for e in diccionario_rotacion[categoria] if e.lower() not in ejercicio_actual.lower()]
            if opciones_validas:
                np.random.seed(int(fila.get('customer_id', 0)) + int(fila.get(col_orden, 0)) + int(fila.get(col_counter, 0)))
                nuevo_ejercicio, motivo, goma_str = np.random.choice(opciones_validas), "VARIANTE APLICADA", ''

    return pd.Series([nuevo_ejercicio, nuevo_peso, nuevas_reps, '', nueva_ou, goma_str, motivo, str_confianza, alerta])

df_futuro[['Ejercicio_Propuesto_IA', 'Nuevos_Kilos_IA', 'Nuevas_Reps_IA', 'Velocidad_kmh', 'Nuevas_OU_IA', 'Color_Goma_IA', 'Motivo_IA', 'Confianza_IA_Str', 'Alerta_Monitor']] = df_futuro.apply(aplicar_motor_ia, axis=1)
df_futuro['cantidad_otra_unidad'], df_futuro['color_goma'], df_futuro['Confianza_IA'] = df_futuro['Nuevas_OU_IA'], df_futuro['Color_Goma_IA'], df_futuro['Confianza_IA_Str']

df_predecir['Ejercicio_Propuesto_IA'], df_predecir['Nuevos_Kilos_IA'], df_predecir['Nuevas_Reps_IA'] = df_predecir['ejercicio_limpio'], df_predecir['peso_kg'], df_predecir['repeticiones']
df_predecir['Velocidad_kmh'], df_predecir['Motivo_IA'], df_predecir['Confianza_IA'], df_predecir['Alerta_Monitor'] = df_predecir.get('kmh_s1', ''), '--- HISTÓRICO ---', '-', '--- HISTÓRICO ---'

try:
    df_entrenar = pd.read_csv('dataset_entrenar.csv', sep=';', encoding='utf-8-sig', low_memory=False)
    df_entrenar['Ejercicio_Propuesto_IA'], df_entrenar['Nuevos_Kilos_IA'], df_entrenar['Nuevas_Reps_IA'] = df_entrenar['ejercicio_limpio'], df_entrenar['peso_kg'], df_entrenar['repeticiones']
    df_entrenar['Velocidad_kmh'], df_entrenar['Motivo_IA'], df_entrenar['Confianza_IA'], df_entrenar['Alerta_Monitor'] = df_entrenar.get('kmh_s1', ''), '--- HISTÓRICO ---', '-', '--- HISTÓRICO ---'

    df_combined = pd.concat([df_entrenar, df_predecir, df_futuro], ignore_index=True)
except FileNotFoundError:
    df_combined = pd.concat([df_predecir, df_futuro], ignore_index=True)

renombres = {'id': 'ID_Sesion', 'customer_id': 'ID_Cliente', 'tipo_circuito': 'Bloque_Principal', col_orden: 'Orden', 'Nuevos_Kilos_IA': 'KILOS_A_LEVANTAR_HOY', 'Nuevas_Reps_IA': 'Reps_Objetivo', 'equipamiento': 'Material_Necesario', 'Ejercicio_Propuesto_IA': 'ejercicio_1'}
if 'circuito' in df_combined.columns: renombres['circuito'] = 'Nombre_Circuito_Original'
df_exportar = df_combined.rename(columns=renombres).copy()

if 'Nombre_Circuito_Original' not in df_exportar.columns: df_exportar['Nombre_Circuito_Original'] = df_exportar['Bloque_Principal']
df_exportar['ID_Cliente_Num'] = pd.to_numeric(df_exportar['ID_Cliente'], errors='coerce').fillna(0)
df_exportar['Counter_Num'] = pd.to_numeric(df_exportar[col_counter], errors='coerce').fillna(0)

orden_bloque = {'Activación': 1, 'Fuerza': 2, 'Metabólico': 3, 'Aeróbico': 3}
df_exportar['rank_bloque'] = df_exportar['Bloque_Principal'].map(lambda x: orden_bloque.get(str(x).strip(), 99))

df_exportar['Orden_Num'] = pd.to_numeric(df_exportar['Orden'].astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(99)

df_exportar = df_exportar.sort_values(by=['ID_Cliente_Num', 'Counter_Num', 'rank_bloque', 'Nombre_Circuito_Original', 'Orden_Num', 'Orden'])

df_exportar = df_exportar.drop(columns=['Orden_Num'])

def rellenar_columnas_circuito_futuro(fila):
    circ, series, formato, minutos = str(fila.get('Nombre_Circuito_Original', '')), str(fila.get('series_circuito', '')), str(fila.get('formato_circuito', '')), str(fila.get('minutos_circuito', ''))
    if series in ['', 'nan', 'None']:
        match = re.search(r'x\s*(\d+)\s*series', circ, re.IGNORECASE)
        series = match.group(1) if match else '1'
    if formato in ['', 'nan', 'None']:
        cl = circ.lower()
        if 'emom' in cl: formato = 'EMOM'
        elif 'amrap' in cl: formato = 'AMRAP'
        elif 'metab' in cl or 'aer' in cl: formato = 'Metabólico'
        elif 'activ' in cl: formato = 'Calentamiento'
        elif 'fuerza' in cl: formato = 'Fuerza'
        else: formato = 'Circuito'
    if minutos in ['', 'nan', 'None', '0', '0.0']:
        match_min = re.search(r'(\d+)\s*(?:min|mins|\')', circ, re.IGNORECASE)
        minutos = match_min.group(1) if match_min else ''
    return pd.Series([series, formato, minutos])

df_exportar[['series_circuito', 'formato_circuito', 'minutos_circuito']] = df_exportar.apply(rellenar_columnas_circuito_futuro, axis=1)

def extraer_material_inteligente(fila):
    ej, mat = str(fila.get('ejercicio_1', '')).lower(), str(fila.get('Material_Necesario', ''))
    if mat in ['nan', 'None', 'Desconocido', '[]']: mat = ''
    mat = mat.replace('[', '').replace(']', '')
    if any(x in ej for x in ['goma', 'banda']) and 'goma' not in mat.lower(): mat += ', Goma'
    if any(x in ej for x in ['cajón', 'cajon', 'box', 'subida', 'step', 'cms']) and 'cajón' not in mat.lower(): mat += ', Cajón'
    if 'polea' in ej and 'polea' not in mat.lower(): mat += ', Polea'
    if 'trx' in ej and 'trx' not in mat.lower(): mat += ', TRX'
    return mat.strip(', ').strip()

df_exportar['Material_Necesario'] = df_exportar.apply(extraer_material_inteligente, axis=1)

def asegurar_unidades_cardio_futuro(fila):
    ou, tou, vel = str(fila.get('cantidad_otra_unidad', '')).strip(), str(fila.get('tipo_otra_unidad', '')).strip(), str(fila.get('Velocidad_kmh', '')).strip()
    if str(fila.get('Motivo_IA')) == '--- HISTÓRICO ---': return pd.Series([ou, tou, vel])

    ej = str(fila.get('ejercicio_1', '')).lower()
    mat = str(fila.get('Material_Necesario', '')).lower()

    if es_maquina_cardio(ej, mat):
        if 'cinta' in ej:
            if ou in ['', '[]', 'nan', 'None', '0', '0.0']: ou = '[15]'
            if tou in ['', 'nan', 'None']: tou = 'min'
            if vel in ['', 'nan', 'None', '0.0', '0']: vel = '10.0'
        else:
            if ou in ['', '[]', 'nan', 'None', '0', '0.0']: ou = '[20]'
            if tou in ['', 'nan', 'None']: tou = 'kcal'
    else: ou, tou, vel = '', '', ''
    return pd.Series([ou, tou, vel])

df_exportar[['cantidad_otra_unidad', 'tipo_otra_unidad', 'Velocidad_kmh']] = df_exportar.apply(asegurar_unidades_cardio_futuro, axis=1)

def limpiar_textos(texto):
    if pd.isna(texto): return ''
    texto = str(texto)
    texto = re.sub(r'\b(sin|con|a|de|en)\s*$', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\[\s*-\s*,?\s*', '[', texto)
    return re.sub(r'\s+', ' ', texto.replace('[,', '[').replace(', ]', ']')).strip() if texto != '[]' else ''

for col in ['ejercicio_1', 'modificador_espacial', 'modificador_mecanico']:
    if col in df_exportar.columns: df_exportar[col] = df_exportar[col].apply(limpiar_textos)

def arreglar_arrays_compuestos(val):
    val = str(val).strip()
    return f"[{val}]" if ',' in val and not val.startswith('[') and val not in ['', 'nan', 'None'] else val

if 'Material_Necesario' in df_exportar.columns: df_exportar['Material_Necesario'] = df_exportar['Material_Necesario'].apply(arreglar_arrays_compuestos)

for col in ['tiempo_iso_seg', 'Velocidad_kmh', 'minutos_circuito']:
    if col in df_exportar.columns: df_exportar[col] = df_exportar[col].astype(str).apply(lambda x: '' if str(x).strip() in ['0', '0.0', '0.00', 'nan', 'None', '[]'] else x)

def limpiar_modificador_iso(fila):
    mod, tiempo = str(fila.get('modificador_mecanico', '')), str(fila.get('tiempo_iso_seg', '')).strip()
    return re.sub(r'(?i)\[?isométrico\]?', '', mod).replace(', ,', ',').strip(' ,') if tiempo == '' and 'isom' in mod.lower() else mod

if 'modificador_mecanico' in df_exportar.columns: df_exportar['modificador_mecanico'] = df_exportar.apply(limpiar_modificador_iso, axis=1)

cols_finales = ['ID_Sesion', 'ID_Cliente', col_counter, 'hour_date', 'Bloque_Principal', 'Nombre_Circuito_Original', 'formato_circuito', 'series_circuito', 'minutos_circuito', 'Orden', 'ejercicio_1', 'ejercicio_2', 'ejercicio_3', 'ejercicio_4', 'ejercicio_5', 'KILOS_A_LEVANTAR_HOY', 'Reps_Objetivo', 'tiempo_iso_seg', 'Velocidad_kmh', 'cantidad_otra_unidad', 'tipo_otra_unidad', 'modificador_espacial', 'modificador_mecanico', 'por_lado', 'Material_Necesario', 'color_goma', 'Confianza_IA', 'Alerta_Monitor', 'Motivo_IA']
df_exportar = df_exportar[[c for c in cols_finales if c in df_exportar.columns]]

cols_texto_limpio = ['Material_Necesario', 'ejercicio_2', 'ejercicio_3', 'ejercicio_4', 'ejercicio_5', 'cantidad_otra_unidad', 'tipo_otra_unidad', 'modificador_espacial', 'modificador_mecanico', 'Reps_Objetivo', 'KILOS_A_LEVANTAR_HOY', 'Velocidad_kmh', 'minutos_circuito', 'por_lado', 'color_goma']
for col in cols_texto_limpio:
    if col in df_exportar.columns: df_exportar[col] = df_exportar[col].astype(str).replace(['Desconocido', '[]', '', 'nan', 'None', '[-]'], '')

df_exportar.to_csv('rutinas_generadas_IA_LIMPIO.csv', sep=';', index=False, encoding='utf-8-sig')
