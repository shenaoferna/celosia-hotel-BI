"""Conexión centralizada a Oracle: pool, lecturas, escrituras en transacción y mensajes de error."""

from contextlib import contextmanager

import oracledb
import pandas as pd
import streamlit as st


@st.cache_resource
def get_pool():
    s = st.secrets["oracle"]
    if "lib_dir" in s:   # modo thick (Instant Client)
        oracledb.init_oracle_client(lib_dir=s["lib_dir"], config_dir=s["config_dir"])
        return oracledb.create_pool(user=s["user"], password=s["password"], dsn=s["dsn"], min=1, max=4)
    return oracledb.create_pool(   # modo thin: el wallet se entrega como parámetros
        user=s["user"], password=s["password"], dsn=s["dsn"], min=1, max=4,
        config_dir=s["config_dir"], wallet_location=s.get("wallet_location", s["config_dir"]),
        wallet_password=s["wallet_password"])


def consultar(sql, params=None):
    """SELECT -> DataFrame (columnas en minúscula)."""
    with get_pool().acquire() as con:
        cur = con.cursor()
        cur.execute(sql, params or {})
        columnas = [d[0].lower() for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=columnas)


def valor(sql, params=None):
    """SELECT que devuelve un solo número."""
    df = consultar(sql, params)
    v = df.iat[0, 0] if len(df) else None
    return 0 if v is None or pd.isna(v) else v


def consultar_solo_lectura(sql, limite=1000):
    """Ejecuta un SELECT escrito por el usuario dentro de una transacción de solo lectura."""
    with get_pool().acquire() as con:
        cur = con.cursor()
        cur.execute("SET TRANSACTION READ ONLY")
        try:
            cur.execute(sql)
            columnas = [d[0].lower() for d in cur.description]
            return pd.DataFrame(cur.fetchmany(limite), columns=columnas)
        finally:
            con.rollback()


def mensaje_error(e):
    """Traduce los errores de Oracle más comunes a un mensaje claro para el usuario."""
    texto = str(e)
    if "ORA-02292" in texto:
        return "No se puede eliminar: hay reservas que dependen de este registro."
    if "ORA-00001" in texto:
        return "Ya existe un registro con esos datos, y deben ser únicos."
    if "ORA-02290" in texto:
        return "El dato no cumple una de las reglas de la base de datos."
    if "ORA-01400" in texto:
        return "Falta un dato obligatorio."
    if "ORA-01031" in texto or "ORA-01456" in texto:
        return "Esta operación no está permitida aquí."
    if "DPY-4011" in texto or "ORA-03113" in texto or "ORA-03114" in texto or "DPY-6005" in texto:
        return "Se perdió la conexión con la base de datos. Recarga la página e intenta de nuevo."
    return f"Oracle rechazó la operación: {texto}"


@contextmanager
def transaccion():
    """INSERT/UPDATE: si todo sale bien COMMIT, si algo falla ROLLBACK."""
    con = get_pool().acquire()
    try:
        yield con.cursor()
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def escribir(sql, params, ok, sin_cambios=None):
    """Ejecuta un INSERT/UPDATE/DELETE en una transacción y muestra el resultado al usuario.
    Devuelve True si cambió al menos una fila."""
    try:
        with transaccion() as cur:
            cur.execute(sql, params)
            filas = cur.rowcount
    except oracledb.Error as e:
        st.error(mensaje_error(e))
        return False
    if filas:
        st.success(ok)
        return True
    st.warning(sin_cambios or "No se hizo ningún cambio.")
    return False
