import streamlit as st
import os
import re
import json
from dotenv import load_dotenv
from supabase import create_client
import login_5 as login
import recomendaciones_3 as recomendaciones

# ── CONFIG ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Roafy Music",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# ── ESTILOS PROFESIONALES SPOTIFY ──────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #121212; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #000000; }
    h1, h2, h3, h4 { color: #FFFFFF !important; }
    div.stButton > button {
        background-color: #1DB954 !important;
        color: #000000 !important;
        border-radius: 500px !important;
        border: none !important;
        font-weight: 700 !important;
        padding: 8px 24px !important;
        transition: transform 0.1s;
    }
    div.stButton > button:hover {
        background-color: #1ed760 !important;
        transform: scale(1.03);
    }
    .song-card {
        background: #1e1e1e;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 8px;
        transition: background 0.2s;
    }
    .song-card:hover { background: #282828; }
    .song-title { font-size: 1rem; font-weight: 700; color: #FFFFFF; }
    .song-meta { font-size: 0.82rem; color: #b3b3b3; }
    .player-card {
        background: #181818;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 20px;
        border: 1px solid #282828;
    }
    hr { border-color: #282828 !important; }
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #121212; }
    ::-webkit-scrollbar-thumb { background: #535353; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ── EXTRAER VIDEO ID DE YOUTUBE ───────────────────────────────────────────────
def extraer_video_id(url):
    if not url:
        return None
    url = url.strip()
    patrones = [
        r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'youtu\.be/([a-zA-Z0-9_-]{11})',
        r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
    ]
    for patron in patrones:
        match = re.search(patron, url)
        if match:
            return match.group(1)
    return None

# ── COLA DE REPRODUCCIÓN ──────────────────────────────────────────────────────
def inicializar_cola():
    defaults = {
        "cola_reproduccion": [],
        "indice_actual": 0,
        "modo_aleatorio": False,
        "cola_inicializada": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def agregar_a_cola(cancion):
    ids_cola = [c["id"] for c in st.session_state.cola_reproduccion]
    if cancion and cancion["id"] not in ids_cola:
        st.session_state.cola_reproduccion.append(cancion)
        st.toast(f"🎵 Agregado: {cancion.get('titulo', '')}")

def cargar_cola_completa(canciones):
    """Carga toda una lista de canciones a la cola sin duplicar."""
    ids_existentes = {c["id"] for c in st.session_state.cola_reproduccion}
    agregadas = 0
    for c in canciones:
        if c["id"] not in ids_existentes:
            st.session_state.cola_reproduccion.append(c)
            ids_existentes.add(c["id"])
            agregadas += 1
    return agregadas

def limpiar_cola():
    st.session_state.cola_reproduccion  = []
    st.session_state.indice_actual       = 0
    st.session_state.cancion_actual      = None
    st.session_state.cola_inicializada   = False
    st.toast("🗑️ Cola limpiada")
    st.rerun()

# ── REPRODUCTOR CORREGIDO ─────────────────────────────────────────────────────
def mostrar_reproductor_avanzado():
    inicializar_cola()

    if not st.session_state.cancion_actual:
        st.info("🎵 Haz clic en ▶️ en una canción para empezar a reproducir")
        return

    c      = st.session_state.cancion_actual
    cola   = st.session_state.cola_reproduccion
    indice = st.session_state.indice_actual

    # Construir playlist completa — solo canciones con video_id válido
    playlist_data = []
    for cancion in cola:
        vid = extraer_video_id(cancion.get("url_youtube", ""))
        if vid:  # solo incluir si el link es válido
            playlist_data.append({
                "videoId": vid,
                "titulo":  cancion.get("titulo", ""),
                "artista": cancion.get("artista", ""),
                "genero":  cancion.get("genero", ""),
            })

    # Encontrar el índice correcto dentro de playlist_data
    video_id_actual = extraer_video_id(c.get("url_youtube", ""))
    indice_js = 0
    for i, item in enumerate(playlist_data):
        if item["videoId"] == video_id_actual:
            indice_js = i
            break

    playlist_json  = json.dumps(playlist_data, ensure_ascii=False)
    modo_aleatorio = str(st.session_state.modo_aleatorio).lower()

    st.markdown("---")
    st.markdown("## 🎬 Reproductor")

    col_video, col_info = st.columns([2, 1])

    with col_video:
        iframe_html = f"""
        <html><body style="margin:0;padding:0;background:#121212;font-family:sans-serif;">

        <div id="player" style="border-radius:12px;overflow:hidden;"></div>

        <div style="margin-top:10px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
            <button onclick="anteriorCancion()"
                style="background:#1DB954;color:#000;border:none;padding:8px 20px;
                       border-radius:500px;font-weight:700;cursor:pointer;font-size:16px;">⏮️ Anterior</button>
            <button onclick="siguienteCancion()"
                style="background:#1DB954;color:#000;border:none;padding:8px 20px;
                       border-radius:500px;font-weight:700;cursor:pointer;font-size:16px;">⏭️ Siguiente</button>
            <span id="badge_idx"
                style="color:#1DB954;font-weight:700;font-size:14px;margin-left:8px;">
                {indice_js + 1} / {len(playlist_data)}
            </span>
        </div>

        <div style="margin-top:8px;padding:10px;background:#1e1e1e;border-radius:8px;">
            <div id="titulo_actual" style="color:#FFFFFF;font-weight:700;font-size:15px;">
                {c.get('titulo', '')}
            </div>
            <div id="artista_actual" style="color:#b3b3b3;font-size:13px;margin-top:4px;">
                {c.get('artista', '')} · {c.get('genero', '')}
            </div>
        </div>

        <script>
            var playlist     = {playlist_json};
            var currentIndex = {indice_js};
            var modoAleatorio = {modo_aleatorio};
            var player;
            var playerReady  = false;

            var tag = document.createElement('script');
            tag.src = "https://www.youtube.com/iframe_api";
            document.head.appendChild(tag);

            function onYouTubeIframeAPIReady() {{
                if (!playlist.length) return;
                var firstId = playlist[currentIndex].videoId;
                player = new YT.Player('player', {{
                    height: '315',
                    width:  '100%',
                    videoId: firstId,
                    playerVars: {{
                        rel:            0,
                        modestbranding: 1,
                        autoplay:       1,
                    }},
                    events: {{
                        onReady:       function(e) {{ playerReady = true; }},
                        onStateChange: onStateChange,
                        onError:       onError,
                    }}
                }});
            }}

            function onStateChange(e) {{
                // 0 = terminado → avanzar automáticamente
                if (e.data === 0) {{
                    siguienteCancion();
                }}
            }}

            // Si hay error en el video (eliminado, bloqueado, etc.) saltar al siguiente
            function onError(e) {{
                console.warn('Error en video, saltando. Código:', e.data);
                setTimeout(function() {{ siguienteCancion(); }}, 1500);
            }}

            function siguienteCancion() {{
                if (playlist.length === 0) return;
                if (modoAleatorio) {{
                    currentIndex = Math.floor(Math.random() * playlist.length);
                }} else {{
                    currentIndex = (currentIndex + 1) % playlist.length;
                }}
                cargarCancion(currentIndex);
            }}

            function anteriorCancion() {{
                if (playlist.length === 0) return;
                currentIndex = (currentIndex - 1 + playlist.length) % playlist.length;
                cargarCancion(currentIndex);
            }}

            function cargarCancion(idx) {{
                if (!playerReady) return;
                var item = playlist[idx];
                if (!item || !item.videoId) {{
                    siguienteCancion();
                    return;
                }}
                currentIndex = idx;
                player.loadVideoById(item.videoId);
                actualizarInfo(item, idx);
            }}

            function actualizarInfo(item, idx) {{
                var t = document.getElementById('titulo_actual');
                var a = document.getElementById('artista_actual');
                var b = document.getElementById('badge_idx');
                if (t) t.innerText = item.titulo;
                if (a) a.innerText = item.artista + ' · ' + item.genero;
                if (b) b.innerText = (idx + 1) + ' / ' + playlist.length;
            }}
        </script>
        </body></html>
        """
        st.components.v1.html(iframe_html, height=460)

    with col_info:
        st.markdown(f"""
        <div class='player-card'>
            <p style='color:#1DB954;font-size:0.8rem;margin:0'>▶ REPRODUCIENDO AHORA</p>
            <h3 style='color:#FFFFFF;margin:8px 0 4px'>{c.get('titulo', '')}</h3>
            <p style='color:#b3b3b3;margin:0'>{c.get('artista', '')}</p>
            <p style='color:#888;font-size:0.85rem;margin:4px 0'>🎸 {c.get('genero', '')}</p>
            <p style='color:#555;font-size:0.75rem;margin:8px 0 0'>
                📋 {len(playlist_data)} canciones en cola con video válido
            </p>
        </div>
        """, unsafe_allow_html=True)

        b1, b2 = st.columns(2)
        with b1:
            icono_ale = "🔀✅" if st.session_state.modo_aleatorio else "🔀"
            if st.button(icono_ale, use_container_width=True, key="btn_ale"):
                st.session_state.modo_aleatorio = not st.session_state.modo_aleatorio
                st.rerun()
        with b2:
            if st.button("🗑️ Limpiar", use_container_width=True, key="btn_lim"):
                limpiar_cola()

        total  = len(cola)
        actual = indice + 1 if total > 0 else 0
        st.markdown(
            f"<p style='text-align:center;color:#1DB954;margin-top:8px'>📋 {actual}/{total} en cola</p>",
            unsafe_allow_html=True
        )

        # Mostrar advertencia si hay canciones sin link válido
        sin_link = total - len(playlist_data)
        if sin_link > 0:
            st.warning(f"⚠️ {sin_link} canciones sin link de YouTube válido fueron omitidas.")

    # Cola de reproducción visual (compacta)
    if cola:
        with st.expander(f"📋 Ver cola completa ({len(cola)} canciones)", expanded=False):
            for i, cancion in enumerate(cola):
                vid_ok = bool(extraer_video_id(cancion.get("url_youtube", "")))
                c1, c2, c3 = st.columns([0.5, 8, 1])
                with c1:
                    if i == indice:
                        st.markdown("<p style='color:#1DB954;font-weight:bold;margin:0'>▶</p>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<p style='color:#888;margin:0'>{i+1}</p>", unsafe_allow_html=True)
                with c2:
                    color  = "#1DB954" if i == indice else "#FFFFFF"
                    estado = "" if vid_ok else " ⚠️"
                    st.markdown(
                        f"<span style='color:{color}'><b>{cancion.get('titulo')}</b>{estado} — {cancion.get('artista')}</span>",
                        unsafe_allow_html=True
                    )
                with c3:
                    if st.button("▶", key=f"cola_{i}"):
                        st.session_state.indice_actual  = i
                        st.session_state.cancion_actual = cancion
                        recomendaciones.guardar_interaccion(
                            supabase, st.session_state.user.id, cancion["id"], es_favorito=False
                        )
                        st.rerun()

# ── ESTADOS ─────────────────────────────────────────────────────────────────
for k, v in [("logueado", False), ("user", None),
             ("cancion_actual", None), ("favoritos_ids", set()),
             ("pagina", "inicio"), ("cola_inicializada", False)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── TARJETA DE CANCIÓN ────────────────────────────────────────────────────────
def tarjeta_cancion(cancion, idx, mostrar_fav=True):
    cid    = cancion.get("id")
    es_fav = cid in st.session_state.favoritos_ids
    vid_ok = bool(extraer_video_id(cancion.get("url_youtube", "")))

    col_info, col_play, col_queue, col_fav = st.columns([5, 1, 1, 1])
    with col_info:
        estado = "" if vid_ok else " ⚠️"
        st.markdown(f"""
        <div class='song-card'>
            <div class='song-title'>🎵 {cancion.get('titulo', '')}{estado}</div>
            <div class='song-meta'>{cancion.get('artista', '')} · {cancion.get('genero', '')}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_play:
        if st.button("▶", key=f"play_{cid}_{idx}"):
            st.session_state.cancion_actual = cancion
            agregar_a_cola(cancion)
            recomendaciones.guardar_interaccion(supabase, st.session_state.user.id, cid, es_favorito=False)
            st.rerun()
    with col_queue:
        if st.button("📋", key=f"queue_{cid}_{idx}", help="Agregar a cola"):
            agregar_a_cola(cancion)
            st.rerun()
    if mostrar_fav:
        with col_fav:
            icono = "❤️" if es_fav else "🤍"
            if st.button(icono, key=f"fav_{cid}_{idx}"):
                if not es_fav:
                    recomendaciones.guardar_interaccion(supabase, st.session_state.user.id, cid, es_favorito=True)
                    st.session_state.favoritos_ids.add(cid)
                    st.toast("❤️ Añadido a favoritos")
                else:
                    recomendaciones.guardar_interaccion(supabase, st.session_state.user.id, cid, es_favorito=False)
                    st.session_state.favoritos_ids.discard(cid)
                    st.toast("❌ Eliminado de favoritos")
                st.rerun()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
def mostrar_sidebar():
    with st.sidebar:
        col_logo, col_titulo = st.columns([1, 3])
        with col_logo:
            try:
                st.image("logo.png", width=45)
            except Exception:
                st.markdown("🎵")
        with col_titulo:
            st.markdown("### **Roafy**")

        st.markdown("---")
        if st.button("🏠 Inicio",        use_container_width=True): st.session_state.pagina = "inicio";    st.rerun()
        if st.button("🔍 Buscar",        use_container_width=True): st.session_state.pagina = "buscar";    st.rerun()
        if st.button("❤️ Mis Favoritos", use_container_width=True): st.session_state.pagina = "favoritos"; st.rerun()
        if st.button("📊 Mi Perfil",     use_container_width=True): st.session_state.pagina = "perfil";    st.rerun()

        st.markdown("---")
        st.markdown("### 🎧 Variedad Musical")
        for g in ["Rock", "Pop", "Urbano", "Tropical", "Electrónica", "Regional"]:
            if st.button(f"🎸 {g}", use_container_width=True, key=f"gen_{g}"):
                st.session_state.pagina = "buscar"
                st.rerun()

        st.markdown("---")
        u      = st.session_state.user
        nombre = u.user_metadata.get("nombre", u.email) if u and u.user_metadata else (u.email if u else "")
        st.markdown(f"<p style='color:#b3b3b3;font-size:0.8rem'>👤 {nombre}</p>", unsafe_allow_html=True)

        if st.button("🚪 Cerrar sesión", use_container_width=True):
            for k in ["logueado", "user", "cancion_actual", "cola_reproduccion",
                      "favoritos_ids", "cola_inicializada"]:
                if k == "logueado":            st.session_state[k] = False
                elif k == "cola_reproduccion": st.session_state[k] = []
                elif k == "favoritos_ids":     st.session_state[k] = set()
                elif k == "cola_inicializada": st.session_state[k] = False
                else:                          st.session_state[k] = None
            st.rerun()

# ── PÁGINAS ───────────────────────────────────────────────────────────────────
def pagina_inicio():
    st.markdown("## 🏠 Para ti")

    with st.spinner("🎵 Calculando recomendaciones..."):
        canciones = recomendaciones.obtener_musica_recomendada(supabase, st.session_state.user.id)

    if not canciones:
        # Fallback: traer TODAS las canciones de la BD
        canciones = supabase.table("canciones").select("*").execute().data or []

    # ── AUTO-CARGAR toda la lista a la cola al entrar por primera vez ──
    # Así el reproductor tiene todas las canciones disponibles
    if not st.session_state.cola_inicializada and canciones:
        cargar_cola_completa(canciones)
        st.session_state.cola_inicializada = True
        if not st.session_state.cancion_actual and st.session_state.cola_reproduccion:
            st.session_state.cancion_actual = st.session_state.cola_reproduccion[0]
            st.session_state.indice_actual  = 0

    mostrar_reproductor_avanzado()

    st.markdown(f"<p style='color:#b3b3b3'>🎯 {len(canciones)} canciones para ti</p>", unsafe_allow_html=True)

    col_acc1, col_acc2 = st.columns(2)
    with col_acc1:
        if st.button("▶️ Reproducir todo desde el inicio", use_container_width=True):
            if canciones:
                st.session_state.cola_reproduccion = []
                st.session_state.cola_inicializada = False
                cargar_cola_completa(canciones)
                st.session_state.cola_inicializada = True
                st.session_state.cancion_actual    = canciones[0]
                st.session_state.indice_actual     = 0
                st.rerun()
    with col_acc2:
        if st.button("🔀 Reproducir en aleatorio", use_container_width=True):
            if canciones:
                import random
                mezcladas = canciones.copy()
                random.shuffle(mezcladas)
                st.session_state.cola_reproduccion = []
                st.session_state.cola_inicializada = False
                cargar_cola_completa(mezcladas)
                st.session_state.cola_inicializada = True
                st.session_state.cancion_actual    = mezcladas[0]
                st.session_state.indice_actual     = 0
                st.rerun()

    for i, c in enumerate(canciones):
        tarjeta_cancion(c, i)


def pagina_buscar():
    st.markdown("## 🔍 Buscar Música")

    col1, col2 = st.columns(2)
    with col1:
        genero_filtro = st.selectbox("🎸 Género", ["Todos", "Electrónica", "Pop", "Regional", "Rock", "Tropical", "Urbano"])
    with col2:
        orden = st.selectbox("📊 Ordenar por", ["Título", "Artista"])

    query = st.text_input("🔎", placeholder="Busca por título, artista o género...")

    todos = supabase.table("canciones").select("*").execute().data or []

    if query:
        q = query.lower()
        todos = [c for c in todos if q in c.get("titulo", "").lower()
                 or q in c.get("artista", "").lower()
                 or q in c.get("genero", "").lower()]
    if genero_filtro != "Todos":
        todos = [c for c in todos if c.get("genero") == genero_filtro]
    if orden == "Título":
        todos = sorted(todos, key=lambda x: x.get("titulo", ""))
    elif orden == "Artista":
        todos = sorted(todos, key=lambda x: x.get("artista", ""))

    st.markdown(f"<p style='color:#b3b3b3'>📀 {len(todos)} canciones</p>", unsafe_allow_html=True)

    # Botón para agregar todos los resultados a la cola
    if todos and st.button(f"📋 Agregar los {len(todos)} resultados a la cola", use_container_width=True):
        agregadas = cargar_cola_completa(todos)
        st.toast(f"✅ {agregadas} canciones nuevas agregadas a la cola")
        st.rerun()

    mostrar_reproductor_avanzado()

    for i, c in enumerate(todos):
        tarjeta_cancion(c, f"bus_{i}")


def pagina_favoritos():
    st.markdown("## ❤️ Mis Favoritos")
    mostrar_reproductor_avanzado()

    inter = supabase.table("interacciones")\
        .select("cancion_id")\
        .eq("usuario_id", st.session_state.user.id)\
        .eq("es_favorito", True).execute().data or []

    ids_fav = list({r["cancion_id"] for r in inter})
    st.session_state.favoritos_ids = set(ids_fav)

    if not ids_fav:
        st.info("💖 Aún no tienes favoritos. ¡Dale ❤️ a las canciones que te gusten!")
        return

    canciones = supabase.table("canciones").select("*").in_("id", ids_fav).execute().data or []
    st.markdown(f"<p style='color:#b3b3b3'>🎵 {len(canciones)} canciones favoritas</p>", unsafe_allow_html=True)

    if canciones and st.button("▶️ Reproducir solo favoritos", use_container_width=True):
        st.session_state.cola_reproduccion = []
        st.session_state.cola_inicializada = False
        cargar_cola_completa(canciones)
        st.session_state.cola_inicializada = True
        st.session_state.cancion_actual    = canciones[0]
        st.session_state.indice_actual     = 0
        st.rerun()

    for i, c in enumerate(canciones):
        tarjeta_cancion(c, f"fav_{i}", mostrar_fav=False)


def pagina_perfil():
    st.markdown("## 📊 Mi Perfil Musical")
    u      = st.session_state.user
    nombre = u.user_metadata.get("nombre", "Usuario") if u and u.user_metadata else "Usuario"

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div style='background:#1e1e1e;padding:20px;border-radius:12px'>
            <h3>👤 {nombre}</h3>
            <p style='color:#b3b3b3'>{u.email}</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        inter = supabase.table("interacciones").select("id").eq("usuario_id", u.id).execute().data or []
        favs  = supabase.table("interacciones").select("id").eq("usuario_id", u.id).eq("es_favorito", True).execute().data or []
        pref  = supabase.table("preferencias_usuario").select("*").eq("usuario_id", u.id).execute().data or []
        st.markdown(f"""
        <div style='background:#1e1e1e;padding:20px;border-radius:12px'>
            <h4 style='color:#1DB954'>📈 Tu actividad</h4>
            <p>🎵 Escuchadas: <b>{len(inter)}</b></p>
            <p>❤️ Favoritos: <b>{len(favs)}</b></p>
            <p>🎸 Género: <b>{pref[0]['genero_favorito'] if pref else 'No definido'}</b></p>
            <p>🌟 Artista: <b>{pref[0]['artista_favorito'] if pref else 'No definido'}</b></p>
        </div>
        """, unsafe_allow_html=True)

# ── MAIN ──────────────────────────────────────────────────────────────────────
if not st.session_state.logueado:
    login.mostrar_login(supabase)
else:
    if not st.session_state.favoritos_ids:
        try:
            inter = supabase.table("interacciones")\
                .select("cancion_id")\
                .eq("usuario_id", st.session_state.user.id)\
                .eq("es_favorito", True).execute().data or []
            st.session_state.favoritos_ids = {r["cancion_id"] for r in inter}
        except Exception:
            pass

    inicializar_cola()
    mostrar_sidebar()

    pagina = st.session_state.pagina
    if   pagina == "inicio":    pagina_inicio()
    elif pagina == "buscar":    pagina_buscar()
    elif pagina == "favoritos": pagina_favoritos()
    elif pagina == "perfil":    pagina_perfil()
