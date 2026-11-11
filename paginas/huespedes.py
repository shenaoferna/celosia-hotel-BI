"""Página Huéspedes: registro, búsqueda con historial y eliminación."""

import datetime as dt
import re

import oracledb
import streamlit as st

from config import FORMATO_DOC, HOY
from conexion import consultar, escribir, transaccion, valor
from interfaz import pesos, tabla, titulo
from reglas import edad, limpiar_documento


def huespedes():
    titulo("Huéspedes", "Registra huéspedes nuevos o consulta el historial de uno existente.")
    registrar, buscar, eliminar = st.tabs(["Registrar huésped", "Buscar e historial", "Eliminar huésped"])

    with registrar:
        with st.form("form_huesped", clear_on_submit=False):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre completo *")
            pais = c2.text_input("País *", value="Colombia")
            c3, c4 = st.columns(2)
            tipo = c3.selectbox("Tipo de documento *", ["CC", "CE", "PAS"],
                                format_func={"CC": "CC · Cédula de ciudadanía", "CE": "CE · Cédula de extranjería",
                                             "PAS": "PAS · Pasaporte"}.get)
            documento = c4.text_input("Número de documento *", help="Puedes escribirlo con puntos o espacios; la app los quita.")
            # Fecha de nacimiento con tres listas. Solo se ofrecen años de personas entre 18 y 100 años.
            # (Quien nació en HOY.year - 18 puede no haber cumplido aún: eso lo revisa la validación de edad.)
            meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                     "octubre", "noviembre", "diciembre"]
            anios = list(range(HOY.year - 18, HOY.year - 101, -1))
            d1, d2, d3 = st.columns(3)
            dia_n = d1.selectbox("Día de nacimiento *", range(1, 32), index=0)
            mes_n = d2.selectbox("Mes de nacimiento *", range(1, 13), index=0, format_func=lambda m: meses[m - 1])
            anio_n = d3.selectbox("Año de nacimiento *", anios, index=anios.index(1990))
            c6, c7 = st.columns(2)
            email = c6.text_input("Email (opcional)")
            telefono = c7.text_input("Teléfono *", placeholder="+57 300 123 4567")
            guardar = st.form_submit_button("Registrar huésped", type="primary")

        if guardar:
            errores = []
            try:
                nacimiento = dt.date(anio_n, mes_n, dia_n)
            except ValueError:                      # por ejemplo, 31 de febrero
                nacimiento = None
                errores.append(f"La fecha {dia_n} de {meses[mes_n - 1]} de {anio_n} no existe.")
            documento = limpiar_documento(documento)
            if not nombre.strip() or not documento or not telefono.strip() or not pais.strip():
                errores.append("Completa todos los campos marcados con *.")
            patron, mensaje = FORMATO_DOC[tipo]
            if documento and not re.fullmatch(patron, documento):
                errores.append(mensaje)
            if nacimiento and edad(nacimiento) < 18:
                errores.append(f"El huésped tiene {edad(nacimiento)} años. Debe ser mayor de edad para registrarse.")
            if documento and valor("SELECT COUNT(*) FROM huesped WHERE hd_tipo_documento = :t AND hd_documento = :d",
                                   {"t": tipo, "d": documento}):
                errores.append(f"Ya existe un huésped con {tipo} {documento}.")
            if email.strip() and valor("SELECT COUNT(*) FROM huesped WHERE LOWER(hd_email) = LOWER(:m)", {"m": email.strip()}):
                errores.append("Ese email ya está registrado por otro huésped.")
            if errores:
                for e in errores:
                    st.error(e)
            else:
                try:
                    with transaccion() as cur:
                        nuevo_id = cur.var(oracledb.NUMBER)
                        cur.execute("""
                            INSERT INTO huesped (hd_nombre, hd_tipo_documento, hd_documento, hd_fecha_nacimiento,
                                                 hd_email, hd_telefono, hd_pais)
                            VALUES (:n, :t, :d, :f, :m, :tel, :p)
                            RETURNING hd_id_huesped INTO :nid""",
                            {"n": nombre.strip(), "t": tipo, "d": documento, "f": nacimiento,
                             "m": email.strip() or None, "tel": telefono.strip(), "p": pais.strip(), "nid": nuevo_id})
                        nid = int(nuevo_id.getvalue()[0])
                    st.success(f"Huésped registrado con el código {nid}. Ya puedes crear su reserva.")
                except oracledb.DatabaseError as e:
                    st.error(f"Oracle rechazó el registro: {e}")

    with eliminar:
        eliminar_huesped()

    with buscar:
        q = st.text_input("Nombre o documento", placeholder="Ej: Restrepo o 1036654321")
        if len(q.strip()) < 3:
            st.caption("Escribe al menos 3 caracteres.")
            return
        encontrados = consultar("""
            SELECT hd_id_huesped AS codigo, hd_nombre AS nombre, hd_tipo_documento AS tipo,
                   hd_documento AS documento, hd_pais AS pais, hd_email AS email, hd_telefono AS telefono
            FROM huesped
            WHERE hd_documento = :d OR UPPER(hd_nombre) LIKE UPPER(:q)
            ORDER BY hd_nombre FETCH FIRST 50 ROWS ONLY""", {"d": limpiar_documento(q), "q": f"%{q.strip()}%"})
        if encontrados.empty:
            st.info("No se encontró ningún huésped con ese nombre o documento.")
            return
        tabla(encontrados)
        opciones = dict(zip(encontrados["nombre"] + " · " + encontrados["documento"], encontrados["codigo"]))
        codigo = int(opciones[st.selectbox("Ver historial de", list(opciones))])
        hist = consultar("""
            SELECT r.re_id_reserva AS reserva, r.re_fecha_entrada AS entrada, r.re_fecha_salida AS salida,
                   h.ha_numero AS habitacion, h.ha_tipo AS tipo, r.re_noches AS noches,
                   r.re_valor_total AS valor, r.re_estado AS estado
            FROM reserva r JOIN habitacion h ON h.ha_id_habitacion = r.re_id_habitacion
            WHERE r.re_id_huesped = :c
            ORDER BY r.re_fecha_entrada DESC""", {"c": codigo})
        validas = hist[hist["estado"] != "cancelada"]
        k = st.columns(3)
        k[0].metric("Estadías", len(validas))
        k[1].metric("Noches", int(validas["noches"].sum()) if len(validas) else 0)
        k[2].metric("Total gastado", pesos(validas["valor"].sum() if len(validas) else 0))
        if len(hist):
            tabla(hist, dinero=["valor"], fechas=["entrada", "salida"], exportar=f"historial_{codigo}")
        else:
            st.info("Este huésped todavía no tiene reservas.")


