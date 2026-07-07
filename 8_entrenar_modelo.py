import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from catboost import CatBoostClassifier
from sklearn.metrics import accuracy_score

df_entrenamiento = pd.read_csv('dataset_entrenar.csv', sep=';', encoding='utf-8-sig', low_memory=False)

df_entrenamiento['customer_id'] = df_entrenamiento['customer_id'].astype(str)

df = df_entrenamiento.copy()
df['counter'] = pd.to_numeric(df['counter'], errors='coerce')

df = df[df['firma_circuito'] != 'Basura Total'].copy() if 'firma_circuito' in df.columns else df[~df['tipo_ejercicio_1'].isin(['Ignorar'])].copy()

col_agrupacion = 'firma_circuito' if 'firma_circuito' in df.columns else 'categoria_maestra_1'

df = df.sort_values(by=['customer_id', col_agrupacion, 'counter'], ascending=[True, True, True])

df['sesiones_descanso'] = df.groupby(['customer_id', col_agrupacion])['counter'].diff().fillna(5.0)

cols_fuerza = ['peso_s1', 'peso_s1_SIGUIENTE', 'reps_s1', 'reps_s1_SIGUIENTE']
for col in cols_fuerza:
    if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    else: df[col] = 0.0

df['tonelaje_actual'] = df['peso_s1'] * df['reps_s1']
df['tonelaje_medio'] = df.groupby(['customer_id', col_agrupacion])['tonelaje_actual'].transform(lambda x: x.rolling(window=3, min_periods=1).mean())
df['fatiga_por_volumen'] = (df['tonelaje_actual'] / df['tonelaje_medio']).replace([np.inf, -np.inf], 1.0).fillna(1.0)

peso_sin_ceros = df['peso_s1'].replace(0.0, np.nan)
df['fuerza_base_historica'] = peso_sin_ceros.groupby([df['customer_id'], df['categoria_maestra_1']]).transform(lambda x: x.expanding().max()).fillna(0.0)

if 'modificador_mecanico' in df.columns:
    df['cm_salto_s1'] = df['modificador_mecanico'].astype(str).str.extract(r'(\d+)\s*cm', expand=False).astype(float).fillna(0.0)
    df['angulo_banco'] = df['modificador_mecanico'].astype(str).str.extract(r'(\d+)\s*[º|grados]', expand=False).astype(float).fillna(0.0)
else:
    df['cm_salto_s1'] = 0.0
    df['angulo_banco'] = 0.0

if 'modificador_mecanico_SIGUIENTE' in df.columns:
    df['cm_salto_s1_SIGUIENTE'] = df['modificador_mecanico_SIGUIENTE'].astype(str).str.extract(r'(\d+)\s*cm', expand=False).astype(float).fillna(0.0)
else:
    df['cm_salto_s1_SIGUIENTE'] = 0.0

min_s1 = pd.to_numeric(df['min_s1'], errors='coerce').fillna(0.0) if 'min_s1' in df.columns else 0.0
seg_s1 = pd.to_numeric(df['seg_s1'], errors='coerce').fillna(0.0) if 'seg_s1' in df.columns else 0.0
tiempo_total_min = min_s1 + (seg_s1 / 60.0)

min_sig = pd.to_numeric(df['min_s1_SIGUIENTE'], errors='coerce').fillna(0.0) if 'min_s1_SIGUIENTE' in df.columns else 0.0
seg_sig = pd.to_numeric(df['seg_s1_SIGUIENTE'], errors='coerce').fillna(0.0) if 'seg_s1_SIGUIENTE' in df.columns else 0.0
tiempo_total_min_sig = min_sig + (seg_sig / 60.0)

pasillos = pd.to_numeric(df['pasillos_s1'], errors='coerce').fillna(0.0) if 'pasillos_s1' in df.columns else 0.0
metros_base = pd.to_numeric(df['m_s1'], errors='coerce').fillna(0.0) if 'm_s1' in df.columns else 0.0
metros_totales = metros_base + (pasillos * 10.0)

pasillos_sig = pd.to_numeric(df['pasillos_s1_SIGUIENTE'], errors='coerce').fillna(0.0) if 'pasillos_s1_SIGUIENTE' in df.columns else 0.0
metros_base_sig = pd.to_numeric(df['m_s1_SIGUIENTE'], errors='coerce').fillna(0.0) if 'm_s1_SIGUIENTE' in df.columns else 0.0
metros_totales_sig = metros_base_sig + (pasillos_sig * 10.0)

