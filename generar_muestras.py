import pandas as pd


df = pd.read_csv('resultado_limpio.csv', sep=';')

muestra_total = df.sample(n=50, random_state=None)

lotes = []
for i in range(50):
    numero_lote = (i // 10) + 1
    lotes.append(f"Lote {numero_lote}")

muestra_total.insert(0, 'Lote', lotes)

columnas_revision = [
    'Lote',
    'id', 
    'ejercicio_bruto', 
    'ejercicio_limpio', 
    'ejercicio_2',      
    'ejercicio_3',
    'ejercicio_4',
    'ejercicio_5',
    'peso_kg', 
    'repeticiones',
    'por_lado',
    'color_goma',
    'tiempo_iso_seg',
    'rir',
    'cantidad_otra_unidad', 
    'tipo_otra_unidad', 
]
muestra_final = muestra_total[columnas_revision]

muestra_final.to_csv('muestras_qa.csv', sep=';', index=False, encoding='utf-8-sig')

print("¡Muestras generadas!")
