"""Página Reservas: filtros, check-in, check-out, cancelación, modificación y calificación."""

import datetime as dt

import oracledb
import pandas as pd
import streamlit as st

from config import ESTADOS, HOY
from conexion import consultar, escribir, mensaje_error, transaccion
from interfaz import pesos, tabla, titulo
from reglas import hacer_checkin, hacer_checkout, limpiar_documento


def reservas():
    titulo("Reservas", "Busca una reserva y gestiónala: check-in, check-out, cambios de fechas o habitación y cancelación.")

    c1, c2, c3, c4 = st.columns([2, 2, 1, 2])
    rango = c1.date_input("Entrada entre", value=(HOY - dt.timedelta(days=30), HOY + dt.timedelta(days=60)),
                          format="DD/MM/YYYY")
    estados = c2.multiselect("Estado", ESTADOS, default=["confirmada", "en_curso"])
    hab = c3.text_input("Habitación", placeholder="402")
    q = c4.text_input("Huésped (nombre o documento)")
    if not isinstance(rango, tuple) or len(rango) != 2:
        st.caption("Elige la fecha final del rango.")
        return

    sql = """SELECT r.re_id_reserva AS reserva, hu.hd_nombre AS huesped, hu.hd_documento AS documento,
                    h.ha_numero AS habitacion, h.ha_tipo AS tipo, t.tp_nombre AS temporada,
                    r.re_fecha_entrada AS entrada, r.re_fecha_salida AS salida, r.re_noches AS noches,
                    r.re_num_personas AS personas, r.re_valor_total AS valor, r.re_estado AS estado,
                    r.re_canal AS canal, r.re_calificacion AS calificacion,
                    r.re_hora_checkin AS checkin, r.re_hora_checkout AS checkout
             FROM reserva r
             JOIN huesped hu   ON hu.hd_id_huesped = r.re_id_huesped
             JOIN habitacion h ON h.ha_id_habitacion = r.re_id_habitacion
             JOIN temporada t  ON t.tp_id_temporada = r.re_id_temporada
             WHERE r.re_fecha_entrada BETWEEN :desde AND :hasta
               AND (:estados IS NULL OR INSTR(:estados, ',' || r.re_estado || ',') > 0)
               AND (:hab IS NULL OR h.ha_numero = :hab)
               AND (:q IS NULL OR hu.hd_documento = :q OR UPPER(hu.hd_nombre) LIKE UPPER(:ql))
             ORDER BY r.re_fecha_entrada DESC
             FETCH FIRST 500 ROWS ONLY"""
    # Los filtros vacíos se envían como NULL y la condición correspondiente no filtra nada.
    params = {"desde": rango[0], "hasta": rango[1],
              "estados": ("," + ",".join(estados) + ",") if estados else None,
              "hab": hab.strip() or None,
              "q": limpiar_documento(q) or None, "ql": f"%{q.strip()}%"}
    df = consultar(sql, params)

    k = st.columns(3)
    k[0].metric("Reservas encontradas", len(df))
    k[1].metric("Noches", int(df["noches"].sum()) if len(df) else 0)
    k[2].metric("Valor (sin canceladas)", pesos(df.loc[df["estado"] != "cancelada", "valor"].sum() if len(df) else 0))
    if df.empty:
        st.info("Ninguna reserva cumple esos filtros.")
    else:
        tabla(df, dinero=["valor"], fechas=["entrada", "salida"], horas=["checkin", "checkout"], exportar="reservas")

    st.subheader("Gestionar una reserva")
    num = st.number_input("Número de reserva", min_value=1, step=1, value=None, placeholder="Ej: 2581")
    if num is None:
        return
    r = consultar("""SELECT r.re_id_reserva, r.re_estado, r.re_fecha_entrada, r.re_fecha_salida, r.re_num_personas,
                            r.re_id_habitacion, r.re_valor_total, r.re_calificacion, r.re_hora_checkin,
                            r.re_hora_checkout, hu.hd_nombre, h.ha_numero
                     FROM reserva r JOIN huesped hu ON hu.hd_id_huesped = r.re_id_huesped
                     JOIN habitacion h ON h.ha_id_habitacion = r.re_id_habitacion
                     WHERE r.re_id_reserva = :id""", {"id": int(num)})
    if r.empty:
        st.warning("No existe una reserva con ese número.")
        return
    r = r.iloc[0]
    rid = int(num)
    sal = pd.to_datetime(r["re_fecha_salida"]).date()
    ent = pd.to_datetime(r["re_fecha_entrada"]).date()
    estado = r["re_estado"]
    hora = lambda v: pd.to_datetime(v).strftime("%d/%m/%Y %H:%M") if pd.notna(v) else "—"
    st.write(f"**{r['hd_nombre']}**, habitación {r['ha_numero']}, del {ent:%d/%m/%Y} al {sal:%d/%m/%Y}. "
             f"Estado: **{estado}**.")
    if estado in ("en_curso", "finalizada"):
        st.caption(f"Check-in: {hora(r['re_hora_checkin'])}   Check-out: {hora(r['re_hora_checkout'])}")

    if estado == "cancelada":
        st.caption("Las reservas canceladas no cambian de estado.")
        return

    if estado == "finalizada":
        if pd.notna(r["re_calificacion"]):
            st.caption(f"Calificación del huésped: {int(r['re_calificacion'])} / 5")
            return
        nota = st.select_slider("Calificación del huésped", options=[1, 2, 3, 4, 5], value=4)
        if st.button("Guardar calificación", type="primary"):
            escribir("""UPDATE reserva SET re_calificacion = :c
                        WHERE re_id_reserva = :id AND re_estado = 'finalizada' AND re_calificacion IS NULL""",
                     {"c": nota, "id": rid}, f"Calificación {nota} / 5 guardada.",
                     "La reserva ya tenía calificación o no está finalizada.")
        return

    if estado == "en_curso":
        if sal > HOY:
            st.info(f"El huésped tiene la habitación hasta el {sal:%d/%m}. Si sale antes, la estadía se cobra completa.")
        st.button("Registrar check-out", type="primary", on_click=hacer_checkout, args=(rid,))
        return

    # ---- confirmada: check-in, cancelar o modificar ----
    b1, b2 = st.columns(2)
    puede_entrar = ent <= HOY < sal
    b1.button("Registrar check-in", type="primary", disabled=not puede_entrar, on_click=hacer_checkin, args=(rid,),
              help=None if puede_entrar else f"El check-in se habilita desde el {ent:%d/%m/%Y}.")
    if b2.button("Cancelar reserva"):
        escribir("UPDATE reserva SET re_estado = 'cancelada' WHERE re_id_reserva = :id AND re_estado = 'confirmada'",
                 {"id": rid}, f"Reserva {rid} cancelada.", "La reserva ya no estaba confirmada.")
        return

    with st.expander("Modificar fechas, personas o habitación"):
        modificar_reserva(rid, ent, sal, int(r["re_num_personas"]), int(r["re_id_habitacion"]), float(r["re_valor_total"]))


