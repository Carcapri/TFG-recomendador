import pandas as pd

df = pd.read_csv('fusion_revisar.csv', sep=';', encoding='utf-8-sig')

ejercicios_dudosos = pd.concat([df['ejercicio_1'], df['ejercicio_2']]).unique()

df_or = pd.DataFrame({'ejercicio_original': ejercicios_dudosos})
df_or.to_csv('para_openrefine.csv', sep=';', encoding='utf-8-sig', index=False)
