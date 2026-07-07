import pandas as pd
import requests
from thefuzz import process, fuzz
from deep_translator import GoogleTranslator
import time
from tqdm import tqdm 

archivo_principal = 'dataset_IA_listo.csv'
archivo_kaggle = 'megaGymDataset.csv'

try:
    df_gym = pd.read_csv(archivo_principal, sep=';', encoding='utf-8-sig', low_memory=False)
    df_kaggle = pd.read_csv(archivo_kaggle, sep=';', encoding='utf-8-sig') 
except FileNotFoundError as e:
    exit()


opciones_kaggle = df_kaggle['Exercise_Name'].tolist() if 'Exercise_Name' in df_kaggle.columns else []
traductor = GoogleTranslator(source='es', target='en')

diccionario_manual = {
    'powerkibe': {'musculo': 'Cuerpo Completo', 'categoria': 'Cardio / Metabólico'},
    'battlerope': {'musculo': 'Cuerpo Completo', 'categoria': 'Cardio / Metabólico'},
    'add cadera': {'musculo': 'Adductores', 'categoria': 'Hip / Glute Isolation'}
}

def consultar_wger_api(ejercicio_en):
    try:
        url = f"https://wger.de/api/v2/exercise/search/?term={ejercicio_en}"
        res = requests.get(url, timeout=4)
        if res.status_code == 200:
            data = res.json()
            if data.get('suggestions'):
                mejor_resultado = data['suggestions'][0]['value']
                return {'musculo': 'Asignación Automática (Wger)', 'categoria': 'Fuerza', 'match': mejor_resultado}
    except Exception:
        pass 
    return None

def clasificar_ejercicio_maestro(ejercicio_es):
    ej_limpio = str(ejercicio_es).lower().strip()
    
    if ej_limpio in diccionario_manual:
        return pd.Series({
            'ejercicio_original': ejercicio_es,
            'fuente_datos': '1. Regla Manual', 
            'musculo_principal_1': diccionario_manual[ej_limpio]['musculo'],
            'categoria_maestra_1': diccionario_manual[ej_limpio]['categoria']
        })
        
    try:
        ejercicio_en = traductor.translate(ej_limpio)
    except:
        ejercicio_en = ej_limpio

    if opciones_kaggle:
        mejor_match, puntuacion = process.extractOne(ejercicio_en, opciones_kaggle, scorer=fuzz.token_set_ratio)
        if puntuacion > 75:  
            datos = df_kaggle[df_kaggle['Exercise_Name'] == mejor_match].iloc[0]
            return pd.Series({
                'ejercicio_original': ejercicio_es,
                'fuente_datos': f'2. Kaggle DB ({puntuacion}%)', 
                'musculo_principal_1': datos['Muscle_Target'] if 'Muscle_Target' in df_kaggle.columns else 'Desconocido',
                'categoria_maestra_1': datos['Mechanics'] if 'Mechanics' in df_kaggle.columns else 'Fuerza'
            })
        
    time.sleep(0.3)
    resultado_wger = consultar_wger_api(ejercicio_en)
    if resultado_wger:
        return pd.Series({
            'ejercicio_original': ejercicio_es,
            'fuente_datos': '3. Wger API', 
            'musculo_principal_1': resultado_wger['musculo'],
            'categoria_maestra_1': resultado_wger['categoria']
        })
        
    return pd.Series({
        'ejercicio_original': ejercicio_es,
        'fuente_datos': '4. Fallback', 
        'musculo_principal_1': 'Otros / General',
        'categoria_maestra_1': 'General / No Clasificado'
    })


columna_objetivo = 'ejercicio_limpio' 
if columna_objetivo not in df_gym.columns:
    exit()

ejercicios_unicos = df_gym[columna_objetivo].dropna().unique()

tqdm.pandas(desc="Clasificando Ejercicios")
df_mapeo = pd.Series(ejercicios_unicos).progress_apply(clasificar_ejercicio_maestro)

df_final = pd.merge(df_gym, df_mapeo, left_on=columna_objetivo, right_on='ejercicio_original', how='left')

df_final = df_final.drop(columns=['ejercicio_original'])

nombre_salida = 'dataset_IA_Anatomia_Compuestos_2.csv'
df_final.to_csv(nombre_salida, sep=';', index=False, encoding='utf-8-sig')