def eliminar_huesped():
    """Borra un huésped solo si no tiene reservas: la FK de reserva protege su historial."""
    st.caption("Solo se pueden eliminar huéspedes sin reservas, por ejemplo un registro hecho por error.")
    c1, c2 = st.columns([1, 2])
    tipo = c1.selectbox("Tipo de documento", ["CC", "CE", "PAS"], key="borrar_tipo")
    doc = limpiar_documento(c2.text_input("Número de documento", key="borrar_doc"))
    if not doc:
        return
    g = consultar("""SELECT h.hd_id_huesped AS id, h.hd_nombre AS nombre, h.hd_pais AS pais,
                            (SELECT COUNT(*) FROM reserva r WHERE r.re_id_huesped = h.hd_id_huesped) AS reservas
                     FROM huesped h WHERE h.hd_tipo_documento = :t AND h.hd_documento = :d""", {"t": tipo, "d": doc})
    if g.empty:
        st.info(f"No hay ningún huésped con {tipo} {doc}.")
        return
    g = g.iloc[0]
    st.write(f"**{g['nombre']}**, {g['pais']}. Reservas registradas: **{int(g['reservas'])}**.")
    if g["reservas"]:
        st.warning("Este huésped tiene reservas, así que no se puede eliminar: se perdería su historial. "
                   "La base de datos también lo impide con la llave foránea de reserva.")
        return
    confirmar = st.checkbox(f"Confirmo que quiero eliminar a {g['nombre']}", key="confirmar_borrar_huesped")
    if st.button("Eliminar huésped", disabled=not confirmar):
        escribir("DELETE FROM huesped WHERE hd_id_huesped = :id", {"id": int(g["id"])},
                 f"{g['nombre']} fue eliminado.", "El huésped ya no existía.")
