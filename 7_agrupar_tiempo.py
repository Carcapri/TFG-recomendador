import pandas as pd
import re
import numpy as np

archivo_entrada = 'dataset_IA_Anatomia_Compuestos.csv'
try:
    df = pd.read_csv(archivo_entrada, sep=';', encoding='utf-8-sig', low_memory=False)
except FileNotFoundError:
    print(f"No se encuentra el archivo {archivo_entrada}.")
    exit()

df.columns = df.columns.str.strip()

def extraer_lista_numeros(valor):
    if pd.isna(valor) or str(valor).strip().lower() in ['nan', '', '0.0', '0']: return []
    return [float(n) for n in re.findall(r'\d+\.?\d*', str(valor))]

def corregir_series_tiempo(row):
    formato = str(row.get('formato_circuito', '')).lower()
    nums_s = extraer_lista_numeros(row.get('series_circuito', '0'))
    nums_m = extraer_lista_numeros(row.get('minutos_circuito', '0'))
    
    series = float(nums_s[0]) if nums_s else 1.0
    mins = float(nums_m[0]) if nums_m else 0.0
    
    if any(x in formato for x in ['emom', 'amrap', '21-15-9', 'tiempo', 'min']):
        if series > 5 and mins == 0.0: return pd.Series([1.0, series]) 
    return pd.Series([series, mins])

if 'series_circuito' in df.columns and 'minutos_circuito' in df.columns:
    df[['series_circuito', 'minutos_circuito']] = df.apply(corregir_series_tiempo, axis=1)


def limpiar_texto_extremo(x):
    if pd.isna(x) or str(x).strip().lower() in ['nan', '']: return np.nan
    return re.sub(r'[\[\]\'\"]', '', str(x)).strip(', ')

cols_texto = ['equipamiento', 'intensidad_ca', 'color_goma', 'modificador_e', 'modificador_r', 'formato_circuito', 'tipo_circuito']
txt_existentes = [c for c in cols_texto if c in df.columns]
for col in txt_existentes: df[col] = df[col].apply(limpiar_texto_extremo)

MAX_SERIES = 5
col_cant = next((c for c in df.columns if 'cantidad' in c.lower() and 'otra' in c.lower()), None)
col_unid = next((c for c in df.columns if 'tipo' in c.lower() and 'otra' in c.lower()), None)

def extraer_cardio_clonador(row):
    cant_raw = str(row[col_cant]) if col_cant and pd.notna(row[col_cant]) else ''
    unid_raw = str(row[col_unid]) if col_unid and pd.notna(row[col_unid]) else ''
    n_series = max(1, min(int(row.get('series_circuito', 1)), MAX_SERIES))
    series_data = [{'kcal':0.0, 'min':0.0, 'kmh':0.0, 'm':0.0, 'w':0.0} for _ in range(MAX_SERIES)]
    
    if cant_raw.strip() and unid_raw.strip() and cant_raw.lower() != 'nan' and unid_raw.lower() != 'nan':
        cant_bloques = re.findall(r'\[([^\[\]]+)\]', cant_raw)
        unid_bloques = re.findall(r'\[([^\[\]]+)\]', unid_raw)
        if not cant_bloques: cant_bloques = [cant_raw]
        if not unid_bloques: unid_bloques = [unid_raw]
        
        for i in range(MAX_SERIES):
            if i < n_series:
                idx_c = i if i < len(cant_bloques) else len(cant_bloques) - 1
                idx_u = i if i < len(unid_bloques) else len(unid_bloques) - 1
                nums = [float(n) for n in re.findall(r'\d+\.?\d*', cant_bloques[idx_c])]
                unis = [t.strip().lower() for t in unid_bloques[idx_u].split(',') if t.strip()]
                for j in range(min(len(nums), len(unis))):
                    val, u = nums[j], unis[j]
                    if 'cal' in u: series_data[i]['kcal'] = max(series_data[i]['kcal'], val)
                    elif any(x in u for x in ['min', 'tiempo', 'seg']): series_data[i]['min'] = max(series_data[i]['min'], val)
                    elif any(x in u for x in ['km/h', 'vel', 'rpm']): series_data[i]['kmh'] = max(series_data[i]['kmh'], val)
                    elif any(x in u for x in ['m', 'km', 'dist']): series_data[i]['m'] = max(series_data[i]['m'], val)
                    elif any(x in u for x in ['w', 'vat']): series_data[i]['w'] = max(series_data[i]['w'], val)

    flat_res = []
    for i in range(MAX_SERIES):
        flat_res.extend([series_data[i]['kcal'], series_data[i]['min'], series_data[i]['kmh'], series_data[i]['m'], series_data[i]['w']])
    return flat_res