if 'intensidad_cardio' in df.columns:
    int_str = df['intensidad_cardio'].astype(str).str.lower()
    condiciones_intensidad = [
        int_str.str.contains('sprint|máxima|maxima|tope', na=False),
        int_str.str.contains('muy fuerte|durísim', na=False),
        int_str.str.contains('rápid|fuerte|alta', na=False),
        int_str.str.contains('muy suave|recuperación', na=False),
        int_str.str.contains('suave|baja|liger', na=False)
    ]
    df['multiplicador_esfuerzo'] = np.select(
        condiciones_intensidad,
        [4.0, 2.5, 1.5, 0.5, 0.8],
        default=1.0
    )
else:
    df['multiplicador_esfuerzo'] = 1.0

df['carga_metabolica_actual'] = (tiempo_total_min + (pd.to_numeric(df['kcal_s1'], errors='coerce').fillna(0.0) / 10.0) + (metros_totales / 100.0)) * df['multiplicador_esfuerzo']
df['carga_metabolica_media'] = df.groupby(['customer_id', col_agrupacion])['carga_metabolica_actual'].transform(lambda x: x.rolling(window=3, min_periods=1).mean())
df['fatiga_metabolica'] = (df['carga_metabolica_actual'] / df['carga_metabolica_media']).replace([np.inf, -np.inf], 1.0).fillna(1.0)

kcal_actual = pd.to_numeric(df['kcal_s1'], errors='coerce').fillna(0.0) if 'kcal_s1' in df.columns else 0.0
kcal_sig = pd.to_numeric(df['kcal_s1_SIGUIENTE'], errors='coerce').fillna(0.0) if 'kcal_s1_SIGUIENTE' in df.columns else 0.0
kmh_actual = pd.to_numeric(df['kmh_s1'], errors='coerce').fillna(0.0) if 'kmh_s1' in df.columns else 0.0
kmh_sig = pd.to_numeric(df['kmh_s1_SIGUIENTE'], errors='coerce').fillna(0.0) if 'kmh_s1_SIGUIENTE' in df.columns else 0.0

prog_peso = df['peso_s1_SIGUIENTE'] > df['peso_s1']
prog_reps = (df['peso_s1'] == 0) & (df['reps_s1_SIGUIENTE'] > df['reps_s1'])
prog_min = tiempo_total_min_sig > tiempo_total_min
prog_m = metros_totales_sig > metros_totales
prog_kcal = kcal_sig > kcal_actual
prog_kmh = kmh_sig > kmh_actual
prog_cm = df['cm_salto_s1_SIGUIENTE'] > df['cm_salto_s1']

hubo_progresion = prog_peso | prog_reps | prog_min | prog_m | prog_kcal | prog_kmh | prog_cm

reg_peso = (df['peso_s1_SIGUIENTE'] < df['peso_s1']) & (df['peso_s1_SIGUIENTE'] > 0)
reg_reps = (df['peso_s1'] == 0) & (df['reps_s1_SIGUIENTE'] < df['reps_s1']) & (df['reps_s1_SIGUIENTE'] > 0)
reg_min = (tiempo_total_min_sig < tiempo_total_min) & (tiempo_total_min_sig > 0)
reg_m = (metros_totales_sig < metros_totales) & (metros_totales_sig > 0)
reg_kcal = (kcal_sig < kcal_actual) & (kcal_sig > 0)
reg_cm = (df['cm_salto_s1_SIGUIENTE'] < df['cm_salto_s1']) & (df['cm_salto_s1_SIGUIENTE'] > 0)

hubo_regresion = reg_peso | reg_reps | reg_min | reg_m | reg_kcal | reg_cm

df['decision_estrategica'] = np.select([hubo_regresion, hubo_progresion], [0, 2], default=1)

col_ej_original = next((c for c in ['ej_1', 'ejercicio_limpio', 'ejercicio_1'] if c in df.columns), None)

columnas_categoricas = ['customer_id']
if 'firma_circuito' in df.columns: columnas_categoricas.append('firma_circuito')

columnas_categoricas.extend(['categoria_maestra_1', 'musculo_principal_1', 'tipo_ejercicio_1'])

if col_ej_original: columnas_categoricas.append(col_ej_original)
if 'equipamiento' in df.columns: columnas_categoricas.append('equipamiento')
if 'tipo_circuito' in df.columns: columnas_categoricas.append('tipo_circuito')

if 'modificador_mecanico' in df.columns: columnas_categoricas.append('modificador_mecanico')

for col in columnas_categoricas:
    df[col] = df[col].fillna('Desconocido').astype(str)

