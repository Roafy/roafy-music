import streamlit as st

# TUS 6 GENEROS EXACTOS (COMO ESTÁN EN LA BD)
GENEROS = ["Electrónica", "Pop", "Regional / Folclore", "Rock", "Tropical", "Urbano"]

def _barra_progreso(paso: int):
    pasos = ["👤 Tu cuenta", "🎵 Tus generos", "🎶 Tus canciones"]
    cols = st.columns(3)
    for i, (col, nombre) in enumerate(zip(cols, pasos)):
        if i < paso:
            col.markdown(f"<div style='text-align:center;color:#1DB954;font-weight:bold'>✅ {nombre}</div>", unsafe_allow_html=True)
        elif i == paso:
            col.markdown(f"<div style='text-align:center;color:#FFFFFF;font-weight:bold;border-bottom:2px solid #1DB954'>{nombre}</div>", unsafe_allow_html=True)
        else:
            col.markdown(f"<div style='text-align:center;color:#888'>{nombre}</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

def mostrar_login(supabase):
    # Inicializar estados
    for k, v in [("paso_registro", 0), ("temp_user_id", None),
                 ("temp_generos", []), ("canciones_paso3", []),
                 ("temp_email", ""), ("temp_password", ""),
                 ("artistas_seleccionados", [])]:  # 👈 Ahora es una lista
        if k not in st.session_state:
            st.session_state[k] = v

    if st.session_state.paso_registro == 0:
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            st.markdown("""
                <div style='text-align:center;margin-bottom:30px'>
                    <h1 style='color:#1DB954;font-size:3rem'>🎵 Roafy</h1>
                    <p style='color:#aaa'>Tu musica, tu mundo</p>
                </div>
            """, unsafe_allow_html=True)

            tab1, tab2 = st.tabs(["🔑 Iniciar Sesion", "📝 Registrarse"])

            with tab1:
                email = st.text_input("Correo electronico", placeholder="tu@email.com", key="l_email")
                password = st.text_input("Contraseña", type="password", key="l_pass")
                if st.button("Ingresar", use_container_width=True, key="btn_login"):
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        if res.user:
                            st.session_state.user = res.user
                            st.session_state.user_id = res.user.id
                            st.session_state.logueado = True
                            st.rerun()
                        else:
                            st.error("Correo o contraseña incorrectos.")
                    except Exception as e:
                        st.error(f"Error al iniciar sesion: {e}")

            with tab2:
                nombre = st.text_input("Nombre completo", placeholder="Tu nombre", key="r_nombre")
                new_email = st.text_input("Correo electronico", placeholder="tu@email.com", key="r_email")
                new_pass = st.text_input("Contraseña", type="password", placeholder="Minimo 6 caracteres", key="r_pass")
                if st.button("Crear cuenta", use_container_width=True, key="btn_registro"):
                    if not nombre or not new_email or not new_pass:
                        st.warning("Completa todos los campos.")
                    elif len(new_pass) < 6:
                        st.warning("La contraseña debe tener al menos 6 caracteres.")
                    else:
                        try:
                            res = supabase.auth.sign_up({
                                "email": new_email,
                                "password": new_pass,
                                "options": {"data": {"nombre": nombre}}
                            })
                            if res.user:
                                st.session_state.temp_user_id = res.user.id
                                st.session_state.temp_email = new_email
                                st.session_state.temp_password = new_pass
                                st.session_state.paso_registro = 1
                                st.rerun()
                            else:
                                st.error("No se pudo crear la cuenta.")
                        except Exception as e:
                            st.error(f"Error al crear cuenta: {e}")

    elif st.session_state.paso_registro == 1:
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            _barra_progreso(1)
            st.markdown("## 🎵 ¿Que musica te gusta?")
            st.caption("Selecciona uno o mas generos favoritos")

            seleccionados = []
            cols = st.columns(2)
            for i, g in enumerate(GENEROS):
                with cols[i % 2]:
                    checked = st.checkbox(g, key=f"gen_{g}", value=(g in st.session_state.temp_generos))
                    if checked:
                        seleccionados.append(g)

            st.session_state.temp_generos = seleccionados

            # Mostrar artistas según género seleccionado
            artistas_seleccionados = st.session_state.artistas_seleccionados.copy()
            
            if seleccionados:
                st.markdown("### 🎤 Selecciona tus artistas favoritos (puedes elegir varios):")
                
                for genero in seleccionados:
                    st.markdown(f"**{genero}:**")
                    result = supabase.table("canciones")\
                        .select("artista")\
                        .eq("genero", genero)\
                        .execute().data or []
                    artistas_disponibles = list(set([a["artista"] for a in result if a.get("artista")]))
                    
                    if artistas_disponibles:
                        cols_artistas = st.columns(2)
                        for i, art in enumerate(artistas_disponibles):
                            with cols_artistas[i % 2]:
                                if st.checkbox(art, key=f"art_{genero}_{art}", value=(art in artistas_seleccionados)):
                                    if art not in artistas_seleccionados:
                                        artistas_seleccionados.append(art)
                                    elif art in artistas_seleccionados and not st.session_state.get(f"art_{genero}_{art}", False):
                                        artistas_seleccionados.remove(art)
                    else:
                        st.info(f"No hay artistas disponibles para {genero}")
                
                st.session_state.artistas_seleccionados = artistas_seleccionados
                
                if artistas_seleccionados:
                    st.success(f"✅ Artistas seleccionados: {', '.join(artistas_seleccionados)}")
            else:
                st.info("Selecciona un genero primero para ver los artistas disponibles")

            if st.button("Continuar →", use_container_width=True, key="btn_paso2"):
                if not seleccionados:
                    st.warning("Selecciona al menos un genero.")
                elif not artistas_seleccionados:
                    st.warning("Selecciona al menos un artista favorito.")
                else:
                    generos_str = ", ".join(seleccionados)
                    artistas_str = ", ".join(artistas_seleccionados)
                    try:
                        supabase.table("preferencias_usuario").upsert({
                            "usuario_id": st.session_state.temp_user_id,
                            "genero_favorito": generos_str,
                            "artista_favorito": artistas_str
                        }).execute()
                    except Exception as e:
                        st.warning(f"Error al guardar preferencias: {e}")
                    
                    canciones_muestra = supabase.table("canciones")\
                        .select("*")\
                        .eq("genero", seleccionados[0])\
                        .limit(3).execute().data
                    if not canciones_muestra:
                        canciones_muestra = supabase.table("canciones")\
                            .select("*")\
                            .order("popularidad", desc=True)\
                            .limit(3).execute().data
                    st.session_state.canciones_paso3 = canciones_muestra
                    st.session_state.paso_registro = 2
                    st.rerun()

    elif st.session_state.paso_registro == 2:
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            _barra_progreso(2)
            st.markdown("## 🎶 ¿Te gustan estas canciones?")
            st.caption("Marca las que te gusten para que Roafy aprenda tu gusto")

            canciones = st.session_state.canciones_paso3 or []
            gustos = []
            for cancion in canciones:
                with st.container():
                    st.markdown(f"**{cancion.get('titulo')}** — {cancion.get('artista')}")
                    st.caption(f"Genero: {cancion.get('genero')}")
                    if st.checkbox("❤️ Me gusta esta", key=f"like_{cancion.get('id')}"):
                        gustos.append(cancion.get("id"))
                    st.divider()

            if st.button("¡Empezar a escuchar! 🎧", use_container_width=True, key="btn_paso3"):
                for cid in gustos:
                    try:
                        supabase.table("interacciones").insert({
                            "usuario_id": st.session_state.temp_user_id,
                            "cancion_id": cid,
                            "es_favorito": True
                        }).execute()
                    except Exception as e:
                        st.warning(f"Error al guardar interaccion: {e}")
                
                # LOGIN AUTOMATICO despues del registro
                try:
                    res = supabase.auth.sign_in_with_password({
                        "email": st.session_state.temp_email,
                        "password": st.session_state.temp_password
                    })
                    if res.user:
                        st.session_state.user = res.user
                        st.session_state.user_id = res.user.id
                        st.session_state.logueado = True
                        st.session_state.paso_registro = 0
                        st.rerun()
                except Exception as e:
                    st.error(f"Error al iniciar sesion automaticamente: {e}")
                    st.session_state.paso_registro = 0
                    st.success("¡Registro completo! Ahora inicia sesion con tu cuenta.")
                    st.rerun()