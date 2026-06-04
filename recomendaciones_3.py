import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder
from collections import Counter
import random

# ─────────────────────────────────────────────
# FUNCIÓN PRINCIPAL DE RECOMENDACIÓN (VERSIÓN PROFESIONAL)
# ─────────────────────────────────────────────
def obtener_musica_recomendada(supabase, user_id: str) -> list:
    """
    Sistema profesional de recomendación musical.
    Prioriza artistas favoritos, balancea géneros y evita repeticiones.
    """
    # 1. Obtener preferencias del usuario
    pref = supabase.table("preferencias_usuario")\
        .select("genero_favorito, artista_favorito")\
        .eq("usuario_id", user_id).execute().data
    
    # 2. Si no hay preferencias, mostrar canciones populares
    if not pref:
        populares = supabase.table("canciones")\
            .select("*")\
            .order("popularidad", desc=True)\
            .limit(12)\
            .execute().data or []
        return populares
    
    # 3. Procesar géneros favoritos
    generos_str = pref[0].get("genero_favorito", "")
    generos_fav = [g.strip() for g in generos_str.split(",")] if generos_str else []
    
    # 4. Procesar artistas favoritos
    artistas_str = pref[0].get("artista_favorito", "")
    artistas_fav = [a.strip() for a in artistas_str.split(",")] if artistas_str else []
    
    # 5. Obtener historial de canciones ya escuchadas
    historial = supabase.table("interacciones")\
        .select("cancion_id")\
        .eq("usuario_id", user_id)\
        .execute().data or []
    ids_escuchadas = set([h["cancion_id"] for h in historial])
    
    # 6. Obtener canciones que ya son favoritas
    favoritos = supabase.table("interacciones")\
        .select("cancion_id")\
        .eq("usuario_id", user_id)\
        .eq("es_favorito", True)\
        .execute().data or []
    ids_favoritas = set([f["cancion_id"] for f in favoritos])
    
    # 7. Recopilar canciones por género y artista
    canciones_por_genero = {}
    canciones_por_artista = {}
    
    for genero in generos_fav:
        if genero:
            canciones_genero = supabase.table("canciones")\
                .select("*")\
                .eq("genero", genero)\
                .execute().data or []
            canciones_por_genero[genero] = canciones_genero
    
    for artista in artistas_fav:
        if artista:
            canciones_artista = supabase.table("canciones")\
                .select("*")\
                .ilike("artista", f"%{artista}%")\
                .execute().data or []
            canciones_por_artista[artista] = canciones_artista
    
    recomendadas = []
    ids_agregados = set()
    
    # 8. Calcular distribución balanceada
    num_generos = len(generos_fav)
    num_artistas = len(artistas_fav)
    total_deseado = 20
    
    # Definir cuotas
    if num_artistas > 0:
        cuota_artista = min(3, total_deseado // num_artistas)
    else:
        cuota_artista = 0
    
    if num_generos > 0:
        cuota_genero = max(2, (total_deseado - (cuota_artista * num_artistas)) // num_generos)
    else:
        cuota_genero = 0
    
    # 9. PRIORIDAD 1: Canciones de artistas favoritos (con límite por artista)
    for artista, canciones in canciones_por_artista.items():
        count = 0
        # Mezclar para variedad
        canciones_mezcladas = canciones.copy()
        random.shuffle(canciones_mezcladas)
        
        for c in canciones_mezcladas:
            if count >= cuota_artista:
                break
            if c["id"] not in ids_agregados and c["id"] not in ids_escuchadas:
                # Priorizar canciones que no son favoritas aún
                if c["id"] not in ids_favoritas:
                    recomendadas.append(c)
                    ids_agregados.add(c["id"])
                    count += 1
                elif count < cuota_artista // 2:
                    # Si ya es favorita, igual la incluimos pero con menor prioridad
                    recomendadas.append(c)
                    ids_agregados.add(c["id"])
                    count += 1
    
    # 10. PRIORIDAD 2: Canciones de géneros favoritos (balanceado)
    for genero, canciones in canciones_por_genero.items():
        count = 0
        canciones_mezcladas = canciones.copy()
        random.shuffle(canciones_mezcladas)
        
        for c in canciones_mezcladas:
            if count >= cuota_genero:
                break
            if c["id"] not in ids_agregados and c["id"] not in ids_escuchadas:
                recomendadas.append(c)
                ids_agregados.add(c["id"])
                count += 1
    
    # 11. PRIORIDAD 3: Rellenar con más canciones de géneros favoritos
    if len(recomendadas) < total_deseado - 5:
        for genero, canciones in canciones_por_genero.items():
            canciones_mezcladas = canciones.copy()
            random.shuffle(canciones_mezcladas)
            for c in canciones_mezcladas:
                if len(recomendadas) >= total_deseado:
                    break
                if c["id"] not in ids_agregados and c["id"] not in ids_escuchadas:
                    recomendadas.append(c)
                    ids_agregados.add(c["id"])
    
    # 12. PRIORIDAD 4: Canciones populares (último recurso)
    if len(recomendadas) < 10:
        populares = supabase.table("canciones")\
            .select("*")\
            .order("popularidad", desc=True)\
            .limit(30)\
            .execute().data or []
        
        for c in populares:
            if len(recomendadas) >= total_deseado:
                break
            if c["id"] not in ids_agregados and c["id"] not in ids_escuchadas:
                recomendadas.append(c)
                ids_agregados.add(c["id"])
    
    # 13. Mezclar final para mayor variedad (pero mantener prioridad)
    if len(recomendadas) > 5:
        primeras = recomendadas[:5]
        resto = recomendadas[5:]
        random.shuffle(resto)
        recomendadas = primeras + resto
    
    return recomendadas[:total_deseado]


# ─────────────────────────────────────────────
# GUARDAR INTERACCIÓN (versión profesional)
# ─────────────────────────────────────────────
def guardar_interaccion(supabase, user_id: str, cancion_id: int, es_favorito: bool = True):
    """
    Guarda o actualiza la interacción del usuario con una canción.
    No duplica registros y mantiene historial limpio.
    """
    # Verificar si ya existe la interacción
    existing = supabase.table("interacciones")\
        .select("id")\
        .eq("usuario_id", user_id)\
        .eq("cancion_id", cancion_id)\
        .execute().data
    
    if existing:
        # Actualizar si ya existe
        return supabase.table("interacciones")\
            .update({"es_favorito": es_favorito})\
            .eq("usuario_id", user_id)\
            .eq("cancion_id", cancion_id)\
            .execute()
    else:
        # Insertar nueva
        data = {
            "usuario_id": user_id,
            "cancion_id": cancion_id,
            "es_favorito": es_favorito,
        }
        return supabase.table("interacciones").insert(data).execute()


# ─────────────────────────────────────────────
# FUNCIONES ADICIONALES (para compatibilidad)
# ─────────────────────────────────────────────
def construir_arbol_decision(historial: list, canciones: list):
    """Árbol de decisión (mantenido para compatibilidad)"""
    return None

def predecir_con_arbol(modelo_tuple, canciones: list):
    """Predicción con árbol (mantenido para compatibilidad)"""
    return canciones

def recomendar_con_clustering(supabase, user_id: str, canciones: list):
    """Clustering (mantenido para compatibilidad)"""
    return []

def construir_lista_recursiva(canciones: list, resultado: list = None, vistas: set = None):
    """Construcción recursiva (mantenido para compatibilidad)"""
    if resultado is None:
        resultado = []
    if vistas is None:
        vistas = set()
    for c in canciones:
        if c["id"] not in vistas:
            resultado.append(c)
            vistas.add(c["id"])
    return resultado