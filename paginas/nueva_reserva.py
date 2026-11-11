"""Página Nueva reserva: huésped, fechas, habitaciones disponibles y confirmación."""

import datetime as dt

import oracledb
import pandas as pd
import streamlit as st

from config import CANALES, HOY
from conexion import consultar, transaccion
from interfaz import pesos, titulo
from reglas import edad, huesped_por_documento


def nueva_reserva():
    titulo("Nueva reserva", "Busca al huésped, elige fechas y la app te muestra solo las habitaciones que sirven.")

    # ---- Paso 1: huésped ----
    st.subheader("1. Huésped")
    doc = st.text_input("Número de documento", placeholder="Ej: 1036654321")
    if not doc.strip():
        st.caption("Si el huésped es nuevo, regístralo primero en la página Huéspedes.")
        return
    g = huesped_por_documento(doc)
    if g.empty:
        st.warning("No hay ningún huésped con ese documento. Regístralo en la página Huéspedes y vuelve aquí.")
        return
    if len(g) > 1:     # el mismo número con dos tipos de documento distintos (por ejemplo, CC y PAS)
        tipos = list(g["hd_tipo_documento"])
        g = g[g["hd_tipo_documento"] == st.radio("Hay más de un huésped con ese número. ¿Qué tipo de documento es?",
                                                 tipos, horizontal=True)]
    g = g.iloc[0]
    nacimiento = pd.to_datetime(g["hd_fecha_nacimiento"]).date() if pd.notna(g["hd_fecha_nacimiento"]) else None
    años = edad(nacimiento) if nacimiento else None
    st.success(f"**{g['hd_nombre']}** · {g['hd_tipo_documento']} {g['hd_documento']} · {g['hd_pais']}"
               + (f" · {años} años" if años is not None else ""))
    if años is not None and años < 18:     # el huésped debe ser mayor de edad
        st.error("El huésped es menor de edad. Solo un adulto puede hacer la reserva.")
        return

    # ---- Paso 2: fechas y personas ----
    st.subheader("2. Fechas y personas")
    c1, c2, c3 = st.columns(3)
    entrada = c1.date_input("Entrada", value=HOY, min_value=HOY, format="DD/MM/YYYY")
    salida = c2.date_input("Salida", value=entrada + dt.timedelta(days=1), min_value=HOY, format="DD/MM/YYYY")
    personas = c3.number_input("Personas", min_value=1, max_value=6, value=1)
    canal = st.selectbox("¿Por dónde llegó la reserva?", list(CANALES), format_func=CANALES.get,
                         index=3 if entrada == HOY else 0)
    noches = (salida - entrada).days
    if noches <= 0:
        st.error("La fecha de salida debe ser posterior a la de entrada.")
        return

    # La temporada la define la fecha de entrada
    temp = consultar("""SELECT tp_id_temporada, tp_nombre, tp_recargo FROM temporada
                        WHERE :e BETWEEN tp_fecha_inicio AND tp_fecha_fin""", {"e": entrada})
    if temp.empty:
        st.error("No hay una temporada creada para esa fecha de entrada. Créala en la página Temporadas.")
        return
    temp = temp.iloc[0]
    recargo = float(temp["tp_recargo"])
    st.caption(f"Temporada: **{temp['tp_nombre']}** · recargo {recargo:.0f} % · {noches} noche(s)")

    # ---- Paso 3: habitaciones disponibles (activas, con capacidad y sin cruces de fechas) ----
    st.subheader("3. Habitaciones disponibles")
    libres = consultar("""
        SELECT h.ha_id_habitacion, h.ha_numero, h.ha_tipo, h.ha_capacidad, h.ha_piso, h.ha_precio_noche
        FROM habitacion h
        WHERE h.ha_estado = 'activa'
          AND h.ha_capacidad >= :p
          AND NOT EXISTS (SELECT 1 FROM reserva r
                          WHERE r.re_id_habitacion = h.ha_id_habitacion
                            AND r.re_estado <> 'cancelada'
                            AND r.re_fecha_entrada < :s
                            AND r.re_fecha_salida  > :e)
        ORDER BY h.ha_precio_noche, h.ha_numero""", {"p": personas, "s": salida, "e": entrada})
    if libres.empty:
        st.warning("No hay habitaciones libres con esa capacidad en esas fechas. Prueba otras fechas o menos personas.")
        return
    # Valor total = precio × noches × (1 + recargo/100)
    libres["valor_total"] = (libres["ha_precio_noche"].astype(float) * noches * (1 + recargo / 100)).round(2)

    opciones = {f"{r.ha_numero} · {r.ha_tipo} · hasta {r.ha_capacidad} personas · piso {r.ha_piso} · {pesos(r.valor_total)}": r
                for r in libres.itertuples()}
    elegida = opciones[st.radio("Elige una habitación", list(opciones))]

    # ---- Paso 4: confirmar ----
    st.subheader("4. Confirmar")
    k = st.columns(4)
    k[0].metric("Habitación", elegida.ha_numero)
    k[1].metric("Precio por noche", pesos(elegida.ha_precio_noche))
    k[2].metric("Noches", noches)
    k[3].metric("Valor total", pesos(elegida.valor_total))

    if st.button("Confirmar reserva", type="primary"):
        try:
            with transaccion() as cur:
                # se vuelve a revisar justo antes de guardar, por si alguien la tomó mientras tanto
                cur.execute("""SELECT COUNT(*) FROM reserva
                               WHERE re_id_habitacion = :ha AND re_estado <> 'cancelada'
                                 AND re_fecha_entrada < :s AND re_fecha_salida > :e""",
                            {"ha": int(elegida.ha_id_habitacion), "s": salida, "e": entrada})
                if cur.fetchone()[0] > 0:
                    raise ValueError("La habitación se acaba de ocupar en esas fechas. Elige otra.")
                nuevo_id = cur.var(oracledb.NUMBER)
                cur.execute("""
                    INSERT INTO reserva (re_id_huesped, re_id_habitacion, re_id_temporada, re_fecha_reserva,
                                         re_fecha_entrada, re_fecha_salida, re_noches, re_num_personas,
                                         re_valor_total, re_estado, re_canal)
                    VALUES (:hu, :ha, :tp, :fr, :e, :s, :n, :p, :v, 'confirmada', :c)
                    RETURNING re_id_reserva INTO :nid""",
                    {"hu": int(g["hd_id_huesped"]), "ha": int(elegida.ha_id_habitacion),
                     "tp": int(temp["tp_id_temporada"]), "fr": HOY, "e": entrada, "s": salida,
                     "n": noches, "p": int(personas), "v": float(elegida.valor_total), "c": canal, "nid": nuevo_id})
                numero = int(nuevo_id.getvalue()[0])
            st.success(f"Reserva confirmada. Número de reserva: **{numero}**.")
        except ValueError as e:
            st.error(str(e))
        except oracledb.IntegrityError:
            st.error("Esa habitación ya tiene una reserva (aunque esté cancelada) con la misma fecha de entrada. "
                     "Elige otra habitación o cambia la fecha de entrada.")
        except oracledb.DatabaseError as e:
            st.error(f"Oracle rechazó la reserva: {e}")
