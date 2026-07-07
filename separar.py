import pandas as pd

def separar_por_utilidad():    
    try:
        df = pd.read_csv('resultado_limpio.csv', sep=';', encoding='utf-8')
    except FileNotFoundError:
        print(" Error: No se encuentra resultado_limpio.csv.")
        return

    niveles = df['utilidad'].dropna().astype(int).unique()
    niveles.sort()

    for nivel in niveles:
        df_filtrado = df[df['utilidad'] == nivel]
        
        if nivel == 0:
            nombre = "0_datos_perfectos.csv"
        elif nivel == 1:
            nombre = "1_auditoria_textos_largos.csv"
        elif nivel == 2:
            nombre = "2_auditoria_valores_extremos.csv"
        elif nivel == 3:
            nombre = "3_auditoria_nulos_y_basura.csv"
        elif nivel == 4:
            nombre = "4_auditoria_circuitos.csv"
        else:
            nombre = f"auditoria_utilidad_{nivel}.csv"
            
        df_filtrado.to_csv(nombre, sep=';', index=False, encoding='utf-8-sig')
        print(f"Archivo guardado: {nombre} ({len(df_filtrado)} filas)")


if __name__ == "__main__":
    separar_por_utilidad()