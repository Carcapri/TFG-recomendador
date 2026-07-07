import pandas as pd
import re
import numpy as np

archivo_entrada = 'dataset_IA_listo.csv'
try:
    df_gym = pd.read_csv(archivo_entrada, sep=';', encoding='utf-8-sig', low_memory=False)
except FileNotFoundError:
    print(f"No se encuentra el archivo {archivo_entrada}.")
    exit()

if 'utilidad' in df_gym.columns:
    df_gym = df_gym[df_gym['utilidad'].isin([0, 1])].copy()


cols_ejercicios = [col for col in df_gym.columns if re.match(r'^(ejercicio_limpio|ejercicio_\d+|ej_\d+)$', str(col).lower())]

if len(cols_ejercicios) == 0:
    exit()

def clasificar_categoria_maestra(nombre):
    if pd.isna(nombre) or str(nombre).strip().lower() in ['nan', '', '0', 'none']: 
        return 'Estructura / Basura'
    
    nombre_str = str(nombre).lower()
    nombre_str = re.sub(r'^[\'"\-=\+@\s]+', '', nombre_str).strip()
    
    nombre_limpio = re.sub(r'\b(con|sin|sobre|desde|para|una|del|de|los|las|un|sitio|punto|más|ambos)\b', '', nombre_str).strip()
    nombre_limpio = nombre_limpio.replace('cor r e', 'corre').replace('hobro', 'hombro').replace('ddías', 'días').replace('battle rop', 'battlerope')

    reglas = {
        r'\bfuerza\b|\bsuelo\b|asistidos|repatir|\bparte\b|m[áa]quina|\bmet\b|kettlebel|acumula|time|donde quieras|\bmano\b|complex|completar|acabar|hor|#¿nombre\?|b[úu]squeda|estimado|activaci[óo]n|continuos|me quedo|y balance|pagas al final|rounds|^apoyo$|m[áa]ximos?|\bpared\b|\brodillas\b|\belegir\b|fatiga': 'Estructura / Basura',
        r'snatch|arrancada|jerk|clean|cargada|halterofilia|thruster|tir[óo]n alto|sumo high pull|tgu|cluster|levantamiento turco|\blift\b': 'Olympic Weightlifting / Power',
        r'sentadilla|\bsq\b|squat|sissy|goblet|apoyo pared|pistol|levantarse|subir y bajar|subo y bajo|cosaco|cossack|sentarse|me siento.*levanto|subo y paso|me siento': 'Squat',
        r'zancada|lunge|b[úu]lgara|split|step|subida|paso lateral|pasos amplios|vallas|velocista|marcha|lateral\b|laterales|desplazamiento lateral|lado a lado': 'Lunge / Gait',
        r'prensa|leg press': 'Leg Press',
        r'extensi[óo]n.*cu[áa]driceps|leg.*xtensi[óo]n|inverse nordic|ext.*rodilla|quads': 'Leg Extension',
        r'peso muerto|deadlift|\bdl\b|rdl|buenos d[ií]as?|swing|hiperextensi[óo]n|hiper.*extens|ciclo acort': 'Hinge (Peso Muerto)',
        r'hip thrust|hip thurst|puente|elevaci[óo]n.*cadera': 'Glute Bridge',
        r'curl.*isquio|curl.*femoral|n[óo]rdic|\bisquios?\b': 'Leg Curl',
        r'patada|kickback|abductor|add?uctores|aductor|add?ucci[óo]n|monster walk|band walk|gl[úu]teo|abd.*cadera|add.*cadera|add\b|drop p[ée]lvico|apertura cadera': 'Hip / Glute Isolation',
        r'gemelo|calf|ext.*tobillo|s[óo]leo|puntillas|supinaci[óo]n|pronaci[óo]n|supinadores|dorsilfexi[óo]n|tibial': 'Calf / Foot Isolation',
        r'press banca|pres.*banca|pb|chest press|flexion(?:es)?|push\s*up|\bpush\b|press.*inclinado|wall press|floorpress|pase.*pecho|\bpress\b': 'Horizontal Press (Pecho)',
        r'aperturas|flyes|cruce|posterior': 'Chest Fly / Posterior',
        r'press militar|press.*hombro|shpress|hspu|arnold|forntal|pulsos hombro|eleva.*frontal|pulsos rack': 'Vertical Press (Hombro)',
        r'elevaci[oó]n(?:es)?.*lat|p[áa]jaro|face\s*pull|rotaci[óo]n externa|rotadores|n[úu]meros hombro|n[úu]meros pared|rot.*interna|abd hombro|medialuna|c[ií]rculo.*hombro': 'Shoulder Isolation',
        r'tr[ií]ceps|franc[eé]s|extensi[óo]n codo|overhead|barbilla|\btri\b': 'Triceps Isolation',
        r'jal[óo]n|lat pulldown|dominada|pull up|chin up|pullover|nadador|colgad[oa]|aguantar colgada|tracci[óo]n|colgarse': 'Vertical Pull (Dorsal)',
        r'remo|row|trx': 'Horizontal Pull (Espalda)',
        r'curl|\bb[ií]ceps\b|\bbi\b|martillo': 'Biceps Isolation',
        r'fuerza agarre|farmer|granjero': 'Grip Strength',
        r'plancha|pancha|plank|core|abdomen|abdominal|rueda|ab wheel|pallof|le[ñn]ador|chop|deadbug|dead bug|bicho|ruso|russian|sit up|carretilla|sit through|toe to hand|toes to hand|superman|bird[- ]?dog|escaladores|toe taps|pike|v sit|hollow|tucks? up|tijeras|l sit|crunch|elevaci[oó]n.*piernas|elevas piernas|oblicua|twist|rodillas al pecho|\babd\b': 'Core Stability',
        r'serrato|wallslide|retracci[óo]n|esc[áa]pula|protra-retra': 'Serratus / Scapular',
        r'salto|saltando|jump|pogos|hacia delante|adelante|caj[óo]n|wallball|wall ball|medicinal|lanzar|lanzamiento|lanzo|saque|ca[íi]da|mono|basket|globo|comba|battle\s*rope|battlerope|batle\s*rope|intercambio pie': 'Plyometrics',
        r'oso|gorila|gorilla|animal|lagarto': 'Animal Flow',
        r'cinta|correr|corriendo|corre|carrera|caminar|caminas|remo.*m[áa]quina|bici|bike|airbike|skierg|\bski\b|trineo|burpee|jumping jacks|jjacks|metab[óo]lico|agilida|\bmax\b|kcalski|mountain climbers': 'Cardio / Metabólico',
        r'rotaci[óo]n|\brot\b|rot\.|gato|camello|movilidad|estiramiento|thoracic|torathic|extensi[oó]n tor[áa]cica|p[ée]lvica|cars|copenhague|open ?book|triple amenaza|deceleraci[óo]n|decelero|toque.*pie|manos a pie|toco hombro|flex|giros?|cross in front|90/90|punta.*pies|extender piernas|pecho a pared|kipping|pino|solo piernas|angelito|papada|espaldera|caballero|brindis|halo|cuadrupedia|abrir la puerta|volante|enrollar.*persiana|enrollamiento|acelero la moto|dragon sq|equilibrio|\by\b|diagonal|psoas|me siento.*tumbo|avi[óo]n|piernas cruzadas|codo arriba|extensi[óo]n.*columna': 'Mobility / Control'
    }
    for patron, categoria in reglas.items():
        if re.search(patron, nombre_limpio): return categoria
    return 'General / No Clasificado'

