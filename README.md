# Motor de IA y Procesamiento de datos (Fase Analítica)

Este repositorio contiene los subproyectos de ingeniería de datos y entrenamiento del modelo predictivo (Inteligencia artificial) correspondientes al Trabajo de Fin de Grado. 

Incluye todo el código fuente necesario para la extracción, limpieza, estructuración y análisis algorítmico del histórico de sesiones, finalizando con la exportación del modelo `.cbm` (CatBoost) que posteriormente es consumido por la API en el servidor web.

## Pipeline de Ejecución

El código está estructurado de forma cronológica para procesar los datos en bruto hasta obtener predicciones. El orden lógico de ejecución es el siguiente:

* 1_script.py: Procesamiento léxico inicial. Limpieza de texto libre, corrección de saltos de línea y extracción de métricas numéricas mediante expresiones regulares.
* 2_fuzz.py: Estandarización de la nomenclatura empleando la distancia de Levenshtein para agrupaciones automáticas de ejercicios.
* 3_preparar_openrefine.py: Generación de los subconjuntos de datos dudosos para su resolución en OpenRefine.
* Agrupar en OpenRefine.
* 4_aplicar_diccionarios.py: Reintegración de los diccionarios limpios y sustitución de los nombres brutos en el conjunto principal.
* 6_api_musculos.py: Clasificación anatómica y biomecánica de los ejercicios estructurados.
* 7_agrupar_tiempo.py: Ordenación cronológica, cálculo de medias móviles y agrupación de variables temporales para la evaluación de la fatiga.
* 8_entrenar_modelo.py: Configuración, entrenamiento y exportación del modelo de clasificación CatBoost (modelo_final.cbm).
* 9_predecir.py: Script de evaluación de inferencia y pruebas de predicción sobre nuevos registros.

## Advertencia de Ejecución

NO EJECUTAR el archivo 6_2_musculos.py. Este script contiene código residual o pruebas descartadas de la fase de clasificación muscular y su ejecución puede generar conflictos o corromper el flujo de datos estructurado. Utilizar exclusivamente 6_api_musculos.py para esta tarea.

## Archivos y Recursos Adicionales

El repositorio también actúa como espacio de trabajo y almacenamiento de los artefactos generados durante el proceso de investigación:

* Informes de auditoría (.html): Reportes visuales de la salud de los datos generados mediante herramientas de perfilado (ej. reporte_Final2603.html).
* Conjuntos de datos (.csv): Incluye tanto volcados intermedios para revisión (fusion_revisar.csv) como el dataset final listo para el entrenamiento de la IA (dataset_IA_listo.csv).
* Diagramas y flujos: Se adjuntan archivos de arquitectura como el diagrama relacional de la base de datos (bbdd_diagrama.mwb), maquetación de interfaces (tfg.bmpr) y flujos de Alteryx (.yxmd).
* Scripts auxiliares: Archivos como analizar_csv.py, auditoria_avanzada.py o ver_datos.py empleados para el control de calidad y muestreo estadístico durante el desarrollo.

## Instalación de Dependencias

Para poder ejecutar los scripts de este repositorio, es necesario instalar las dependencias requeridas. Desde la terminal en la raíz del proyecto, ejecuta el siguiente comando:

```bash
pip install -r requirements.txt
