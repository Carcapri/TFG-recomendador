import pandas as pd
from ydata_profiling import ProfileReport

df = pd.read_csv('resultado_limpio.csv', sep=';') 
profile = ProfileReport(df, title="Análisis Ejercicios HTML")
profile.to_file("reporte_errores.html")
#Usar el ejercicio de google colab