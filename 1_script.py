import pandas as pd
import json
import re
import ast

# Ordenar el archivo final: 'sesion' o 'cliente'
ORDENAR_POR = 'sesion' 

def procesar_descripcion(descripcion):
    """
    Toma la cadena de texto de la sesión completa y repara errores de formato típicos del entrenador
    antes de separar el texto por líneas y asociarlas a un circuito.
    """

    # Separa ejercicios que el entrenador escribió en la misma línea separados por muchos espacios.
    # Ej: "Press banca 3x10   2) Dominadas" pasa a "Press banca 3x10\n2) Dominadas"
    descripcion = re.sub(r'\s{3,}(?=\d+[).]\s)', '\n', descripcion)
    
    # Evita que la palabra 'Recomendación' quede separada de los pesos (25-30) en la línea siguiente.
    # Ej: "Recomendación:\n25-30" pasa a "Recomendación: 25-30"
    descripcion = re.sub(r'(?i)(recomendaci[oó]n[:\s]*)\n\s*', r'\1 ', descripcion)

    # Corta la cabecera metabólica si el entrenador metió el ejercicio seguido en la misma línea.
    # Ej: "Circuito EMOM 10 min Sentadillas" -> "Circuito EMOM 10 min\nSentadillas"
    descripcion = re.sub(r'(?i)((?:circuito|bloque).*?(?:emom|amrap)\s*\d+\s*min(?:utos|s)?[\'"]?)\s+(?=[a-z])', r'\1\n', descripcion)
    
    # Repara líneas huerfanas.
    # Si la línea de abajo empieza por un modificador, la pega a la línea de arriba.
    # Ej: "Sentadilla\n15kg" -> "Sentadilla 15kg" | "Remo\nx brazo" -> "Remo x brazo"
    patrones_huerfanos = r'(?:x|por|cada)?\s*(?:lado|pierna|brazo)s?\b|(?:\+|-)?\s*\d+(?:[.,]\d+)?\s*(?:x|kg|kkg|”|"|\'|seg|min|reps|vuelta|vueltas)|\bminutos?\b|\bgoma\b|\bkcal\b|\bcalor[ií]as?\b|\biso\b|\bvueltas?\b'
    descripcion = re.sub(r'\n\s*(?=' + patrones_huerfanos + r')', ' ', descripcion, flags=re.IGNORECASE)
            
    # Cortamos el bloque por saltos de línea y limpiamos tabulaciones
    lineas = [linea.replace('\t', ' ').strip() for linea in descripcion.split('\n') if linea.strip()]
    ejercicios_procesados = []
    circuito_actual = "Sin circuito definido"
    
    for linea in lineas:
        # Detecta si la línea es un título de circuito.
        # Ej: "Circuito Fuerza:", "*Metcon 15 min*"
        if re.match(r'^[-*•·\s]*(circuito|cicuito|final|metab[óo]lico|fuerza|movilidad|activaci[óo]n|metcon|calentamiento|core|emom|amrap|abdomen|aer[oó]bico|cardio)\b', linea.lower()):
            circuito_actual = re.sub(r'^[-*•·\s]+', '', linea).strip(' :')
            
            # Si el entrenador metió el ejercicio en la misma línea del título después de los dos puntos
            # Ej: "Circuito Fuerza: Sentadilla 3x10" -> Extrae "Sentadilla 3x10"
            if ':' in linea:
                posible_ejercicio = linea.split(':', 1)[1].strip()
                # Descarta si a la derecha de los dos puntos solo hay un subtítulo aburrido
                # Ej: "Activación x 3 series"
                if not re.search(r'(?i)^(activaci[óo]n|fuerza|movilidad|core|calentamiento)\s*(?:x\s*\d+\s*(?:series|vueltas))?$', posible_ejercicio):
                    
                    # Descarta si la derecha es puramente un esquema de formato sin ejercicio.
                    # Ej: "21-15-9", "max 9 mins", "30-20-10"
                    es_solo_formato = re.match(r'(?i)^(?:emom|amrap|tabata|max|mins?|minutos?|met|metcon|metab[óo]lico|fuerza|fase|bloque|\d+|[x\s\-\.,_])+$', posible_ejercicio)

                    if not es_solo_formato:
                        # Si tiene números (ej: 15/30) y no es solo un "x 3 series", lo guardamos como ejercicio.
                        if re.search(r'\d', posible_ejercicio) and not re.match(r'(?i)^x\s*\d+\s*(?:series|vueltas)', posible_ejercicio):
                            ejercicios_procesados.append({
                                'circuito_perteneciente': circuito_actual,
                                'linea_texto': posible_ejercicio
                            })
        else:
            ejercicios_procesados.append({
                'circuito_perteneciente': circuito_actual,
                'linea_texto': linea
            })

    return ejercicios_procesados

def separar_metabolicos(fila):
    """
    Detecta si un circuito es de alta intensidad (AMRAP, EMOM, Metcon). Si lo es, 
    separa los ejercicios que han sido tecleados de forma seguida en la misma celda.
    """
    circuito_str = str(fila['circuito']).lower()
    
    # Detecta identificadores de circuitos por tiempo o rondas.
    # Ej: "Metabólico", "21-15-9", "For time"
    es_metab = bool(re.search(r'(?i)(metab|met\b|amrap|emom|aer[oó]bico|cardio|\d+(?:[-/]\d+)+|\bmax\s*\d|\bpor tiempo\b|\bfor time\b)', circuito_str))

    texto = str(fila['ejercicio_bruto'])
    
    if es_metab:
        # Inyecta un punto y coma separador donde el entrenador se comió la coma al listar ejercicios.
        # Ej: "bici 10 cal burpees 5" a "bici 10 cal; burpees 5"
        texto = re.sub(r'(?i)(bici|cinta|remo|ski|skierg|trx|swing|flexiones|burpees|box)\s+(?=\d+(?!\d)(?!\s*(?:k\b|kkg|kgs?|lbs|%|m\b|kms?|km/h|mins?|\'|\"|segs?|kcals?|cals?|pasillos?)))', r'\1; ', texto)
        
        # Convierte comas separadoras en punto y coma para facilitar el corte posterior.
        # Buscamos coma + espacio para no romper decimales. Ej: "Dominadas, Flexiones" a "Dominadas; Flexiones" (pero ignora "12,5 kg")
        texto = re.sub(r',\s+', '; ', texto)
        
        # Cortar cadena y limpia los huecos
        if ';' in texto:
            return [ejercicio.strip() for ejercicio in texto.split(';') if ejercicio.strip()]
            
    return [texto]

def arreglar_esquema_fecha(valor):
    """
    Evita que esquemas numéricos compuestos sean convertidos a fechas automáticamente por Excel.
    Ej: "21/15/9" a "Esquema 21-15-9" (Evita que ponga '21 de septiembre de 2015')
    """
    if pd.isnull(valor): return valor
    val_str = str(valor).lower().replace('/', '-').replace('\\', '-')
    
    # Limpieza de erratas por palabras duplicadas. Ej: "emom emom" -> "emom"
    palabras = val_str.split()
    if len(palabras) == 2 and palabras[0] == palabras[1]:
        val_str = palabras[0]
        
    if '-' in val_str:
        return f"Esquema {val_str}"
    return val_str

