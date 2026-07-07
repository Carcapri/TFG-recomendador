import pandas as pd

print("Cargando base de datos...")
df = pd.read_csv('resultado_ESTANDARIZADO.csv', sep=';', encoding='utf-8-sig')

if 'circuito' in df.columns:
    series_rescatadas = df['circuito'].str.extract(r'(?i)x\s*(\d+)', expand=False)
    df['series_circuito'] = df['series_circuito'].fillna(series_rescatadas)

df['tipo_circuito'] = df['tipo_circuito'].fillna('General')

df['series_circuito'] = df['series_circuito'].fillna(1)
df['series_circuito'] = df['series_circuito'].astype(float).astype(int)

columnas_basura = ['ejercicio_bruto', 'circuito']
columnas_a_borrar = [col for col in columnas_basura if col in df.columns]
df = df.drop(columns=columnas_a_borrar)

print(f"Columnas eliminadas: {columnas_a_borrar}")

nombre_salida = 'dataset_IA_listo.csv'
df.to_csv(nombre_salida, sep=';', index=False, encoding='utf-8-sig')
