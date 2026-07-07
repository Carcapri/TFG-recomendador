import pandas as pd

df = pd.read_csv('resultado_limpio.csv', sep=';', dtype=str)

nombres_sucios = df[df['ejercicio_limpio'].str.contains(r'\d', na=False, regex=True)]
print(nombres_sucios['ejercicio_limpio'].value_counts().head(20))

print("\n--------------------------------------------------\n")

kilos_perdidos = df[df['ejercicio_bruto'].str.contains(r'kg', case=False, na=False) & df['peso_kg'].isnull()]
for texto in kilos_perdidos['ejercicio_bruto'].head(10):
    print(f"-> {texto}")