cols_cardio = []
for i in range(1, MAX_SERIES+1): cols_cardio.extend([f'kcal_s{i}', f'min_s{i}', f'kmh_s{i}', f'm_s{i}', f'w_s{i}'])
df[cols_cardio] = df.apply(extraer_cardio_clonador, axis=1, result_type='expand')

def procesar_fuerza_expandida(row, col_name):
    if col_name not in row: return [0.0]*MAX_SERIES
    lista = extraer_lista_numeros(row[col_name])
    if not lista: return [0.0]*MAX_SERIES
    n_series = max(1, min(int(row.get('series_circuito', 1)), MAX_SERIES))
    res = []
    for i in range(MAX_SERIES):
        if i < n_series:
            res.append(lista[i] if i < len(lista) else lista[-1])
        else:
            res.append(0.0)
    return res

pesos_exp = df.apply(lambda row: procesar_fuerza_expandida(row, 'peso_kg'), axis=1)
reps_exp = df.apply(lambda row: procesar_fuerza_expandida(row, 'repeticiones'), axis=1)
df['volumen_total_reps'] = reps_exp.apply(sum)

for i in range(MAX_SERIES):
    df[f'peso_s{i+1}'] = pesos_exp.apply(lambda x: x[i])
    df[f'reps_s{i+1}'] = reps_exp.apply(lambda x: x[i])


cols_cat_maestra = [c for c in df.columns if c.startswith('categoria_maestra_')]

def crear_firma_circuito(row):
    categorias = []
    for col in cols_cat_maestra:
        val = str(row.get(col, 'Estructura / Basura'))
        if val not in ['Estructura / Basura', 'nan', 'None', '']:
            categorias.append(val)
    return " + ".join(categorias) if categorias else 'Basura Total'

df['firma_circuito'] = df.apply(crear_firma_circuito, axis=1)

df = df.sort_values(['customer_id', 'firma_circuito', 'counter'])

df['peso_temp'] = df['peso_s1'].replace(0.0, np.nan)
df['nivel_fuerza_patron'] = df.groupby(['customer_id', 'firma_circuito', 'tipo_circuito'])['peso_temp'].transform(lambda x: x.expanding().mean()).round(2).fillna(0.0)


df = df.sort_values(['customer_id', 'counter'])

df = df[df['firma_circuito'] != 'Basura Total'].copy()

grupo = df.groupby(['customer_id', 'firma_circuito'])

cols_anatomia = [col for col in df.columns if col.startswith('categoria_maestra_') or col.startswith('musculo_') or col.startswith('tipo_ejercicio_') or col.startswith('ejercicio_')]

variables_futuras = ['firma_circuito'] + cols_anatomia + ['volumen_total_reps'] + txt_existentes + [f'peso_s{i}' for i in range(1,6)] + [f'reps_s{i}' for i in range(1,6)] + cols_cardio

if 'color_goma' in df.columns: variables_futuras.append('asistencia_goma_kg')
col_iso = next((c for c in df.columns if 'iso' in c.lower() and 'tiempo' in c.lower()), None)
if col_iso: variables_futuras.append(col_iso)
col_rir = next((c for c in df.columns if 'rir' in c.lower()), None)
if col_rir: variables_futuras.append(col_rir)

for col in variables_futuras:
    if col in df.columns:
        df[f'{col}_SIGUIENTE'] = grupo[col].shift(-1)

col_verificacion = 'firma_circuito_SIGUIENTE'

df_entrenamiento = df.dropna(subset=[col_verificacion]).copy()
df_predecir = df[df[col_verificacion].isna()].copy()

df_entrenamiento.to_csv('dataset_entrenamiento.csv', sep=';', index=False, encoding='utf-8-sig')
df_predecir.to_csv('dataset_predecir.csv', sep=';', index=False, encoding='utf-8-sig')

print(f"Filas para dataset de entrenamiento: {len(df_entrenamiento)} ")
print(f"Filas para dataset de predecir: {len(df_predecir)} ")