def analizar_ejercicio(texto):
    """
    Motor principal de extracción. Saca métricas (pesos, reps, material, gomas) del texto
    en bruto y luego aniquila todos los números para dejar solo el nombre limpio del ejercicio.
    """
    texto = str(texto).strip()
    
    # Aniquilar flechas decorativas usadas como viñetas. Ej: "Sentadilla -> 10kg" a "Sentadilla   10kg"
    texto = re.sub(r'[➔→⇒▶]|->|=>|-->', ' ', texto) 
    
    # Borra el número de lista al principio de la línea antes de proteger los ejercicios numéricos. 
    # Ej: "1) Press", "2. Remo", "3a) Curl" a "Press", "Remo", "Curl"
    texto = re.sub(r'^\s*\d+[a-zA-Z]?\s*[-).]\s*', '', texto)
    
    # proteger el estiramiento 90/90 y evitar que se confunda con repeticiones o porcentajes.
    # Ej: "Estiramiento 90/90" pasa a "Estiramiento noventa_noventa"
    texto = re.sub(r'(?i)(?<!\d)90/90(?!\d)', 'noventa_noventa', texto) 
    
    # Destruir restos de cabeceras metabólicas incrustadas para que sus números no entorpezcan.
    # Ej: "AMRAP en 10 min de Sentadilla" -> " Sentadilla"
    texto = re.sub(r'(?i)\b(?:m[áa]ximas?\s*rondas?|max\s*rondas?|amrap|emom|tc|time cap|por tiempo|for time)\b\s*(?:en\s*)?\d*(?:[.,]\d+)?\s*(?:mins?|minutos?|\'|”|"|’|´)?\s*(?:de\s*)?', '', texto)

    # Normalización de caracteres especiales y erratas comunes.
    texto = texto.replace('¸', ',')
    
    # Separa la preposición 'a' si está pegada a un número. Ej: "banco a45" a "banco a 45"
    texto = re.sub(r'(?i)\ba(?=\d)', 'a ', texto) 
    
    # Guiones tipográficos largos (Word) a guion simple de programación
    texto = re.sub(r'[–—−]', '-', texto) 
    
    # Unifica rangos con espacios rotos para que se capturen bien. Ej: "10 - 12 reps" a "10-12 reps"
    texto = re.sub(r'(?<=\d)\s+-\s*(?=\d)', '-', texto) 

    # Despega los símbolos de mayor y menor. Ej: ">10" a "> 10"
    texto = re.sub(r'(?<=\d)(?=[<>])|(?<=[<>])(?=\d)', ' ', texto)
    
    texto_original = str(texto)
    
    # Despega letras y números pegados accidentalmente. Ej: "adelante1" a "adelante 1", "Swings12" a "Swings 12"
    texto = re.sub(r'(?<=[a-zA-ZáéíóúÁÉÍÓÚñÑ])(?=\d)(?<![xX])', ' ', texto)

    # Despega números de letras respetando el punto decimal. Ej: "2.5k" a "2.5 k"
    texto = re.sub(r'(?<=\d)(?=[a-zA-ZáéíóúÁÉÍÓÚñÑ])(?<!x)(?<!X)', ' ', texto)

    # Separa el peso o unidad de las repeticiones. Ej: "20kgx10" a "20 kg x 10"
    texto = re.sub(r'(?i)(kg|k|kgs|kkg|lbs|cms|cm)\s*x\s*(\d)', r'\1 x \2', texto)

    # Repaso extra de letras y números
    texto = re.sub(r'(?<=[a-zA-ZáéíóúÁÉÍÓÚñÑ])(?=\d)', ' ', texto)
    texto = re.sub(r'(?i)(kg|k|kgs|kkg|cms|cm)x(\d)', r'\1 x \2', texto)

    # Erratas hiper-específicas
    texto = texto.replace('tumbad0', 'tumbado')

    # Protege abreviaturas musculares traduciéndolas para que no se borren por error en filtros de limpieza.
    # Ej: "curl bi" a "Curl bíceps", "bi y tr" a "bíceps y tríceps"
    texto = re.sub(r'(?i)\bcurl\s+bi\b', 'Curl bíceps', texto)
    texto = re.sub(r'(?i)\bbi\s+(?:y|/|-|o)\s+tr\b', 'bíceps y tríceps', texto)
    texto = re.sub(r'(?i)\btr\s+(?:y|/|-|o)\s+bi\b', 'tríceps y bíceps', texto)
    texto = re.sub(r'(?i)\bpolea\s+bi\b', 'Polea bíceps', texto)

    # Borra modificadores de lateralidad si actúan como mecánicos (no son parte del nombre). 
    # Ej: "iso uni" -> "iso"
    texto = re.sub(r'(?i)\b(?:bi|uni)\s*(?:/|-|y|o|\+)?\s*(?=exc|iso|isometr[ií]a|isom[eé]tric[oa]s?|exc[eé]ntric[oa]s?)\b', '', texto)
    texto = re.sub(r'(?i)(exc|iso|isometr[ií]a|isom[eé]tric[oa]s?|exc[eé]ntric[oa]s?)\s*(?:/|-|y|o|\+)?\s*(?:bi|uni)\b', r'\1', texto)
    texto = re.sub(r'(?i)\bbi\s*(?:/|-|y|o)\s*uni\b', '', texto)
    texto = re.sub(r'(?i)\buni\s*(?:/|-|y|o)\s*bi\b', '', texto)

    # Estandariza mancuernas para la detección de material. Ej: "press mc" -> "press mancuernas"
    texto = re.sub(r'(?i)\bmcs?\b', 'mancuernas', texto)

    # Repartidor dinámico de pesos: dviide una carga total entre las series solicitadas.
    # Ej: "30 kg a repartir entre 3 series" a "10 kg x 3 series"
    def aplicar_division(match):
        cantidad = float(match.group(1).replace(',', '.'))
        texto_intermedio = match.group(2)
        series = int(match.group(3))
        if series > 0:
            resultado = cantidad / series
            if resultado.is_integer():
                resultado_str = str(int(resultado))
            else:
                resultado_str = str(round(resultado, 2)).replace('.', ',')
            return f"{resultado_str} {texto_intermedio} x {series} series"
        return match.group(0)

    texto = re.sub(r'(?i)\b(\d+(?:[.,]\d+)?)\s+([a-zA-Z\s]+?)\s*(?:a\s*repartir\s*)?(?:entre|en)\s*(?:las\s*)?(\d+)\s*series?\b', aplicar_division, texto)

    # Cambia punto y coma por separador de ejercicios "|" si va antes de un número de lista.
    # Ej: "1) Ejercicio A; 2) Ejercicio B" -> "1) Ejercicio A | 2) Ejercicio B"
    texto = re.sub(r'(?i)[;,]\s*(?=\d+\))', ' | ', texto)
    
    # Unificación de comillas
    texto = re.sub(r'[`´’]', "'", texto)
    texto = re.sub(r'[¿?]', '', texto) 
    texto = re.sub(r"''", '"', texto) # Ej: "1'20''" -> "1'20\""
    
    # Destructor de signos huérfanos
    texto = re.sub(r'"{2,}', '', texto) 
    texto = re.sub(r'^["\']+', '', texto)
    
    # Destructor de barras múltiples. Ej: "10//12" -> "10/12"
    texto = re.sub(r'/{2,}', '/', texto) 
    texto = re.sub(r'^[\s/]+', '', texto)

    # Convierte 'vs' en '+' para que el script lo considere una superserie. Ej: "Press vs Remo" -> "Press + Remo"
    texto = re.sub(r'(?i)\bvs\b', '+', texto)

    # Gira la palabra nivel o resistencia para facilitar su extracción (Número siempre delante).
    # Ej: "bici nivel 5", "a resistencia 16" -> "bici 5 resistencia", "16 resistencia"
    texto = re.sub(r'(?i)\b(?:a\s*)?(?:resistencia|nivel|lvl)\s*(\d+(?:[.,]\d+)?)', r'\1 resistencia', texto)

    # Aniquila totales de cardio previos a un desglose fraccionado para que no se extraigan dos veces.
    # Ej: "16 calorías: 5 fuertes, 11 suaves" -> "calorías: 5 fuertes, 11 suaves"
    texto = re.sub(r'(?i)\b\d+(?:[.,]\d+)?\s*(?=(?:calor[ií]as?|kcals?|cals?|metros?|m\b|kms?|mins?|minutos?|segs?|segundos?|pasillos?|vueltas?)[\s:,\(-]*\d+\s*(?:fuertes?|suaves?|medias?|medios?|moderadas?|moderados?|ligeras?|ligeros?|sprint|a\s*tope))', '', texto)

    # Destruye fórmulas matemáticas de progresión y notas de ritmo. 
    # Ej: "S2 = S1 + 10 reps" o "cada ronda en 1.5 mins" -> ""
    texto = re.sub(r'(?i)[.,;]?\s*\bS\s*\d+\s*=\s*S\s*\d+\s*[+-]\s*\d+\s*(?:cals?|kcals?|calor[ií]as?|reps?|kg|k|m\b|metros?|kms?|km/h)?\b', '', texto)
    texto = re.sub(r'(?i)\(?\bcada\s+ronda\s+en\s*\d+(?:[.,]\d+)?\s*(?:\'|”|"|mins?|minutos?|segs?|segundos?)\)?', '', texto)
    texto = re.sub(r'(?i)\bmax\s+(?:cals?|kcals?|calor[ií]as?|reps?|metros|m\b|distancia)\b', '', texto)

    # Traductor de tiempo compuesto (minutos y segundos a solo segundos).
    # Ej: "1'20\"" -> "80\""
    def min_seg_a_segundos(match):
        mins = int(match.group(1))
        segs = int(match.group(2))
        return f'{mins * 60 + segs}"'
    
    texto = re.sub(r'(?i)\b(\d+)\s*(?:\'|’|´|mins?|minutos?)\s*(\d+)\s*(?:"|”|segs?|segundos?)', min_seg_a_segundos, texto)

    # Protege fracciones y ejercicios clave para que no se partan.
    # Ej: "1/2 sentadilla" -> "medio_ejercicio sentadilla"
    texto = re.sub(r'\b1/2\b', 'medio_ejercicio', texto)
    texto = re.sub(r'(?i)\bstep\s*ups?\b', 'step_up', texto) 
    texto = re.sub(r'(?i)\b1\s*reps?\s*=\s*', '', texto)

    # Transforma '+' en 'con' si le sigue un peso o material. Esto evita que parta el ejercicio en dos.
    # Ej: "Zancada + 10kg" -> "Zancada con 10kg"
    texto = re.sub(r'(?i)\s*\+\s*(?=\d*(?:[.,]\d+)?\s*(?:kg|k|kkg|lbs|mc|mancuerna|barra|disco|kb|trx))', ' con ', texto)
    
    # Limpieza de viñetas residuales
    texto = re.sub(r'^[\s•·\-*…]+', '', texto)
    texto = re.sub(r'^\s*\d+[\)]\s*', '', texto)
    texto = re.sub(r'^\s*\d+\.\s+', '', texto)
    texto = re.sub(r'^\s*\d+-\s+', '', texto)
    
    # Protección de unidades y porcentajes
    texto = re.sub(r'\b(\d+)\s*(?:cm|cms)\b', r'\1cm', texto, flags=re.IGNORECASE)
    
    # Asigna centímetros a las alturas de cajón. Ej: "Salto cajón 60" -> "Salto cajón 60cm"
    texto = re.sub(r'(?i)\b(saltos?|caj[oó]n|box)\s*(?:a|de)?\s*(\d{2,3})\b(?!\s*(?:k\b|kkg|kgs?|kg|lbs|%|x|reps?|mins?|segs?))', r'\1 \2cm', texto)

    # Unifica nombres de saltos. Ej: "saltos al cajón", "salto en box" -> "Salto cajón"
    texto = re.sub(r'(?i)\bsaltos?\s+(?:a|al|de|en)?\s*(?:caj[oó]n|box|vertical|altura|vallas?)\b', 'Salto cajón', texto)
    texto = re.sub(r'(?i)\bsaltos?\s+(?:longitudinal(?:es)?|de\s+longitud|horizontal(?:es)?|hacia\s+delante|frente)\b', 'Salto longitudinal', texto)
    
    # Estandariza métricas de distancia. Ej: "5 idas y vueltas" -> "5 idas_y_vueltas"
    texto = re.sub(r'(?i)(\d+)\s*idas?\s*y\s*(?:\d+\s*)?vueltas?\b', r'\1 idas_y_vueltas', texto)
    texto = re.sub(r'(?i)\b(?:x\s*)?x?idas?\s*y\s*vueltas?\b', ' idas_y_vueltas', texto)
    
    # Protege los porcentajes para que no se borren en limpiezas futuras. Ej: "80 a 90 %" -> "PCT80 a PCT90_porc"
    texto = re.sub(r'(?i)\b(\d+)\s*a\s*(\d+)\s*%', r'PCT\1 a PCT\2_porc', texto)
    texto = re.sub(r'(?i)\b(\d+(?:-\d+)*)\s*%', r'PCT\1_porc', texto)

    # Protege anatomía del borrado numérico. Ej: "1 pierna" -> "una pierna"
    texto = re.sub(r'(?i)\b1\s*(pierna|brazo|mano|apoyo)\b', r'una \1', texto)
    texto = re.sub(r'(?i)\b(\d+)\s+jumping\b', r'\1 reps jumping', texto)
    texto = re.sub(r'(?i)\(\s*x\s*(\d+)\)', r'\1 series', texto)
    
    # Une material y peso tragándose la 'k' original para no duplicar en las columnas.
    # Ej: "mc 5", "disco de 5" -> "mc 5kg ", "disco 5kg "
    texto = re.sub(r'(?i)(kb|kbs|ktbs?|kts?|kettlebells?|mc|mancuernas?|db|dumbbells?|barras?|discos?)\s*(?:de\s*)?(\d+(?:[.,]\d+)?)\s*(?:k\b|kkg|kgs?|kg|lbs)?', r'\1 \2kg ', texto)
    texto = re.sub(r'(?i)\b2\s*(kb|ktbs?|kbs|kettlebells?|mc|mancuernas?|db|dumbbells?)\b', r'Doble \1', texto)
    texto = re.sub(r'(?i)\b1\s*(kb|ktbs?|kbs|kettlebells?|mc|mancuernas?|db|dumbbells?)\b', r'Una \1', texto)
    
    # Estandariza ángulos de banco. Ej: "banco a 45" -> "banco 45º"
    texto = re.sub(r'(?i)\bbanco\s+a\s+(\d+)\b', r'banco \1º', texto)
    
    # Repartidor de superseries abreviadas. Ej: "Y + T 8 de cada" -> "Y 8 reps + T 8 reps"
    def distribuir_de_cada(match):
        cadena = match.group(1)
        num = match.group(2)
        partes = cadena.split('+')
        if len(partes) > 1:
            return " + ".join([p + f" {num} reps" for p in partes])
        return f"{cadena} {num} reps"

    texto = re.sub(r'(?i)([^;.,|~]*?)\s*\b(\d+)\s+de\s+cada\b', distribuir_de_cada, texto)
    texto = re.sub(r'(?i)\bde\s+cada\b', '', texto)

    rir_val = None
    
    # Escudo anti-colisión para RIR en formato rango. 
    # Ej: "10-8-6rir 2-2-1" -> Atrapa "2-2-1" como RIR y deja "10-8-6" para repeticiones.
    m_rir_completo = re.search(r'(?i)(?<!\d)(\d+(?:-\d+)*)\s*(?:rir|rpe)\s*(\d+(?:-\d+)*)', texto)

    if m_rir_completo:
        rir_val = m_rir_completo.group(2) 
        texto = texto.replace(m_rir_completo.group(0), m_rir_completo.group(1))
    else:
        # RIR colocado después del peso/reps (Se asegura de no capturar kilos). 
        # Ej: "Sentadilla 3x10 RIR 2" -> Atrapa "2".
        m_rir_despues = re.search(r'(?i)(?:rir|rpe|@)\s*(\d+(?:-\d+)*)\b(?!\s*(?:k\b|kkg|kgs?|kg|lbs|%))', texto)

        # RIR colocado delante de las reps. 
        # Ej: "2 RIR 10 reps" -> Atrapa "2".
        m_rir_antes = re.search(r'(?i)(?<![\d\-])(?<![xX])(?<![xX]\s)(\d+(?:-\d+)*)\b\s*(?:rir|rpe)\b', texto)

        if m_rir_despues:
            rir_val = m_rir_despues.group(1)
            texto = re.sub(r'(?i)(?:rir|rpe|@)\s*' + re.escape(rir_val), ' ', texto)
        elif m_rir_antes:
            rir_val = m_rir_antes.group(1)
            texto = re.sub(r'(?i)' + re.escape(rir_val) + r'\s*(?:rir|rpe)\b', ' ', texto)

    # Destruye tempos complejos de forma segura para que no se confundan con repeticiones.
    # Ej: "tempo 3-1-1-0" -> ""
    texto = re.sub(r'(?i)\btempo\s*\d+(?:-\d+){2,3}\b', '', texto)
    texto = re.sub(r'(?i)(?<![.,\d])\d(?:-\d){2,3}(?![.,\d])\b', '', texto)

    # Estandariza estructuras de bloques y series. Ej: "Fuerza 3 x 10 series" -> "Fuerza 3 series 10"
    texto = re.sub(r'(?i)\b(Fuerza|Circuito|Bloque)\s+(\d+)\s*x\s*(\d+)\s*series?\b', r'\1 \2 series \3', texto)
    
    # Evita confundir la variable reps con las series. Ej: "x6 serie" no es lo mismo que "6 series"
    texto = re.sub(r'(?i)(?<!x\s)(?<!x)\b(\d+)\s*series?\b', r'series \1', texto)
    texto = re.sub(r'(?i)\bsolo\s+piernas?\b', 'TRENINFERIOR', texto)
    texto = re.sub(r'(?i)\bsolo\s+brazos?\b', 'TRENSUPERIOR', texto)
    texto = re.sub(r'(?i)\(\s*stops?\s*\d+(?:-\d+)*\s*\)', '', texto)
    texto = re.sub(r'(?i)(?:[-+])\s*(\d+)\s*(?:º|°|grados?)(?!\w)', r' \1º', texto)
    
    # Convierte números sueltos en ángulos si coinciden con inclinaciones típicas. Ej: "en 45" -> " 45º"
    texto = re.sub(r'(?i)(?:\+|\ba\b|\ben\b)\s*(15|30|45|60|75|90)(?!\s*(?:kg|k|kkg|lbs|cm|m|s|seg|min|%|x|\'))\b', r' \1º', texto)

    # Corrige erratas de peso que el entrenador escribió con el cero delante por teclear rápido.
    # Ej: "08 x 10" -> "80 x 10" (El entrenador quiso poner 80kg, no 8kg)
    texto = re.sub(r'\b0([1-9])(?=\s*x\b)', r'\g<1>0', texto, flags=re.IGNORECASE)
    
    texto = texto.replace('minsa', 'mins a')
    texto = re.sub(r'(?i)^(?:aer[oó]bico\s*(?:cl)?|cardio)[^:]*:\s*', '', texto)
    texto = re.sub(r'(?i)^(?:aer[oó]bico\s*(?:cl)?|cardio)\s*[.-]?\s*', '', texto)
    
    # Despega distancias si están unidas a la máquina de cardio. Ej: "500remo" -> "500 remo"
    texto = re.sub(r'(?i)(\d+)(cinta|remo|ski|skierg|bici|bike|airbike|el[ií]ptica|correr|andar)', r'\1 \2', texto)
    
    # Reordena unidades de cardio para una extracción precisa. Ej: "kcal remo 50" -> "remo 50 kcal"
    texto = re.sub(r'(?i)\b(kcal|calor[ií]as?|cals?|metros?|kms?)\s+(cinta|remo|ski|skierg|bici|bike|airbike|el[ií]ptica)\s*(\d+(?:[.,]\d+)?)', r'\2 \3 \1', texto)
    texto = re.sub(r'\b0([1-9])\b', r'\g<1>0', texto)
    texto = re.sub(r'[()]', ' ', texto)

    # Identifica si es un ejercicio unilateral
    por_lado = bool(re.search(r'(?i)(?:x|por|cada|/)\s*(?:lado|lad0|lad|pierna|brazo)s?|\bunilateral\b|\buni\b', texto))
    global_multiplier = 1

    texto = re.sub(r'^\s*\d+\s*[).]\s*', '', texto)
    
    # Usa la virgulilla ~ para agrupar diferentes rondas, dropsets o descensos de peso de un mismo ejercicio.
    # Ej: "Press 10kg. Serie 2 12kg" -> "Press 10kg ~ Serie 2 12kg"
    texto = re.sub(r'[-.,;]*\s*(?=(?:\b(?:Serie|series?)\b\s*\d|\bS\s*\d|\bS\d))', ' ~ ', texto, flags=re.IGNORECASE)
    texto = re.sub(r'(?<=[a-zA-Z])\.\s*(?=\d+(?:[.,]\d+)?\s*(?:x|kg|kkg))', ' ~ ', texto, flags=re.IGNORECASE)    
    
    # Regla: No cortar si detectamos material, kilos, libras, minutos tras un '+'. 
    regla_no_cortar = r'(?:(?:\d+(?:[.,]\d+)?\s*(?:kg|k|kkg|kgs)?\s*|Doble\s+|Una\s+)?(?:kb|kbs|ktbs?|kettlebells?|mc|mancuernas?|db|dumbbells?|discos?|gomas?|bandas?|picas?|barras?|pesos?|chalecos?|lastres?)\b)|(?:\d+(?:[.,]\d+)?\s*(?:kg|k|kkg|kgs|lbs|%|cm|m|seg|s|min)\b)|(?:\d+(?:[.,]\d+)?\s*(?:$|[,;.]|\bpasillos?\b))'

    # Protege superseries que son movimientos integrados. Ej: "Zancada + salto" -> "Zancada con salto"
    texto = re.sub(r'(?i)\s*\+\s*(pasos?|saltos?|isom[eé]trico|iso|caminata|desplazamiento|rotaci[óo]n|remos?|c[ií]rculos?)\b', r' con \1', texto)
    texto = re.sub(r'(?i)\s*\+\s*(?=\d*(?:[.,]\d+)?\s*(?:kg|k|kkg|lbs|mc|mancuerna|barra|disco|kb|trx))', ' con ', texto)
    texto = re.sub(rf'(?i)\s*\+\s*(?={regla_no_cortar})', ' con ', texto)
    
    # Si el '+' no va seguido de material o un modificador válido, asume que es otro ejercicio y lo separa.
    # Ej: "Sentadilla + Press" -> "Sentadilla | Press"
    texto = re.sub(rf'(?i)\s*\+\s*(?!{regla_no_cortar})', ' | ', texto)
    
    # Si el punto y coma está entre números, es una serie (dropset), no un ejercicio nuevo.
    # Ej: "10;12;15" -> "10 ~ 12 ~ 15"
    texto = re.sub(r'(?<=\d)\s*;\s*(?=\d)', ' ~ ', texto)

    texto = re.sub(r'(?i)[;,]\s*(?=\d+[\)\.-]\s*[a-zA-Z])', ' | ', texto)

    texto = re.sub(r'(?<=\d)\s*;\s*(?=\d)', ' ~ ', texto)

    # Si después del punto y coma solo hay material o reps, hereda el nombre del ejercicio previo (es serie).
    # Ej: "Press banca; con mc" -> "Press banca ~ con mc"
    texto = re.sub(r';\s*(?=(?:barra|mc|mancuerna|disco|kb|kettlebell|x\s*\d|serie|s\d))(?![^;]*?(?:press|remo|sentadilla|curl|extensi[óo]n|elevaci[óo]n))', ' ~ ', texto, flags=re.IGNORECASE)

    texto = texto.replace(';', ' | ')

    # Cortafuegos de Cardio: Fuerza separación en columnas si detecta máquinas tras el signo de puntuación.
    # Ej: "Burpees; remo 500m" -> "Burpees | remo 500m"
    texto = re.sub(r'(?i)(?:;|(?<!\d),(?!\d))\s*(?=[^;\|]*?(?:cinta|remo|ski|skierg|bici|bike|airbike|el[ií]ptica|correr|andar)\b)', ' | ', texto)
    
    # Cortafuegos de Guiones: Separa si el entrenador usó un guion antes de palabras clave que inician otro ejercicio.
    # Ej: "Press - burpees" -> "Press | burpees"
    texto = re.sub(r'(?i)\s*[-–]\s*(?=(?:pasillos?|corriendo|carrera|burpees|cinta|remo|ski|skierg|bici|bike|el[ií]ptica|correr|andar|swings?|saltos?|flexiones|dominadas|zancadas?|trineo|wall?l?balls?|walballs?|bal[oó]n(?:es)?|step_up)\b)', ' | ', texto)

    texto = re.sub(rf'(?i)\s*\+\s*(?!{regla_no_cortar})', ' | ', texto)
    
    ejercicios_compuestos = texto.split('|')
        
    pesos_globales = []
    reps_globales = []
    isos_globales = []
    equipos_globales = []
    espaciales_globales = [] # Alturas y Ángulos
    mecanicos_globales = []  # Saltos, Isométricos, etc.
    gomas_globales = []
    cants_globales = [] 
    tipos_globales = [] 
    intensidades_globales = []

    for ej in ejercicios_compuestos:
        matches_unidades = []
        
        # Atrapa distancias huérfanas y asume que es carrera.
        patron_fantasma = r"""(?i)(\d+(?:[.,]\d+)?\s*(?:mins?|minutos?|segs?|segundos?|"|'')\s*(?:a|@)\s*\d+|kms?\b|km/h)"""
        if re.search(patron_fantasma, ej) and not re.search(r'(?i)(cinta|correr|bici|bike|remo|el[ií]ptica|skierg|aer[oó]bico|caminar|andar)', ej):
            ej = "Cinta " + ej.replace('(', '').replace(')', '')

        # Extrae telemetría (Tiempo + Velocidad). Ej: "10 mins a 12 km/h"
        patron_telemetria = r"""(?i)(\d+(?:[.,]\d+)?)\s*("|''|'|mins?|minutos?|segs?|segundos?)\s*(?:(?:cinta|remo|bici|bike|skierg|el[ií]ptica|correr|andar)\s*)?(?:a|@)\s*(\d+(?:[.,]\d+)?)(?:\s*km/?h)?"""
        for match_tel in re.finditer(patron_telemetria, ej):
            tiempo_val = match_tel.group(1).replace(',', '.')
            unidad_tiempo_raw = match_tel.group(2).lower()
            velocidad_val = match_tel.group(3).replace(',', '.')
            unidad_tiempo = "segundos" if '"' in unidad_tiempo_raw or "seg" in unidad_tiempo_raw or "''" in unidad_tiempo_raw else "minutos"
            matches_unidades.append((tiempo_val, unidad_tiempo))
            matches_unidades.append((velocidad_val, "km/h"))
            
        ej = re.sub(patron_telemetria, '', ej, flags=re.IGNORECASE)

        # Extractor general de unidades de cardio
        patron_unidades = r'(?i)(?<![\d.,])((?:[<>]?\s*)?\d+(?:[.,]\d+)?(?:[/-]\d+(?:[.,]\d+)?)*)[\s\-]*(pasillos?|calor[ií]as?|kcals?|cals?|mins?|minutos?|segs?|segundos?|km/?h|kms?|metros?|m\b|vueltas?|resistencia|niveles?|watts?|w\b|["\'”’]|a\s*tope|suaves?|medias?|medios?|moderadas?|moderados?|fuertes?|ligeras?|ligeros?|sprint)(?!\s*(?:iso|exc\b))'

        for m_uni in re.finditer(patron_unidades, ej):
            texto_original_match = m_uni.group(0)
            cant = m_uni.group(1).replace(',', '.').strip() 
            tipo = m_uni.group(2).lower()

            if tipo in ['"', '”', "''"]: tipo = "segundos"
            elif tipo in ["'", '’']: tipo = "minutos"

            if tipo in ["segundos", "segs", "seg", "minutos", "mins", "min"] and re.search(r'(?i)\b(?:iso|exc)\b', ej):
                continue

            es_intensidad = bool(re.match(r'(?i)^(a\s*tope|suaves?|medias?|medios?|moderadas?|moderados?|fuertes?|ligeras?|ligeros?|sprint)$', tipo))
            if es_intensidad:
                if matches_unidades:
                    tipo_real = matches_unidades[-1][1]
                elif re.search(r'(?i)calor[ií]as?|kcals?|cals?', ej):
                    tipo_real = 'kcal'
                elif re.search(r'(?i)metros?|\bm\b', ej):
                    tipo_real = 'm'
                else:
                    tipo_real = "uds"
                matches_unidades.append((cant, tipo_real))
                ej = ej.replace(texto_original_match, f' {tipo} ') 
            else:
                matches_unidades.append((cant, tipo))
                ej = ej.replace(texto_original_match, ' ')

        cants_globales.append([str(x[0]).replace(',', '.') for x in matches_unidades])
        tipos_globales.append([str(x[1]) for x in matches_unidades])
        
        # Extrae modificadores de intensidad pura (cualitativa)
        patron_intensidad = r'(?i)\b(a\s*tope|suaves?|medias?|medios?|moderadas?|moderados?|fuertes?|ligeras?|ligeros?|sprint|ritmo(?:s)?|r[áa]pid[oa]s?)\b'
        matches_int = re.findall(patron_intensidad, ej)
        intensidades_globales.append([m.lower() for m in matches_int])

        ej = re.sub(patron_intensidad, '', ej)

        partes = [p.strip() for p in ej.split('~') if p.strip()]
        pesos = []
        reps = []
        isos = []
        gomas = []
        equipos = []
        espaciales = [] 
        mecanicos = []  

        for parte in partes:
            goma_val = None

            # Escudo de cajones: Unir el color al cajón con un guion bajo para que las gomas no se lo roben en la regex de colores.
            # Ej: "Cajón rojo" -> "Cajón_rojo"
            parte = re.sub(r'(?i)\b(caj[oó]n(?:es)?|box)\s+(roj[oa]s?|negr[oa]s?|verd[eo]s?|amarill[oa]s?|azules?|azuls?|blanc[oa]s?)\b', r'\1_\2', parte)
            
            if re.search(r'(?i)sin\s+(?:goma|banda|material)', parte):
                goma_val = "Sin goma"
                parte = re.sub(r'(?i)sin\s+(?:goma|banda|material)', '', parte)
                
            # Extrae el color de las bandas elásticas cubriendo decenas de erratas tipográficas comunes.
            patron_material = r'(?i)\b(goma|banda|slide)s?(?:\s+(roj[oa]s?|rojaa|orjas?|turquesas?|negr[oa]s?|ngeras?|nergas?|negrs?|amarill[oa]s?|amrillas?|morad[oa]s?|verd[eo]s?|azules?|azuls?|gris(?:es)?|blanc[oa]s?))\b|(?<![a-z])\b(roj[oa]s?|rojaa|orjas?|turquesas?|negr[oa]s?|ngeras?|nergas?|negrs?|amarill[oa]s?|amrillas?|morad[oa]s?|verd[eo]s?|azules?|azuls?|gris(?:es)?|blanc[oa]s?)\b'
            m_mat = re.search(patron_material, parte)
            
            if m_mat and not goma_val:
                tipo = m_mat.group(1).lower() if m_mat.group(1) else "goma"
                color_raw = m_mat.group(2) or m_mat.group(3) or ""
                color_raw = color_raw.lower().strip() 
                
                # Normalización limpia
                if re.match(r'roj[oa][as]?|orjas?', color_raw): color = 'roja'
                elif re.match(r'turquesas?', color_raw): color = 'turquesa'
                elif re.match(r'negr[oa]s?|ngeras?|nergas?|negrs?', color_raw): color = 'negra'
                elif re.match(r'amarill[oa]s?|amrillas?', color_raw): color = 'amarilla'
                elif re.match(r'morad[oa]s?', color_raw): color = 'morada'
                elif re.match(r'verd[eo]s?', color_raw): color = 'verde'
                elif re.match(r'azules?|azuls?', color_raw): color = 'azul'
                elif re.match(r'gris(?:es)?', color_raw): color = 'gris'
                elif re.match(r'blanc[oa]s?', color_raw): color = 'blanca'
                else: color = color_raw

                goma_val = f"{tipo.capitalize()} {color}".strip()
                parte = re.sub(patron_material, '', parte, flags=re.IGNORECASE)

            equipo_val = None
            patron_equipamiento = r'(?i)\b(mancuernas?|mancuenras?|macuernas?|mc|db|dumbbells?|kettlebells?|kb|kbs|ktbs?|kts?|barras?(?:\s*z)?|barraz|bbarras?|discos?|trx|picas?|chalecos?|lastres?|wall?l?balls?|walballs?|bal[oó]n(?:es)?|poleas?(?:\s+(?:alta|baja|media)s?)?|ploaes?|polaes?|poleras?|steps?|caj[oó]n(?:es)?(?:_(?:roj[oa]s?|negr[oa]s?|verd[eo]s?|amarill[oa]s?|azules?|azuls?|blanc[oa]s?))?|box)\b'
            m_equipo = re.search(patron_equipamiento, parte)

            if m_equipo:
                equipo_crudo = m_equipo.group(1).lower()
                if re.match(r'mancuernas?|mancuenras?|macuernas?|mc|db|dumbbells?', equipo_crudo): equipo_val = "Mancuernas"
                elif re.match(r'kettlebells?|kb|kbs|ktbs?|kts?', equipo_crudo): equipo_val = "Kettlebell"
                elif re.match(r'barras?(?:\s*z)?|barraz|bbarras?', equipo_crudo): equipo_val = "Barra Z" if "z" in equipo_crudo else "Barra"
                elif re.match(r'discos?', equipo_crudo): equipo_val = "Disco"
                elif re.match(r'trx', equipo_crudo): equipo_val = "TRX"
                elif re.match(r'picas?', equipo_crudo): equipo_val = "Pica"
                elif re.match(r'chalecos?|lastres?', equipo_crudo): equipo_val = "Lastre"
                elif re.match(r'wallballs?|walballs?|bal[oó]n(?:es)?', equipo_crudo): equipo_val = "Wallball"
                elif re.match(r'poleas?(?:\s+(?:alta|baja|media)s?)?|ploaes?|polaes?|poleras?', equipo_crudo): 
                    if 'alta' in equipo_crudo: equipo_val = "Polea alta"
                    elif 'baja' in equipo_crudo: equipo_val = "Polea baja"
                    elif 'media' in equipo_crudo: equipo_val = "Polea media"
                    else: equipo_val = "Polea"
                elif re.match(r'steps?', equipo_crudo): equipo_val = "Step"
                elif re.match(r'caj[oó]n(?:es)?(?:_.*)?|box', equipo_crudo): equipo_val = equipo_crudo.replace('_', ' ').capitalize()
                else: equipo_val = equipo_crudo.capitalize()

            # Saca el modificador y lo borra para que no confunda a los pesos. Ej: "Salto 60cm" -> Extrae "60cm"
            espacial_val = None
            patron_espacial = r'(?i)\b(\d+)\s*(?:cms|cm|º|grados?)'
            m_espacial = re.search(patron_espacial, parte)
            if m_espacial:
                espacial_val = m_espacial.group(0).lower().replace('grados', 'º').replace('grado', 'º').replace(' ', '')
                parte = re.sub(patron_espacial, '', parte, flags=re.IGNORECASE)

            mecanico_val = None
            patron_mecanico = r'(?i)\b(?:con\s*)?(saltos?|isometr[ií]a|isom[eé]tric[oa]s?|iso|exc[eé]ntric[oa]s?|exc)\b'
            m_mecanico = re.search(patron_mecanico, parte)
            if m_mecanico:
                mec_crudo = m_mecanico.group(1).lower()
                if re.match(r'isometr[ií]a|isom[eé]tric[oa]s?|iso', mec_crudo): mecanico_val = "Isométrico"
                elif re.match(r'exc[eé]ntric[oa]s?|exc', mec_crudo): mecanico_val = "Excéntrico"
                else: mecanico_val = "Con Salto"
                parte = re.sub(patron_mecanico, '', parte, flags=re.IGNORECASE)

            m_iso_antes = re.search(r"(\d+)\s*[\"\'”’]\s*(?:iso|exc)", parte, re.IGNORECASE)
            m_iso_despues = re.search(r"(?:iso|exc)\s*(\d+)\s*(?:[\"\'”’]|seg|s\b)", parte, re.IGNORECASE)
            m_tiempo_directo = re.search(r"(\d+)\s*(?:\"|”|'|’|seg|segs)(?:\s|$|x|\b)", parte, re.IGNORECASE)

            iso_val = None
            if m_iso_antes: iso_val = m_iso_antes.group(1)
            elif m_iso_despues: iso_val = m_iso_despues.group(1)
            elif m_tiempo_directo: iso_val = m_tiempo_directo.group(1)

            series_deducidas = global_multiplier 
            multi_series = False
            
            m_multi = re.search(r'(?i)\b(?:series?|s)\s*([1-8])\s*(?:y|e|,|-|/)\s*([1-8])\b', parte)
            m_single = re.search(r'(?i)\b(?:series?|s)\s*([1-8])\b', parte)
            
            if m_multi:
                multi_series = True
                series_deducidas = max(series_deducidas, int(m_multi.group(1)), int(m_multi.group(2)))
                parte = parte.replace(m_multi.group(0), ' ')
            elif m_single:
                series_deducidas = max(series_deducidas, int(m_single.group(1)))
                parte = parte.replace(m_single.group(0), ' ')

            cadena_sets = re.findall(r'(?i)\b(\d+(?:[.,]\d+)?)\s*x\s*(\d+(?:[.,]\d+)?)\b', parte)
            if len(cadena_sets) >= 2 and re.search(r'(?i)x\s*\d+(?:[.,]\d+)?\s*[-–]\s*\d', parte):
                for p1, p2 in cadena_sets:
                    if '.' in p1 or ',' in p1 or float(p1.replace(',','.')) > float(p2.replace(',','.')):
                        pesos.append(p1)
                        reps.append(p2)
                    else:
                        pesos.append(p2)
                        reps.append(p1)
                
                series_deducidas = max(series_deducidas, len(cadena_sets))
                multi_series = True
                parte = re.sub(r'(?i)(?:\b\d+(?:[.,]\d+)?\s*x\s*\d+(?:[.,]\d+)?\s*[-–]*\s*)+', ' ', parte)
            
            m_serie_especifica = re.search(r'(?i)\bserie\s*([1-8])\b', parte)
            serie_objetivo = int(m_serie_especifica.group(1)) if m_serie_especifica else None
            pat_peso = r"(\d+(?:[.,]\d+)?(?:\s*-\s*\d+(?:[.,]\d+)?)*)" 
            pat_reps = r"(\d+(?:\s*-\s*\d+)*)"
            
            m_piramide = re.search(r"x\s*" + pat_reps + r"\s+" + pat_peso + r"(?!\s*(?:\"|'|seg|s\b|iso))", parte, re.IGNORECASE)
            m_reps_peso = re.search(pat_reps + r"\s*x\s*" + pat_peso + r"\s*(?:kkg|kgs?|kg|k)\b", parte, re.IGNORECASE)
            m_peso_reps = re.search(pat_peso + r"\s*(?:kkg|kgs?|kg|k)?\b\s*x\s*" + pat_reps + r"(?!\s*(?:\"|'|seg|s\b|iso))", parte, re.IGNORECASE)            
            m_reps_lado_peso = re.search(r"(?i)(\d+(?:-\d+)*)\s*(?:x|/|por|cada)\s*(?:lado|pierna|brazo)s?\s*x\s*" + pat_peso + r"(?:\s*(?:kkg|kg|k|kgs))?\b", parte)
            peso_val = None
            reps_val = None
            
            if m_piramide:
                reps_val = m_piramide.group(1)
                peso_val = m_piramide.group(2)
            elif m_reps_lado_peso:
                reps_val = m_reps_lado_peso.group(1)
                peso_val = m_reps_lado_peso.group(2)
            elif m_reps_peso:
                reps_val = m_reps_peso.group(1)
                peso_val = m_reps_peso.group(2)
            elif m_peso_reps:
                peso_val = m_peso_reps.group(1)
                reps_val = m_peso_reps.group(2)
            else:
                m_kg = re.search(pat_peso + r"\s*(?:kkg|kgs?|kg|k)\b", parte, re.IGNORECASE)
                if m_kg: peso_val = m_kg.group(1)
                
                m_reps_suelta = re.search(r"(?:^|[^a-zA-Z])x\s*" + pat_reps + r"(?!\s*(?:kg|k|kkg|lbs|cm|m|s|seg|min|\"|'))", parte, re.IGNORECASE)
                m_reps_inversa = re.search(r"(?:^|\s)" + pat_reps + r"\s*x\s+(?:[a-zA-Z]|\d+(?:[.,]\d+)?\s*(?:\"|'|seg|s\b|iso))", parte, re.IGNORECASE)
                
                if m_reps_suelta: reps_val = m_reps_suelta.group(1)
                elif m_reps_inversa: reps_val = m_reps_inversa.group(1)
                
                if not reps_val:
                    m_reps_inicio = re.search(r"^\s*" + pat_reps + r"\s+(?![xX]\b)", parte)
                    if m_reps_inicio: reps_val = m_reps_inicio.group(1)

                m_x_final = re.search(r"(?:^|[^a-zA-Z])x\s*(\d+)[-.,;]*\s*$", parte, re.IGNORECASE)
                if m_x_final:
                    val_final = m_x_final.group(1)
                    if int(val_final) <= 5 and reps_val and val_final != reps_val:
                        series_deducidas = max(series_deducidas, int(val_final))
                    else:
                        reps_val = val_final

            if not peso_val:
                m_db = re.search(r'(?i)\d+DB\s*(\d+(?:[.,]\d+)?)', parte)
                if m_db: peso_val = m_db.group(1)

            if not reps_val:
                m_reps_text = re.search(r'(?i)(\d+(?:-\d+)*)\s*(?:reps?|repeticiones|veces|idas_y_vueltas?|vueltas?)', parte)
                m_x_lado = re.search(r'(?i)(?:x\s*)?(\d+(?:-\d+)*)\s*(?:x|/|por|cada)?\s*(?:lado|lad0|lad|pierna|brazo)s?', parte)
                m_final_suelta = re.search(r'(?i)(?:^|\s)(\d+(?:-\d+)*)\s*$', parte.strip()) # Caza el '5' suelto final
                if m_reps_text: reps_val = m_reps_text.group(1)
                elif m_x_lado: reps_val = m_x_lado.group(1)
                elif m_final_suelta: reps_val = m_final_suelta.group(1)
                
            if multi_series:
                # Si indica "Serie 3 10kg", rellena los huecos de la Serie 1 y 2 con valores previos o vacíos.
                if serie_objetivo:
                    huecos_prev = serie_objetivo - 1
                    if huecos_prev > len(pesos): pesos.extend([pesos[-1] if pesos else ""] * (huecos_prev - len(pesos)))
                    if huecos_prev > len(reps): reps.extend([reps[-1] if reps else ""] * (huecos_prev - len(reps)))
                    if huecos_prev > len(isos): isos.extend([isos[-1] if isos else ""] * (huecos_prev - len(isos)))
                    if huecos_prev > len(gomas): gomas.extend([gomas[-1] if gomas else ""] * (huecos_prev - len(gomas)))
                    if huecos_prev > len(equipos): equipos.extend([equipos[-1] if equipos else ""] * (huecos_prev - len(equipos)))
                    if huecos_prev > len(espaciales): espaciales.extend([espaciales[-1] if espaciales else ""] * (huecos_prev - len(espaciales)))
                    if huecos_prev > len(mecanicos): mecanicos.extend([mecanicos[-1] if mecanicos else ""] * (huecos_prev - len(mecanicos)))

                huecos_pesos = max(0, series_deducidas - len(pesos))
                p_val = peso_val if peso_val else (pesos[-1] if pesos else None)
                if p_val: pesos.extend([p_val] * huecos_pesos)
                
                huecos_reps = max(0, series_deducidas - len(reps))
                r_val = reps_val if reps_val else (reps[-1] if reps else None)
                if r_val: reps.extend([r_val] * huecos_reps)
                
                huecos_isos = max(0, series_deducidas - len(isos))
                i_val = iso_val if iso_val else (isos[-1] if isos else None)
                if i_val: isos.extend([i_val] * huecos_isos)
                
                huecos_gomas = max(0, series_deducidas - len(gomas))
                g_val = goma_val if goma_val else (gomas[-1] if gomas else None)
                if g_val: gomas.extend([g_val] * huecos_gomas)

                huecos_equipos = max(0, series_deducidas - len(equipos))
                eq_val = equipo_val if equipo_val else (equipos[-1] if equipos else None)
                if eq_val: equipos.extend([eq_val] * huecos_equipos)

                huecos_espaciales = max(0, series_deducidas - len(espaciales))
                esp_val = espacial_val if espacial_val else (espaciales[-1] if espaciales else None)
                if esp_val: 
                    espaciales.extend([esp_val] * huecos_espaciales)
                elif not espaciales and huecos_espaciales > 0:
                    espaciales.extend([""] * huecos_espaciales)

                huecos_mecanicos = max(0, series_deducidas - len(mecanicos))
                mec_val = mecanico_val if mecanico_val else (mecanicos[-1] if mecanicos else None)
                if mec_val: mecanicos.extend([mec_val] * huecos_mecanicos)

            else:
                huecos_pesos = max(0, series_deducidas - 1 - len(pesos))
                if huecos_pesos > 0 and pesos: pesos.extend([pesos[-1]] * huecos_pesos)
                add_pesos = max(1, series_deducidas - len(pesos))
                p_val = peso_val if peso_val else (pesos[-1] if pesos else None)
                if p_val: pesos.extend([p_val] * add_pesos)

                huecos_reps = max(0, series_deducidas - 1 - len(reps))
                if huecos_reps > 0 and reps: reps.extend([reps[-1]] * huecos_reps)
                add_reps = max(1, series_deducidas - len(reps))
                r_val = reps_val if reps_val else (reps[-1] if reps else None)
                if r_val: reps.extend([r_val] * add_reps)

                huecos_isos = max(0, series_deducidas - 1 - len(isos))
                if huecos_isos > 0 and isos: isos.extend([isos[-1]] * huecos_isos)
                add_isos = max(1, series_deducidas - len(isos))
                i_val = iso_val if iso_val else (isos[-1] if isos else None)
                if i_val: isos.extend([i_val] * add_isos)

                huecos_gomas = max(0, series_deducidas - 1 - len(gomas))
                if huecos_gomas > 0 and gomas: gomas.extend([gomas[-1]] * huecos_gomas)
                add_gomas = max(1, series_deducidas - len(gomas))
                g_val = goma_val if goma_val else (gomas[-1] if gomas else "")
                gomas.extend([g_val] * add_gomas)

                huecos_equipos = max(0, series_deducidas - 1 - len(equipos))
                if huecos_equipos > 0 and equipos: equipos.extend([equipos[-1]] * huecos_equipos)
                add_equipos = max(1, series_deducidas - len(equipos))
                eq_val = equipo_val if equipo_val else (equipos[-1] if equipos else "")
                equipos.extend([eq_val] * add_equipos)

                huecos_espaciales = max(0, series_deducidas - 1 - len(espaciales))
                if huecos_espaciales > 0 and espaciales: espaciales.extend([espaciales[-1]] * huecos_espaciales)
                add_espaciales = max(1, series_deducidas - len(espaciales))
                esp_val = espacial_val if espacial_val else (espaciales[-1] if espaciales else "")
                espaciales.extend([esp_val] * add_espaciales)

                huecos_mecanicos = max(0, series_deducidas - 1 - len(mecanicos))
                if huecos_mecanicos > 0 and mecanicos: mecanicos.extend([mecanicos[-1]] * huecos_mecanicos)
                add_mecanicos = max(1, series_deducidas - len(mecanicos))
                mec_val = mecanico_val if mecanico_val else (mecanicos[-1] if mecanicos else "")
                mecanicos.extend([mec_val] * add_mecanicos)
        
        pesos_globales.append(pesos)
        reps_globales.append(reps)
        isos_globales.append(isos)
        gomas_globales.append(gomas)
        equipos_globales.append(equipos)
        espaciales_globales.append(espaciales)
        mecanicos_globales.append(mecanicos)

    def to_subarray_str(lista_global, vacio="-"):
        if not lista_global: return None
        arrays_internos = []
        for sublista in lista_global:
            flat = [str(item).replace(' ', '').replace(',', '.').replace('-', ', ') if item is not None and str(item).strip() != "" else vacio for item in sublista]
            if all(item == vacio for item in flat):
                arrays_internos.append("[]")
            else:
                arrays_internos.append(f"[{', '.join(flat)}]")
        if all(arr == "[]" for arr in arrays_internos): return None
        if len(arrays_internos) == 1: return arrays_internos[0]
        return f"[{', '.join(arrays_internos)}]"

    def to_subarray_str_text(lista_global, vacio="-"):
        if not lista_global: return None
        arrays_internos = []
        for sublista in lista_global:
            flat = [str(item).strip() if item is not None and str(item).strip() != "" else vacio for item in sublista]
            if all(item == vacio for item in flat):
                arrays_internos.append("[]")
            else:
                arrays_internos.append(f"[{', '.join(flat)}]")
        if all(arr == "[]" for arr in arrays_internos): return None
        if len(arrays_internos) == 1: return arrays_internos[0]
        return f"[{', '.join(arrays_internos)}]"

    peso_final = to_subarray_str(pesos_globales, vacio="-")
    reps_final = to_subarray_str(reps_globales, vacio="-")
    iso_final = to_subarray_str(isos_globales, vacio="-")
    color_goma = to_subarray_str_text(gomas_globales, vacio="Sin goma")
    equipamiento_final = to_subarray_str_text(equipos_globales, vacio="Sin material")
    modificador_espacial_final = to_subarray_str_text(espaciales_globales, vacio="-")
    modificador_mecanico_final = to_subarray_str_text(mecanicos_globales, vacio="-")
    cantidad_otra_unidad = to_subarray_str(cants_globales, vacio="-")
    tipo_otra_unidad = to_subarray_str_text(tipos_globales, vacio="-")
    rir_val = f"[{rir_val.replace(' ', '').replace(',', '.').replace('-', ', ')}]" if rir_val else None
    intensidad_cardio_final = to_subarray_str_text(intensidades_globales, vacio="-")
    
    # Destruye todos los remanentes numéricos y ruido de formato para aislar el nombre puro del ejercicio.
    nombres_limpios = []
    for parte in ejercicios_compuestos:
        nombre = parte.replace(';', ' ').replace('~', ' ')
        nombre = re.sub(r'^[\s"\']+', '', nombre)

        # Destruye el ruido de series extra o condicionales. Ej: "al menos 2 de las series" -> ""
        nombre = re.sub(r'(?i)\b(?:al\s*menos|al)\s*\d+\s*de\s*las(?:\s*\d+)?(?:\s*series?)?\b', '', nombre)

        # Destruir ruido de cabeceras sueltas. Ej: "Sesión 1 V2" -> ""
        nombre = re.sub(r'(?i)^\s*sesi[óo]n\s*\d+.*', '', nombre)

        nombre = re.sub(r'(?i)\b\d+(?:[.,]\d+)?(?:-\d+(?:[.,]\d+)?)*\s*x\s*\d+(?:-\d+)*\b', '', nombre)
        
        nombre = re.sub(r'(?i)\b(?:series?|s)\s*\d+(?:\s*(?:y|e|,|-|/|y\s*la)\s*\d+)*\b', '', nombre)
        nombre = re.sub(r'(?i)\bs\d+\b', '', nombre)
        nombre = re.sub(r'(?i)\b(?:serie|series|s)\b', '', nombre)
        
        nombre = re.sub(r'(?i)-?\d+(?:-\d+)*\s*rir(?:[^\sA-Za-z]*\d+(?:-\d+)*)?\b', '', nombre)
        
        # Destruye RIR/RPE del nombre, pero lo salva si lleva una 'k'. Ej: "RIR 10k" (se refería a peso, no lo borra).
        nombre = re.sub(r'(?i)\brir\s*\d+(?:-\d+)*\b(?!\s*(?:k\b|kkg|kgs?|kg|lbs|%))', '', nombre)
        nombre = re.sub(r'(?i)\brpe\s*\d+(?:-\d+)*\b(?!\s*(?:k\b|kkg|kgs?|kg|lbs|%))', '', nombre)
        nombre = re.sub(r'(?i)@\s*\d+(?:-\d+)*\b(?!\s*(?:k\b|kkg|kgs?|kg|lbs|%))', '', nombre)
        nombre = re.sub(r'(?i)\b(?:rir|rpe)\b', '', nombre)

        # Destruye isometrías con segundos del nombre. Ej: "Sentadilla iso 10 seg" -> "Sentadilla"
        nombre = re.sub(r'(?i)\b\d+(?:[.,]\d+)?\s*(?:\"|\'|”|’|seg|s\b|segs)(?:\s*(?:de\s*)?(?:isometr[ií]a|isom[eé]tric[oa]s?|iso|exc|exc[eé]ntric[oa]s?))?(?!\w)', '', nombre)
        nombre = re.sub(r'(?i)\b(?:iso|exc)\s*[\"\'”’]?\s*\d+(?:[.,]\d+)?\s*(?:\"|\'|”|’|seg|s\b|segs)?\b', '', nombre)
        nombre = re.sub(r'(?i)\b(?:iso|exc)\b', '', nombre)
        
        # Borra indicadores de extremidad (ya están en la columna "por_lado"). Ej: "Zancada por pierna" -> "Zancada"
        nombre = re.sub(r'(?i)(?:x|/|por|cada)\s*(?:lado|lad0|lad|pierna|brazo)s?(?:\s*y\s*direcci[óo]n)?\b', '', nombre)
        nombre = re.sub(r'(?i)\b(?:uni|bi)lateral\b|\buni\b', '', nombre)

        nombre = re.sub(r'(?i)\b\d+(?:-\d+)*\s*x\s*\d+(?:[.,]\d+)?(?:-\d+(?:[.,]\d+)?)*\s*kg\b', '', nombre)
        nombre = re.sub(r'(?i)\b\d+(?:[.,]\d+)?\s*(?:kg|k|kkg|kgs|lbs)(?![a-zA-Z])', '', nombre)
        nombre = re.sub(r'(?i)\b\d+(?:[.,]\d+)?\s*kg\b', '', nombre)
        nombre = re.sub(r'(?i)(?:^|\s)x\s*\d+(?:-\d+)*\s*(?:reps?|veces)?\b', ' ', nombre)
        nombre = re.sub(r'\(\s*x\s*\d+\s*\)', '', nombre)
        nombre = re.sub(r'(?i)\b\d+(?:-\d+)*\s*x\b', '', nombre)

        nombre = re.sub(r'\b\d+(?:[\s.,-]+\d+)+\b', '', nombre)
        nombre = re.sub(r'(?i)\d+DB(?:\d+(?:[.,]\d+)?)?\s*(?:kg|k|kgs)?', '', nombre)
        
        # Aniquila todos los colores de las gomas si se filtraron al nombre. Ej: "Remo goma roja" -> "Remo"
        nombre = re.sub(r'(?i)(?:con\s*)?(?:gomas?|bandas?|g)?[\s.]*(?:de\s*)?(?:color\s*)?(?:roja|negra|morada|verde|azul|amarilla|naranja|rosa|gris|blanca)s?(?:x\d*)?', '', nombre)
        nombre = re.sub(r'(?i)\b(?:roj[oa]s?|rojaa|orjas?|turquesas?|negr[oa]s?|ngeras?|nergas?|negrs?|amarill[oa]s?|amrillas?|morad[oa]s?|verd[eo]s?|azules?|azuls?|gris(?:es)?|blanc[oa]s?)\b', '', nombre)
        nombre = re.sub(r'(?i)\b(?:con\s*)?(?:gomas?|bandas?|slides?)\b', '', nombre)

        nombre = re.sub(r'(?i)\bg\b', '', nombre)

        # Destruye los materiales explícitos del nombre del ejercicio (Ya se extrajeron). Ej: "Press con mc" -> "Press"
        nombre = re.sub(r'(?i)\b(?:con|en|desde|sobre|a|al)?\s*(?:doble\s+|una\s+)?(?:mancuernas?|mancuenras?|macuernas?|mc|db|dumbbells?|kettlebells?|kb|kbs|ktbs?|kts?|barras?(?:\s*z)?|barraz|bbarras?|discos?|trx|picas?|chalecos?|lastres?|wall?l?balls?|walballs?|bal[oó]n(?:es)?|poleas?(?:\s+(?:alta|baja|media)s?)?|ploaes?|polaes?|poleras?|steps?|caj[oó]n(?:es)?(?:\s+(?:roj[oa]s?|negr[oa]s?|verd[eo]s?|amarill[oa]s?|azules?|azuls?|blanc[oa]s?))?|box)\b', '', nombre)

        # Borra pesos sueltos pero protege frases clave de fallo. Ej: "10kg" se borra, pero "10kg últimas" se mantiene.
        nombre = re.sub(r'(?i)(?:^|\s)\d+(?:[.,]\d+)?\s*(?:kg|k|kkg|kgs|lbs)\b(?!\s*[úu]lt[ií]?mas?\b)', '', nombre)

        # Borra intensidades cualitativas. Ej: "Sentadilla lento" -> "Sentadilla"
        nombre = re.sub(r'(?i)\b(?:lento|controlado|explosivo|r[áa]pid[oa]s?|tempo)\b', '', nombre)

        nombre = re.sub(r'(?i)\b\d+(?:-\d+)*\s*(?:reps?|repeticiones|veces)\b', '', nombre)

        nombre = re.sub(r'(?i)\b\d*\s*pasillos?\s*y\s*medio\b', ' ', nombre)

        # Borra unidades de cardio, niveles y watts. Ej: "10 mins", "nivel 5", "200 w" -> ""
        nombre = re.sub(r'(?i)(?:<|>)?\s*(?:\d+(?:[.,]\d+)?\s*)?(?:km/?h|kms?|metros?|(?<![a-zA-Z])m\b|mins?|minutos?|calor[ií]as?|kcals?|cals?|pasillos?|(?<!_)vueltas?|resistencia|niveles?|lvl|watts?|(?<![a-zA-Z])w\b)\b', ' ', nombre)
        nombre = re.sub(r'(?i)\b(?:resistencia|niveles?|lvl)\s*\d+(?:[.,]\d+)?\b', '', nombre)

        # Elimina "pasillos" incluso si se quedó pegado a otra palabra
        nombre = re.sub(r'(?i)pasillos?\b', '', nombre)
        nombre = re.sub(r'(?i)(?:<|>)?\s*\d+\s*(?:mins?|\')', '', nombre)
        nombre = re.sub(r'(?i)\b\d*\s*(?:idas?_y_vueltas?|idas?\s*y\s*vueltas?|idas?|vueltas?)\b', '', nombre)
        nombre = re.sub(r'(?i)/?\b(?:rest|descanso)\b', '', nombre) 

        nombre = re.sub(r'^\s*\d+[a-zA-Z]?\s*[-).]\s*', '', nombre)
        nombre = re.sub(r'[-.,;?!\s]+$', '', nombre.strip())

        nombre = re.sub(r'(?i)(?:\d+[,.])?\s*k+g[s]?\s*x?\s*\d+\b', '', nombre)
        nombre = re.sub(r'(?i)[+-]?\s*\d+\s*(?:kkg|kgkg|kgs|kg)', '', nombre)
        nombre = re.sub(r'(?i)(?<=[a-zA-Z])(?:kkg|kgkg|kgs|kg)\b', '', nombre)
        nombre = re.sub(r'(?i)\+?\s*(?:kkg|kgkg|kgs|kg)\b', '', nombre)
        nombre = re.sub(r'(?i)\bkg(?=[a-zA-Z])', '', nombre)
        nombre = re.sub(r'(?i)\d*[,.]?\d+\s*k+g[s]?\b', '', nombre)
        nombre = re.sub(r'(?i)(?<=[a-zA-Z])k+g[s]?\b', '', nombre)

        nombre = re.sub(r'(?i)\bx\d+x\b', '', nombre)
        nombre = re.sub(r'(?i)(?<=[a-zA-Z])x\s*\d+\b', '', nombre)
        nombre = re.sub(r'(?i)\bx\d+x\b', '', nombre)
        nombre = re.sub(r'(?i)\bx\d+(?=[a-zA-Z])', ' ', nombre)
        nombre = re.sub(r'(?i)\(\s*x\d+\b\)?', '', nombre)

        # Aniquilar ruido de series opcionales. Ej: "al menos 2 de las series" -> ""
        nombre = re.sub(r'(?i)\bal\s*menos\s*\d+\s*de\s*las\s*\d+\s*series?\b', '', nombre)
        nombre = re.sub(r'(?i)(?:<|>)?\s*\d+\s*(?:mins?|\'|”|")', '', nombre)

        nombre = re.sub(r'(?i)(?:[<>])?\s*x\s*\d+\s*(?:veces)?\b', '', nombre)
        nombre = re.sub(r'(?i)(?<=[a-zA-Z])\d*x\d+\b', '', nombre)
        nombre = re.sub(r'(?i)\d+\s*[\"\']\s*x?\s*\d*\b', '', nombre)
        nombre = re.sub(r'(?i)\(\s*x\s*\d+\s*\)?', '', nombre)
        nombre = re.sub(r'(?i)\b(?:entre\s*)?\d+\s*(?:rondas?|vueltas?)\b', '', nombre)
        nombre = re.sub(r'(?i)\bentre\s*\d+\b', '', nombre)
        
        nombre = re.sub(r'[<>\?]', '', nombre)
        nombre = re.sub(r'(?i)\bseroe\b.*', '', nombre)
        nombre = re.sub(r'\s*\(.*?\)\s*', ' ', nombre) 
        
        # Borrar conectores preposicionales huérfanos. Ej: "Dominadas con " -> "Dominadas"
        nombre = re.sub(r'(?i)\b(?:a|@|con|de|en|entre|hacia)\s*$', '', nombre.strip())
        nombre = re.sub(r'(?i)\b(?:a|@|con|de|en|entre|hacia)\s*$', '', nombre.strip())
        nombre = re.sub(r'\by\s*$', '', nombre.strip()) 
        
        # Borra intensidades cualitativas de cardio. Ej: "5 fuertes" -> ""
        nombre = re.sub(r'(?i)(?:-\s*)?\d+(?:[.,]\d+)?\s*(?:a\s*tope|suaves?|medias?|medios?|moderadas?|moderados?|fuertes?|ligeras?|ligeros?|sprint)\b', '', nombre)
        nombre = re.sub(r'(?i)\b(?:a\s*tope|suaves?|medias?|medios?|moderadas?|moderados?|fuertes?|ligeras?|ligeros?|sprint)\b', '', nombre)

        # Borra prefijos sueltos de unidades de cardio al inicio. Ej: "Calorías remo" -> "remo"
        nombre = re.sub(r'(?i)^(?:calor[ií]as?|kcals?|cals?|metros?|kms?)\s+', '', nombre)

        nombre = re.sub(r'(?i)(?:^|\s)x\b(?!\s*\d)', ' ', nombre)
        
        nombre = re.sub(r'[-–]{2,}', '', nombre)
        nombre = re.sub(r'^\s*\d+\s+(?=[a-zA-Z])', '', nombre)
        nombre = re.sub(r'^\s*\d+\s*$', '', nombre)

        # Borrar formatos metabólicos del nombre si se cruzaron. Ej: "amrap flexiones" -> "flexiones"
        nombre = re.sub(r'(?i)\b(?:emom|amrap|tabata)\b', '', nombre)
        siglas_vip = ['dl', 'bp', 'sq', 'bi', 'sh', 'tr', 'y', 't', 'w', 'l']
        if len(nombre.strip()) <= 2 and not re.search(r'\d', nombre) and nombre.strip().lower() not in siglas_vip:
            nombre = ''
            
        # 1. Restaura los formatos de porcentaje para que no se borren. Ej: "PCT80 a PCT90_porc" -> "80 a 90%"
        nombre = re.sub(r'(?i)PCT(\d+)\s*a\s*PCT(\d+)_porc', r'\1 a \2%', nombre)
        nombre = re.sub(r'(?i)PCT(\d+)_porc', r'\1%', nombre)

        # 2. Aniquilamos cualquier PCT sobrante que estuviera perdido o entre paréntesis.
        nombre = re.sub(r'(?i)\(?\bPCT[\d\-]+_porc\b\)?', '', nombre)

        nombre = nombre.replace('TRENINFERIOR', 'solo piernas').replace('TRENSUPERIOR', 'solo brazos')
        nombre = re.sub(r'(?i)\bm[ií]nimos?\b', '', nombre)

        nombre = nombre.replace('idas_y_vueltas', 'idas y vueltas') 
        nombre = nombre.replace('bilateral', '') 
        nombre = re.sub(r'(?i):\s*sin\b', '', nombre) 
        nombre = re.sub(r'(?i)(?:y|:)\s*sin\b', '', nombre) 
        nombre = re.sub(r'(?i)\b:\s*$', '', nombre.strip())
        nombre = re.sub(r'\by\s*$', '', nombre.strip()) 
        nombre = re.sub(r'(?i)\by\s*\d+\s*$', '', nombre.strip())
        
        nombre = re.sub(r'^[=+\-@:;.,\s]+', '', nombre)

        nombre = re.sub(r'(?i)[.,]?\s*\bobjetivo\b\s*[.,]?', '', nombre)
        nombre = re.sub(r'(?i)^\s*(?:en|a|con|de|para)\s+', '', nombre)
        
        # Limpia frases de libre elección. Ej: "como quieras" -> ""
        nombre = re.sub(r'(?i)^(?:una\s*x\s*serie\s*)?como\s*quieras\s*[:.]?\s*', '', nombre)
        nombre = re.sub(r'\s+[.,;:_]\s+', ' ', nombre)
        
        # Estandariza opciones duales. Ej: "remo/bici" -> "remo o bici"
        patron_maq = r'(?i)\b(remo|airbike|ski|skierg|bici|cinta|el[ií]ptica)\s*[-/]\s*(remo|airbike|ski|skierg|bici|cinta|el[ií]ptica)\b'
        nombre = re.sub(patron_maq, r'\1 o \2', nombre)
        nombre = re.sub(patron_maq, r'\1 o \2', nombre)

        nombre = re.sub(r'(?i)\b(?:en\s*)?menos\s*(?:de)?\b', '', nombre)
        nombre = re.sub(r'(?i)\b(?:a|con)?\s*\d+(?:[.,]\d+)?\s*(?:km/?h|kms?)\b', '', nombre)

        # Destruye Modificadores Espaciales del nombre porque ya se extrajeron. Ej: "60cm" -> ""
        nombre = re.sub(r'(?i)\b\d+\s*(?:cm|cms|º|grados?)', '', nombre)
        
        # Destruye Modificadores Mecánicos (iso, exc), pero protege saltos si es la palabra principal.
        # Ej: "Sentadilla iso" -> "Sentadilla", pero "Salto cajón" se mantiene intacto.
        nombre = re.sub(r'(?i)\b(?:con\s*)?(?:saltos?(?!\s*(?:caj[oó]n|longitudinal))|isometr[ií]a|isom[eé]tric[oa]s?|iso|exc[eé]ntric[oa]s?|exc)\b', '', nombre)

        nombre = re.sub(r'(?<!"[a-zA-Z])["\']+$', '', nombre.strip())
        nombre = re.sub(r'[\s\-–—−:;.,/]+$', '', nombre)
        nombre = re.sub(r'[\s\-–—−:;.,/]+$', '', nombre)
        nombre = re.sub(r'/\s*$', '', nombre.strip())
        nombre = re.sub(r'\s*[-–]\s*$', '', nombre.strip())
        
        # Transformar guiones huérfanos antes de material en "con". Ej: "Zancadas - Doble" -> "Zancadas con Doble"
        nombre = re.sub(r'(?i)\s*[-–]\s*(Doble|Una)\b', r' con \1', nombre)
        nombre = re.sub(r'(?i)\b(Doble\s+\w+|Una\s+\w+)\s+\1\b', r'\1', nombre)
        nombre = re.sub(r'[\s/]+$', '', nombre.strip())

        # Eliminar cualquier tipo de comilla para dejar el nombre totalmente limpio
        nombre = re.sub(r'["“”\'‘’]', '', nombre)
        
        nombre = re.sub(r'\s+[-–]\s+', ' ', nombre) 
        
        # Bucle que destruye TODAS las preposiciones y conectores encadenados al final.
        # Ej: "Dominadas en a " -> "Dominadas"
        nombre = re.sub(r'(?i)(?:\b(?:en|a|de|con|por|hacia|y|o|x|s|desde)\b[\s:;,.\-]*)+$', '', nombre.strip())    

        nombre = re.sub(r'\s*\d+$', '', nombre.strip()) 
        
        #Eliminamos las preposiciones
        nombre = re.sub(r'(?i)(?:\b(?:en|a|de|con|por|hacia|y|o|x|s|desde)\b[\s:;,.\-]*)+$', '', nombre.strip())

        # Destruir duplicados causados por series intermedias metidas en el texto.
        # Ej: "Flexiones 8 flexiones" a "Flexiones"
        nombre = re.sub(r'(?i)\b([a-záéíóúñ]+)\s+\d+\s+\1\b', r'\1', nombre)
        
        # limpieza de espacios y signos
        nombre = nombre.rstrip(' /\\-–—−:;.,')
        nombre = re.sub(r'\s+', ' ', nombre).strip()

        # Si el nombre ha quedado tan triturado que es solo un número (Ej: "35"), lo vaciamos porque no es un nombre válido.
        if re.match(r'^\d+$', nombre):
            nombre = ""

        # Borra todos los números sueltos que no se hayan extraído
        nombre = re.sub(r'\b\d+\b', '', nombre)
        
        # Al borrar números desde el medio pueden quedar espacios dobles, se aspiran de nuevo.
        nombre = re.sub(r'\s+', ' ', nombre).strip()

        # Devolvemos los nombres protegidos a su estado  original al final
        nombre = nombre.replace('noventa_noventa', '90/90')
        nombre = nombre.replace('medio_ejercicio', '1/2')
        nombre = nombre.replace('step_up', 'Step up') 
        
        nombres_limpios.append(nombre if nombre else "")

    ejercicio_limpio = nombres_limpios[0] if len(nombres_limpios) > 0 else None
    ejercicio_2 = nombres_limpios[1] if len(nombres_limpios) > 1 else None
    ejercicio_3 = nombres_limpios[2] if len(nombres_limpios) > 2 else None
    ejercicio_4 = nombres_limpios[3] if len(nombres_limpios) > 3 else None 
    ejercicio_5 = nombres_limpios[4] if len(nombres_limpios) > 4 else None 

    # Si algún ejercicio ha quedado vacío, intentamos rescatarlo a partir de pistas en el texto original o el tipo de unidad.
    if (ejercicio_limpio is None or str(ejercicio_limpio).strip() == ""):
        if re.search(r'km/h', texto_original, re.IGNORECASE) or (tipo_otra_unidad and 'km/h' in str(tipo_otra_unidad)):
            ejercicio_limpio = "Cinta"
        elif tipo_otra_unidad and ('vueltas' in str(tipo_otra_unidad).lower() or 'pasillos' in str(tipo_otra_unidad).lower()):
            ejercicio_limpio = "Carrera"
        elif re.search(r'(?i)\bstep\b', texto_original):
            ejercicio_limpio = "Step up"
        elif re.search(r'(?i)\bsaltos?\b', texto_original):
            ejercicio_limpio = "Saltos" 
        elif equipamiento_final and str(equipamiento_final) not in ['[]', 'None', '']:
            eq_str = str(equipamiento_final).replace('[', '').replace(']', '').split(',')[0].strip()
            ejercicio_limpio = eq_str
        
    return peso_final, reps_final, iso_final, color_goma, equipamiento_final, modificador_espacial_final, modificador_mecanico_final, cantidad_otra_unidad, tipo_otra_unidad, rir_val, intensidad_cardio_final, ejercicio_limpio, ejercicio_2, ejercicio_3, ejercicio_4, ejercicio_5, por_lado

