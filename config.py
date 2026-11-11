"""Identidad del hotel, paleta de colores y parámetros de negocio."""

import datetime as dt

# Identidad de marca. La celosía es la reja de madera de los balcones coloniales:
# deja pasar el aire y protege la intimidad.
HOTEL = "Celosía"
DESCRIPCION_HOTEL = "Hotel boutique en Cartagena de Indias, a cinco minutos de la ciudad amurallada"
LEMA = "La brisa entra, el ruido se queda afuera."

# Fecha de hoy: se usa en todas las reglas que dependen del día actual
HOY = dt.date.today()

# Paleta inspirada en la ciudad amurallada
TINTA = "#2F3F73"        # añil de las puertas coloniales (color principal)
LATON = "#B08D57"        # latón de aldabas y herrajes
SALVIA = "#2F6B5E"       # verde de balcón
PALISANDRO = "#A23E6E"   # buganvilla
PIEDRA = "#8C7F6E"       # piedra coralina de la muralla

COLOR_ESTADO = {"confirmada": LATON, "en_curso": SALVIA, "finalizada": TINTA, "cancelada": PALISANDRO}
ESTADOS = ["confirmada", "en_curso", "finalizada", "cancelada"]
# Ciclo de vida: confirmada --check-in--> en_curso --check-out--> finalizada ; confirmada --cancelar--> cancelada

CANALES = {"directo": "Directo (web o teléfono del hotel)", "booking": "Booking / OTA", "agencia": "Agencia de viajes",
           "walk_in": "Llegó sin reserva (walk-in)"}

# Supuestos de negocio (no están en la base): comisión que cobra cada canal sobre el valor de la reserva
COMISION = {"directo": 0.0, "walk_in": 0.0, "booking": 0.18, "agencia": 0.12}

# Ingreso realizado = estadías finalizadas o en curso. En cartera = reservas confirmadas que todavía no ocurren.
NOTA_CARTERA = ("Realizado: estadías finalizadas o en curso. En cartera: reservas confirmadas que todavía "
                "no ocurren, es decir, dinero esperado.")

# Formato de cada tipo de documento: el mismo que exige el CHECK ck_huesped_formato_doc del DDL
FORMATO_DOC = {
    "CC":  (r"^[0-9]{5,10}$",    "Una cédula de ciudadanía tiene solo números, entre 5 y 10 dígitos."),
    "CE":  (r"^[0-9]{4,7}$",     "Una cédula de extranjería tiene solo números, entre 4 y 7 dígitos."),
    "PAS": (r"^[A-Z0-9]{6,12}$", "Un pasaporte tiene letras y números, entre 6 y 12 caracteres, sin espacios ni símbolos."),
}
