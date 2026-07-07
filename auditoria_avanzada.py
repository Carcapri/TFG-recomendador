import pandas as pd
import re
import ast

df = pd.read_csv('resultado_limpio.csv', sep=';')

def tiene_letras(valor):
    if pd.isna(valor) or str(valor).strip() in ['[]', 'None', 'nan', '']: 
        return False
    return bool(re.search(r'[a-zA-Z]', str(valor)))

df['error_letras_peso'] = df['peso_kg'].apply(tiene_letras)
df['error_letras_reps'] = df['repeticiones'].apply(tiene_letras)

errores_formato = df[df['error_letras_peso'] | df['error_letras_reps']]

def buscar_outliers(valor_str, limite):
    if pd.isna(valor_str) or str(valor_str).strip() in ['[]', 'None', 'nan', '']: 
        return False
    numeros = re.findall(r'\d+', str(valor_str))
    for num in numeros:
        if int(num) > limite: 
            return True
    return False

df['outlier_peso'] = df['peso_kg'].apply(lambda x: buscar_outliers(x, 300))
df['outlier_reps'] = df['repeticiones'].apply(lambda x: buscar_outliers(x, 100))

errores_outliers = df[df['outlier_peso'] | df['outlier_reps']]

columnas_export = ['id', 'ejercicio_bruto', 'ejercicio_limpio', 'peso_kg', 'repeticiones']

if not errores_formato.empty:
    errores_formato[columnas_export].to_csv('qa_formato.csv', sep=';', index=False, encoding='utf-8-sig')
    print(f"{len(errores_formato)} errores")

if not errores_outliers.empty:
    errores_outliers[columnas_export].to_csv('qa_outliers.csv', sep=';', index=False, encoding='utf-8-sig')
    print(f"{len(errores_outliers)} valores extremo")
