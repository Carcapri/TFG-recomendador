import pandas as pd


df = pd.read_csv('resultado_limpio.csv', sep=';')

df_limpio = df.dropna(subset=['ejercicio_limpio'])
filas_largas = df_limpio[df_limpio['ejercicio_limpio'].str.len() > 60]

resultado = filas_largas[['id', 'ejercicio_bruto', 'ejercicio_limpio', 'peso_kg', 'repeticiones']]

resultado.to_csv('frases_largas.csv', sep=';', index=False, encoding='utf-8-sig')

print(f"Se han encontrado {len(filas_largas)}")