cols_peso = [f'peso_s{i}' for i in range(1, 6) if f'peso_s{i}' in df.columns]
cols_reps = [f'reps_s{i}' for i in range(1, 6) if f'reps_s{i}' in df.columns]

cols_cardio = [c for c in df.columns if any(x in c for x in ['min_s', 'seg_s', 'kcal_s', 'm_s', 'kmh_s', 'pasillos_s']) and 'SIGUIENTE' not in c]

columnas_numericas = ['sesiones_descanso', 'fatiga_por_volumen', 'fatiga_metabolica', 'tonelaje_actual', 'carga_metabolica_actual', 'fuerza_base_historica'] + cols_peso + cols_reps + cols_cardio

for col in columnas_numericas:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

col_angulo = 'angulo_banco'
if col_angulo in df.columns:
    df[col_angulo] = pd.to_numeric(df[col_angulo], errors='coerce').fillna(0.0)
    if col_angulo not in columnas_numericas: columnas_numericas.append(col_angulo)

col_cm = 'cm_salto_s1'
if col_cm in df.columns:
    df[col_cm] = pd.to_numeric(df[col_cm], errors='coerce').fillna(0.0)
    if col_cm not in columnas_numericas: columnas_numericas.append(col_cm)

col_iso = next((c for c in df.columns if 'iso' in c.lower() and 'tiempo' in c.lower()), None)
if col_iso:
    df[col_iso] = pd.to_numeric(df[col_iso], errors='coerce').fillna(0.0)
    if col_iso not in columnas_numericas: columnas_numericas.append(col_iso)

col_rir = next((c for c in df.columns if 'rir' in c.lower()), None)
if col_rir:
    df[col_rir] = pd.to_numeric(df[col_rir], errors='coerce')
    if col_rir not in columnas_numericas: columnas_numericas.append(col_rir)

col_minutos_circ = next((c for c in df.columns if 'minutos_circ' in c.lower()), None)
if col_minutos_circ:
    df[col_minutos_circ] = pd.to_numeric(df[col_minutos_circ], errors='coerce').fillna(0.0)
    if col_minutos_circ not in columnas_numericas: columnas_numericas.append(col_minutos_circ)

columnas_totales = columnas_categoricas + columnas_numericas

# Si no se puede calcular
df_limpio = df.dropna(subset=['decision_estrategica']).copy()

X = df_limpio[columnas_totales]
y = df_limpio['decision_estrategica'].astype(int)

#Entrenamos el 80%, el 20% restante para testear
#Siempre misma semilla para evitar resultados aleatorios
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
cat_features_indices = [X.columns.get_loc(col) for col in columnas_categoricas]

modelo_final = CatBoostClassifier(
    iterations=1200,
    learning_rate=0.04,
    depth=7,
    l2_leaf_reg=4,
    auto_class_weights='Balanced',
    cat_features=cat_features_indices,
    task_type="GPU",
    verbose=100,
    random_seed=42
)

modelo_final.fit(X_train, y_train, eval_set=(X_test, y_test), early_stopping_rounds=50)

probabilidades = modelo_final.predict_proba(X_test)
decision_ia = np.argmax(probabilidades, axis=1)
seguridad_ia = np.max(probabilidades, axis=1)

#Nivel de seguridad de la IA, si la decisión supera al umbral, elige esa opción, si está por debajo
#elige la de mayor porcentaje pero indica duda al monitor. Mayor umbral aumenta el nivel de confianza, pero
#apenas automatiza y releva casi todo al entrenador
UMBRAL = 0.55
casos_automatizados = seguridad_ia >= UMBRAL
y_test_seguros = y_test[casos_automatizados]
predicciones_seguras = decision_ia[casos_automatizados]

total_clientes = len(y_test)
clientes_automatizados = sum(casos_automatizados)
porcentaje_automatizacion = (clientes_automatizados / total_clientes) * 100
exactitud_segura = accuracy_score(y_test_seguros, predicciones_seguras)

print("\nResultados")
print("-"*70)
print(f"Porcentaje automatizado: {porcentaje_automatizacion:.1f}%")
print(f"Porcentaje para que revise el monitor: {100 - porcentaje_automatizacion:.1f}%")
print("-" * 70)
print(f"Precisión IA: {exactitud_segura*100:.2f}%")

importancias = pd.Series(modelo_final.get_feature_importance(), index=X.columns).sort_values(ascending=False)
print("\nTop 15 variables:")
print(importancias.head(15).to_string())
modelo_final.save_model('modelo_fitness_v1.cbm')