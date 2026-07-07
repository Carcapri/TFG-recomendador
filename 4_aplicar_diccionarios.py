import pandas as pd

df_principal = pd.read_csv('resultado_limpio.csv', sep=';', encoding='utf-8-sig')

df_auto = pd.read_csv('fusion_automatica.csv', sep=';', encoding='utf-8-sig')
mapa_auto = dict(zip(df_auto['ejercicio_2'], df_auto['ejercicio_1']))

df_or = pd.read_csv('diccionario_openrefine.csv', sep=',', encoding='utf-8-sig')
df_or = df_or[df_or['ejercicio_original'] != df_or['ejercicio_estandar']]
mapa_or = dict(zip(df_or['ejercicio_original'], df_or['ejercicio_estandar']))

traductor = {**mapa_auto, **mapa_or}

columnas = ['ejercicio_limpio', 'ejercicio_2', 'ejercicio_3', 'ejercicio_4', 'ejercicio_5']

for col in columnas:
    df_principal[col] = df_principal[col].map(traductor).fillna(df_principal[col])

df_principal.to_csv('resultado_ESTANDARIZADO.csv', sep=';', index=False, encoding='utf-8-sig')