def modificar_reserva(rid, ent, sal, personas, hab_actual, valor_actual):
    """Cambia una reserva confirmada volviendo a aplicar las reglas: disponibilidad, capacidad, temporada y valor."""
    c1, c2, c3 = st.columns(3)
    n_ent = c1.date_input("Nueva entrada", value=max(ent, HOY), min_value=HOY, format="DD/MM/YYYY", key=f"m_ent_{rid}")
    n_sal = c2.date_input("Nueva salida", value=max(sal, n_ent + dt.timedelta(days=1)), format="DD/MM/YYYY",
                          key=f"m_sal_{rid}")
    n_per = c3.number_input("Personas", min_value=1, max_value=6, value=personas, key=f"m_per_{rid}")
    noches = (n_sal - n_ent).days
    if noches <= 0:
        st.error("La fecha de salida debe ser posterior a la de entrada.")
        return
    temp = consultar("""SELECT tp_id_temporada, tp_nombre, tp_recargo FROM temporada
                        WHERE :e BETWEEN tp_fecha_inicio AND tp_fecha_fin""", {"e": n_ent})
    if temp.empty:
        st.error("No hay una temporada creada para esa fecha de entrada. Créala en la página Temporadas.")
        return
    temp = temp.iloc[0]
    recargo = float(temp["tp_recargo"])
    # habitaciones libres en las nuevas fechas, sin contar esta misma reserva
    libres = consultar("""
        SELECT h.ha_id_habitacion, h.ha_numero, h.ha_tipo, h.ha_capacidad, h.ha_precio_noche
        FROM habitacion h
        WHERE h.ha_estado = 'activa' AND h.ha_capacidad >= :p
          AND NOT EXISTS (SELECT 1 FROM reserva r
                          WHERE r.re_id_habitacion = h.ha_id_habitacion AND r.re_estado <> 'cancelada'
                            AND r.re_id_reserva <> :id
                            AND r.re_fecha_entrada < :s AND r.re_fecha_salida > :e)
        ORDER BY CASE WHEN h.ha_id_habitacion = :actual THEN 0 ELSE 1 END, h.ha_precio_noche""",
        {"p": n_per, "id": rid, "s": n_sal, "e": n_ent, "actual": hab_actual})
    if libres.empty:
        st.warning("No hay habitaciones libres con esa capacidad en esas fechas.")
        return
    libres["valor_total"] = (libres["ha_precio_noche"].astype(float) * noches * (1 + recargo / 100)).round(2)
    opciones = {f"{x.ha_numero} ({x.ha_tipo}, hasta {x.ha_capacidad}): {pesos(x.valor_total)}"
                + ("  · actual" if x.ha_id_habitacion == hab_actual else ""): x for x in libres.itertuples()}
    elegida = opciones[st.selectbox("Habitación", list(opciones), key=f"m_hab_{rid}")]
    k = st.columns(3)
    k[0].metric("Temporada", temp["tp_nombre"])
    k[1].metric("Noches", noches)
    k[2].metric("Nuevo valor", pesos(elegida.valor_total), f"{pesos(elegida.valor_total - valor_actual)} de diferencia",
                delta_color="off")
    if st.button("Guardar cambios", type="primary", key=f"m_ok_{rid}"):
        try:
            with transaccion() as cur:
                cur.execute("""SELECT COUNT(*) FROM reserva WHERE re_id_habitacion = :ha AND re_estado <> 'cancelada'
                               AND re_id_reserva <> :id AND re_fecha_entrada < :s AND re_fecha_salida > :e""",
                            {"ha": int(elegida.ha_id_habitacion), "id": rid, "s": n_sal, "e": n_ent})
                if cur.fetchone()[0] > 0:
                    raise ValueError("La habitación se acaba de ocupar en esas fechas. Elige otra.")
                cur.execute("""UPDATE reserva
                               SET re_fecha_entrada = :e, re_fecha_salida = :s, re_noches = :n, re_num_personas = :p,
                                   re_id_habitacion = :ha, re_id_temporada = :tp, re_valor_total = :v
                               WHERE re_id_reserva = :id AND re_estado = 'confirmada'""",
                            {"e": n_ent, "s": n_sal, "n": noches, "p": int(n_per), "ha": int(elegida.ha_id_habitacion),
                             "tp": int(temp["tp_id_temporada"]), "v": float(elegida.valor_total), "id": rid})
                ok = cur.rowcount
            if ok:
                st.success(f"Reserva {rid} actualizada.")
            else:
                st.warning("La reserva ya no estaba confirmada.")
        except ValueError as e:
            st.error(str(e))
        except oracledb.IntegrityError:
            st.error("Esa habitación ya tiene otra reserva (aunque esté cancelada) con la misma fecha de entrada.")
        except oracledb.Error as e:
            st.error(mensaje_error(e))