ciencia_anatomica = {
    'Olympic Weightlifting / Power': ('Cuerpo Completo', 'Cadena Posterior, Hombros', 'Potencia'),
    'Squat': ('Cuádriceps', 'Glúteos, Isquiosurales', 'Fuerza (Dominante Rodilla)'),
    'Lunge / Gait': ('Cuádriceps', 'Glúteos, Core', 'Fuerza / Desplazamiento'),
    'Leg Press': ('Cuádriceps', 'Glúteos', 'Fuerza (Máquina)'),
    'Leg Extension': ('Cuádriceps', 'Ninguno', 'Aislamiento'),
    'Hinge (Peso Muerto)': ('Isquiosurales', 'Glúteos, Lumbar', 'Fuerza (Dominante Cadera)'),
    'Glute Bridge': ('Glúteos', 'Isquiosurales', 'Fuerza (Cadera)'),
    'Leg Curl': ('Isquiosurales', 'Gemelos', 'Aislamiento'),
    'Hip / Glute Isolation': ('Glúteo Medio/Mayor', 'Aductores', 'Aislamiento'),
    'Calf / Foot Isolation': ('Sóleo / Gemelos', 'Tobillo', 'Aislamiento'),
    'Horizontal Press (Pecho)': ('Pectoral', 'Tríceps, Deltoides Anterior', 'Fuerza (Empuje)'),
    'Chest Fly / Posterior': ('Pectoral / Deltoides Posterior', 'Deltoides Anterior', 'Aislamiento'),
    'Vertical Pull (Dorsal)': ('Dorsal Ancho', 'Bíceps, Antebrazo', 'Fuerza (Tracción)'),
    'Horizontal Pull (Espalda)': ('Espalda Media (Romboides, Trapecio)', 'Dorsal, Bíceps', 'Fuerza (Tracción)'),
    'Vertical Press (Hombro)': ('Deltoides Anterior/Medio', 'Tríceps, Core', 'Fuerza (Empuje)'),
    'Shoulder Isolation': ('Deltoides (Medio/Posterior)', 'Manguito Rotador', 'Aislamiento'),
    'Biceps Isolation': ('Bíceps Braquial', 'Antebrazo', 'Aislamiento'),
    'Triceps Isolation': ('Tríceps Braquial', 'Ninguno', 'Aislamiento'),
    'Grip Strength': ('Antebrazo', 'Trapecio, Core', 'Estabilidad / Fuerza'),
    'Core Stability': ('Abdomen (Recto/Transverso)', 'Oblicuos, Lumbar', 'Estabilidad / Core'),
    'Animal Flow': ('Cuerpo Completo', 'Control Motor, Core', 'Control Dinámico'),
    'Serratus / Scapular': ('Serrato Anterior', 'Estabilizadores Escapulares', 'Activación'),
    'Plyometrics': ('Potencia Muscular', 'Sistema Nervioso', 'Pliometría'),
    'Cardio / Metabólico': ('Sistema Cardiovascular', 'Cuerpo Completo', 'Acondicionamiento'),
    'Mobility / Control': ('Articulaciones / Fascia', 'Control Motor', 'Movilidad / Control'),
    'Estructura / Basura': ('Ignorar', 'Ignorar', 'Ignorar'),
    'General / No Clasificado': ('General', 'General', 'General')
}

