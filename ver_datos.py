import pandas as pd
import dtale

# df = pd.read_csv('resultado_limpio.csv', sep=';', dtype=str)
df = pd.read_csv('resultado_limpio.csv', sep=';', encoding='utf-8-sig', low_memory=False)
d = dtale.show(df)
print(f"enlace: {d.main_url()}")
input("enter para cerrar el servidor...")