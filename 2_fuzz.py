import pandas as pd
import re
from rapidfuzz import fuzz
from itertools import combinations

df = pd.read_csv('resultado_limpio.csv', sep=';', encoding='utf-8-sig')

ejercicios_unicos = df['ejercicio_limpio'].dropna().unique()
print(f"Se han encontrado {len(ejercicios_unicos)} ejercicios únicos. Comparando...")

def normalizar(s):
    s = str(s).lower().strip()
    s = re.sub(r'[^a-záéíóúüñ0-9 ]', '', s)
    s = re.sub(r'\b(de|con|en|el|la|los|las|un|una|para|y)\b', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def es_subconjunto(a, b):
    pal_a, pal_b = set(a.split()), set(b.split())
    if not pal_a or not pal_b or pal_a == pal_b:
        return False
    return pal_a.issubset(pal_b) or pal_b.issubset(pal_a)

resultados = []
dict_norm = {ej: normalizar(ej) for ej in ejercicios_unicos}

for ej1, ej2 in combinations(ejercicios_unicos, 2):
    norm1 = dict_norm[ej1]
    norm2 = dict_norm[ej2]
    
    if not norm1 or not norm2: continue
        
    similitud = round(fuzz.token_sort_ratio(norm1, norm2))
    
    subconjunto = es_subconjunto(norm1, norm2)
    
    if similitud >= 80 or subconjunto:
        resultados.append({
            'ejercicio_1': ej1,
            'ejercicio_2': ej2,
            'similitud': similitud,
            'es_subconjunto': subconjunto,
            'son_identicos': norm1 == norm2
        })

df_pares = pd.DataFrame(resultados)

nivel1 = df_pares[df_pares['son_identicos'] | ((df_pares['similitud'] >= 90) & ~df_pares['es_subconjunto'])]

nivel2 = df_pares[(df_pares['similitud'] >= 85) & (df_pares['similitud'] < 90) & ~df_pares['es_subconjunto']]

descartados = df_pares[df_pares['es_subconjunto']]

nivel1.to_csv('fusion_automatica.csv', sep=';', encoding='utf-8-sig', index=False)
nivel2.to_csv('fusion_revisar.csv', sep=';', encoding='utf-8-sig', index=False)
descartados.to_csv('fusion_descartados.csv', sep=';', encoding='utf-8-sig', index=False)
