import pandas as pd

def crear_diccionario():
    print("Cargando 'resultado_limpio.csv'...")
    
    try:
        df = pd.read_csv('resultado_limpio.csv', sep=';', encoding='utf-8-sig')
    except FileNotFoundError:
        print("Error: No se encuentra resultado_limpio.csv. ")
        return

    cols_posibles = ['ejercicio_limpio', 'ejercicio_2', 'ejercicio_3', 'ejercicio_4', 'ejercicio_5']
    cols_existentes = [col for col in cols_posibles if col in df.columns]

    print("Extrayendo ejercicios únicos...")
    
    todos_los_ejercicios = pd.concat([df[col] for col in cols_existentes])

    ejercicios_limpios = todos_los_ejercicios.dropna().astype(str).str.strip()
    
    ejercicios_limpios = ejercicios_limpios[ejercicios_limpios != ""]

    ejercicios_unicos = ejercicios_limpios.unique()
    ejercicios_unicos.sort()

    df_diccionario = pd.DataFrame({
        'nombre_original': ejercicios_unicos,
        'nombre_limpio': ejercicios_unicos
    })

    nombre_archivo_salida = 'diccionario_ejercicios.csv'
    df_diccionario.to_csv(nombre_archivo_salida, sep=';', encoding='utf-8-sig', index=False)
    
    print(f"Se ha creado '{nombre_archivo_salida}' con {len(ejercicios_unicos)} ejercicios")

if __name__ == '__main__':
    crear_diccionario()