map_principal = {k: v[0] for k, v in ciencia_anatomica.items()}
map_secundario = {k: v[1] for k, v in ciencia_anatomica.items()}
map_tipo = {k: v[2] for k, v in ciencia_anatomica.items()}

todas_categorias = []

for col in cols_ejercicios:
    if 'limpio' in col or col == 'ej_1' or col == 'ejercicio_1':
        num = '1'
    else:
        numeros_encontrados = re.findall(r'\d+', col)
        num = numeros_encontrados[0] if numeros_encontrados else col
    
    col_cat = f'categoria_maestra_{num}'
    
    df_gym[col_cat] = df_gym[col].apply(clasificar_categoria_maestra)
    
    df_gym[f'musculo_principal_{num}'] = df_gym[col_cat].map(map_principal)
    df_gym[f'musculo_secundario_{num}'] = df_gym[col_cat].map(map_secundario)
    df_gym[f'tipo_ejercicio_{num}'] = df_gym[col_cat].map(map_tipo)
    
    df_validos_col = df_gym[df_gym[col_cat] != 'Estructura / Basura']
    todas_categorias.extend(df_validos_col[col_cat].tolist())

total_validos = len(todas_categorias)
total_exito = len([c for c in todas_categorias if c != 'General / No Clasificado'])

if total_validos > 0:
    exito = (total_exito / total_validos) * 100
    print(f"\n El {exito:.2f}% de los ejercicios han sido clasificados.")
else:
    print("\nNo se encontraron datos.")

if 'categoria_maestra_1' in df_gym.columns:
    df_final = df_gym[df_gym['categoria_maestra_1'] != 'Estructura / Basura'].copy()
else:
    df_final = df_gym.copy()

nombre_salida = 'dataset_IA_Anatomia_Compuestos.csv'
df_final.to_csv(nombre_salida, sep=';', index=False, encoding='utf-8-sig')