def main():
    """
    Función orquestadora del pipeline de datos (ETL).
    Ejecuta el ciclo de lectura, limpieza, extracción, transformación y exportación.
    """
    
    # Extracción de datos del JSON original
    with open('_session__202602181741.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    tabla_sesiones = pd.DataFrame(data['session'])

    # Control de sesiones nulas
    sesiones_nulas = tabla_sesiones[tabla_sesiones['description'].isnull()]
    if not sesiones_nulas.empty:
        print(f"Se han saltado {len(sesiones_nulas)} sesiones vacías")
    
    tabla_sesiones = tabla_sesiones.dropna(subset=['description']).copy()

    # Dividir la descripcion en partes estructuradas
    tabla_sesiones['datos_separados'] = tabla_sesiones['description'].apply(procesar_descripcion)
    tabla_final = tabla_sesiones.explode('datos_separados').dropna(subset=['datos_separados'])

    tabla_final['circuito'] = tabla_final['datos_separados'].str.get('circuito_perteneciente')
    
    # Extrae el tipo de circuito
    tabla_final['tipo_circuito'] = tabla_final['circuito'].str.extract(r'(?i)(movilidad|activaci[óo]n|fuerza|metab[óo]lico|metcon|met\b|core|calentamiento|bloque|aer[oó]bico(?:\s*cl)?|cardio)', expand=False).str.capitalize()
    tabla_final['series_circuito'] = tabla_final['circuito'].str.extract(r'(?i)(?:x\s*)?(\d+)\s*(?:series?|rondas?)', expand=False)
    tabla_final['ejercicio_bruto'] = tabla_final['datos_separados'].str.get('linea_texto')

    # Corta en líneas individuales si hay varios ejercicios en la misma línea (Ej: "Sentadilla + Press militar")
    tabla_final['ejercicio_bruto'] = tabla_final.apply(separar_metabolicos, axis=1)
    tabla_final = tabla_final.explode('ejercicio_bruto')

    # Enumeración ejercicios dentro del circuito
    tabla_final['orden_ejercicio'] = tabla_final.groupby(['id', 'circuito']).cumcount() + 1

    # Formato metab
    tabla_final['formato_circuito'] = tabla_final['circuito'].str.extract(r'(?i)(emom|amrap|\d+(?:[-/]\d+)+|cl)')
    tabla_final['formato_circuito'] = tabla_final['formato_circuito'].apply(arreglar_esquema_fecha)

    # Extraer minutos
    minutos_titulo = tabla_final['circuito'].str.extract(r'(?i)(\d+(?:[.,]\d+)?)\s*(?:mins?|minutos?|\'|’|´)')
    minutos_ej = tabla_final['ejercicio_bruto'].str.extract(r'(?i)\b(?:emom|amrap|tc|time cap|por tiempo|for time)\b\s*(\d+(?:[.,]\d+)?)\s*(?:mins?|minutos?|\'|”|"|’|´)?')
    tabla_final['minutos_circuito'] = minutos_titulo[0].fillna(minutos_ej[0])
    
    # Extracción columnas
    extracciones = tabla_final['ejercicio_bruto'].apply(analizar_ejercicio)
    tabla_final['peso_kg'] = [x[0] for x in extracciones]
    tabla_final['repeticiones'] = [x[1] for x in extracciones]
    tabla_final['tiempo_iso_seg'] = [x[2] for x in extracciones]
    tabla_final['color_goma'] = [x[3] for x in extracciones]
    tabla_final['equipamiento'] = [x[4] for x in extracciones]

    tabla_final['modificador_espacial'] = [x[5] for x in extracciones] 
    tabla_final['modificador_mecanico'] = [x[6] for x in extracciones] 
    
    tabla_final['cantidad_otra_unidad'] = [x[7] for x in extracciones]
    tabla_final['tipo_otra_unidad'] = [x[8] for x in extracciones]
    
    tabla_final['rir'] = [x[9] for x in extracciones]
    tabla_final['intensidad_cardio'] = [x[10] for x in extracciones] 

    tabla_final['ejercicio_limpio'] = [x[11] for x in extracciones]
    tabla_final['ejercicio_2'] = [x[12] for x in extracciones]
    tabla_final['ejercicio_3'] = [x[13] for x in extracciones]
    tabla_final['ejercicio_4'] = [x[14] for x in extracciones] 
    tabla_final['ejercicio_5'] = [x[15] for x in extracciones] 
    tabla_final['por_lado'] = [x[16] for x in extracciones] 

    # Ordenar
    tabla_final['hour_date'] = pd.to_datetime(tabla_final['hour_date'], errors='coerce')

    if ORDENAR_POR == 'cliente':
        tabla_final = tabla_final.sort_values(by=['customer_id', 'hour_date', 'id'], na_position='last')
    elif ORDENAR_POR == 'sesion':
        tabla_final = tabla_final.sort_values(by=['id', 'hour_date'], na_position='last')

    tabla_final['hour_date'] = tabla_final['hour_date'].fillna("Por programar")

    # Columnas CSV
    columnas_visibles = [
        'id', 
        'customer_id', 
        'counter', 
        'hour_date', 
        
        'circuito', 
        'tipo_circuito', 
        'series_circuito',
        'formato_circuito', 
        'minutos_circuito',
        
        'orden_ejercicio', 
        'ejercicio_limpio', 
        'ejercicio_2',      
        'ejercicio_3',
        'ejercicio_4',
        'ejercicio_5', 
        
        'peso_kg', 
        'repeticiones', 
        'por_lado', 
        'equipamiento',
        'tiempo_iso_seg', 
        'rir',
        'intensidad_cardio',
        
        'color_goma', 
        'cantidad_otra_unidad', 
        'tipo_otra_unidad', 
        'modificador_espacial', 
        'modificador_mecanico',
        
        'ejercicio_bruto'
    ]
    tabla_final = tabla_final[columnas_visibles]

    # A veces se duplican ejercicios si el etrenador hizo copia y pega
    tabla_final = tabla_final.drop_duplicates()

    #Utilidad
    def clasificar_utilidad(fila):
        # 3 = vacío
        ej_1_vacio = pd.isna(fila['ejercicio_limpio']) or str(fila['ejercicio_limpio']).strip() == ""
        ej_2_vacio = 'ejercicio_2' not in fila or pd.isna(fila['ejercicio_2']) or str(fila['ejercicio_2']).strip() == ""
        
        if ej_1_vacio and ej_2_vacio:
            return 3
            
        # 1 = nombre demasiado largo
        if len(str(fila['ejercicio_limpio']).strip()) > 60:
            return 1
            
        # Outliers
        try:
            # Outlier de peso
            if not pd.isna(fila['peso_kg']) and str(fila['peso_kg']) not in ['[]', '']:
                pesos = ast.literal_eval(str(fila['peso_kg']))
                if any(float(p) > 300 for p in pesos):
                    return 2
                    
            if not pd.isna(fila['repeticiones']) and str(fila['repeticiones']) not in ['[]', '']:
                reps = ast.literal_eval(str(fila['repeticiones']))
                es_cardio = any(palabra in str(fila['ejercicio_limpio']).lower() for palabra in ['jumping', 'comba', 'saltos', 'skipping', 'abdominales', 'step', 'remo', 'ski', 'skierg', 'cinta', 'bici', 'bike', 'elíptica', 'trineo'])
                
                # Límite re de reps
                limite_reps = 5000 if es_cardio else 100
                if any(float(r) > limite_reps for r in reps):
                    return 2
            
            # Revisa que nadie corra a 30 km/h (outlier)
            if not pd.isna(fila['cantidad_otra_unidad']) and str(fila['cantidad_otra_unidad']) not in ['[]', '']:
                cants = ast.literal_eval(str(fila['cantidad_otra_unidad']))
                tipos = ast.literal_eval(str(fila['tipo_otra_unidad'])) if not pd.isna(fila['tipo_otra_unidad']) else []
                for cant, tipo in zip(cants, tipos):
                    if 'km/h' in tipo and float(cant) > 30:
                        return 2
        except:
            pass 

        # 4 = título o formato de circuito
        ej_limpio_lower = str(fila['ejercicio_limpio']).strip().lower()
        palabras_formato = ['emom', 'amrap', 'tabata', 'circuito', 'bloque', 'metab[óo]lico', 'metcon', 'fase', 'calentamiento', 'movilidad', 'descansos?', 'm[áa]x', 'sesi[óo]n']
        if any(re.search(rf'(?i)\b{p}\b', ej_limpio_lower) for p in palabras_formato):
            return 4
            
        # 5 = Ejercicio vacío
        def is_empty(val):
            return pd.isna(val) or str(val).strip() in ['', '[]', 'None']

        if is_empty(fila['peso_kg']) and is_empty(fila['repeticiones']) and is_empty(fila['tiempo_iso_seg']) and is_empty(fila['cantidad_otra_unidad']):
            tiene_formato = not is_empty(fila.get('formato_circuito'))
            tiene_minutos = not is_empty(fila.get('minutos_circuito'))

            if tiene_formato or tiene_minutos:
                pass 
            else:
                return 5 

        # 0 = Calidad buena
        return 0

    tabla_final['utilidad'] = tabla_final.apply(clasificar_utilidad, axis=1)
    
    if 'utilidad' not in columnas_visibles:
        columnas_visibles.append('utilidad')
        tabla_final = tabla_final[columnas_visibles]
    
    tabla_final.to_csv('resultado_limpio.csv', sep=';', encoding='utf-8-sig', index=False)
    print(f"Archivo 'resultado_limpio.csv' generado (Ordenado por: {ORDENAR_POR})")

if __name__ == '__main__':
    main()

    # Usar thefuzz para detectar ejercicios similares y unificar etiquetas (ej: "Sentadilla frontal" vs "Front squat")