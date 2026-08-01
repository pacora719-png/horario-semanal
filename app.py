import streamlit as st
import pandas as pd
from datetime import date, time, timedelta, datetime
from database import get_connection, execute, read_sql_query, get_config, get_ubicaciones

st.set_page_config(page_title="Registro de Horario Semanal", page_icon="🕒", layout="centered")

nombre_empresa = get_config("nombre_empresa", "Mi Empresa")
st.title(f"🕒 Registro de Horario Semanal")
st.caption(f"{nombre_empresa} — solo entrada y salida, se guarda directo en el ERP")

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# ---------- LOGIN BÁSICO (opcional, mismo usuario del ERP si se configura) ----------
def check_login():
    if "usuarios" not in st.secrets:
        return True  # si no se configuró login, la app queda abierta (útil para tablet compartida)
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if st.session_state.autenticado:
        return True

    with st.form("login_form"):
        usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")
        enviar = st.form_submit_button("Ingresar")
    if enviar:
        usuarios_validos = st.secrets.get("usuarios", {})
        if usuario in usuarios_validos and clave == usuarios_validos[usuario]:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")
    return False


if not check_login():
    st.stop()

try:
    horas_normales_max = float(get_config("horas_normales_por_dia", "7"))
except Exception as e:
    st.error(f"No se pudo conectar a la base de datos: {e}")
    st.stop()

# ---------- CARGAR EMPLEADOS ----------
with get_connection() as conn:
    empleados_df = read_sql_query(
        "SELECT * FROM empleados WHERE estado='Activo' ORDER BY nombre", conn
    )

# ---------- AGREGAR EMPLEADO NUEVO ----------
with st.expander("➕ Agregar un empleado nuevo"):
    ubicaciones = get_ubicaciones()
    with st.form("nuevo_empleado_form", clear_on_submit=True):
        nombre_nuevo = st.text_input("Nombre completo *")
        if ubicaciones:
            ubicacion_id_nuevo = st.selectbox(
                "Sede", [u["id"] for u in ubicaciones],
                format_func=lambda x: next(u["nombre"] for u in ubicaciones if u["id"] == x)
            )
        else:
            st.warning("No hay sedes creadas todavía en el ERP — el empleado se creará sin sede asignada.")
            ubicacion_id_nuevo = None
        crear = st.form_submit_button("Agregar empleado")

    if crear:
        if not nombre_nuevo.strip():
            st.error("El nombre es obligatorio.")
        else:
            with get_connection() as conn:
                execute(conn, """
                    INSERT INTO empleados (nombre, ubicacion_id, estado, salario_base, valor_hora)
                    VALUES (?, ?, 'Activo', 0, 0)
                """, (nombre_nuevo.strip(), ubicacion_id_nuevo))
            st.success(f"Empleado '{nombre_nuevo}' agregado. Complétalo con más datos (salario, cédula, afiliaciones) directamente en el ERP cuando puedas.")
            st.rerun()

if empleados_df.empty:
    st.warning("Todavía no hay empleados activos. Agrega el primero arriba.")
    st.stop()

st.divider()

# ---------- SELECCIÓN DE EMPLEADO Y SEMANA ----------
empleado_id = st.selectbox(
    "Empleado",
    empleados_df["id"].tolist(),
    format_func=lambda x: empleados_df[empleados_df["id"] == x]["nombre"].values[0]
)

hoy = date.today()
lunes_actual = hoy - timedelta(days=hoy.weekday())
fecha_inicio_semana = st.date_input("Lunes de la semana a registrar", value=lunes_actual)

# ---------- CARGAR HORAS YA GUARDADAS DE ESA SEMANA (para no perderlas al recargar) ----------
fecha_fin_semana = fecha_inicio_semana + timedelta(days=6)
with get_connection() as conn:
    horas_existentes = read_sql_query("""
        SELECT * FROM horas WHERE empleado_id=? AND fecha BETWEEN ? AND ?
    """, conn, params=(int(empleado_id), str(fecha_inicio_semana), str(fecha_fin_semana)))
existentes_por_fecha = {row["fecha"]: row for _, row in horas_existentes.iterrows()} if not horas_existentes.empty else {}

st.subheader("Horario de la semana")
st.caption("Marca 'No trabajó' en los días libres. El resto se guarda con la hora de entrada y salida que pongas.")

valores_dia = {}
for i, dia_nombre in enumerate(DIAS):
    fecha_dia = fecha_inicio_semana + timedelta(days=i)
    fecha_str = str(fecha_dia)
    existente = existentes_por_fecha.get(fecha_str)

    col_dia, col_libre, col_entrada, col_salida = st.columns([2, 1.3, 1.3, 1.3])
    with col_dia:
        st.markdown(f"**{dia_nombre}**")
        st.caption(fecha_dia.strftime("%d/%m/%Y"))

    entrada_default = time(8, 0)
    salida_default = time(17, 0)
    libre_default = False
    if existente is not None:
        try:
            entrada_default = datetime.strptime(str(existente["hora_entrada"])[:5], "%H:%M").time()
            salida_default = datetime.strptime(str(existente["hora_salida"])[:5], "%H:%M").time()
        except Exception:
            pass
        if float(existente["horas_normales"] or 0) == 0 and not existente["hora_entrada"]:
            libre_default = True

    with col_libre:
        no_trabajo = st.checkbox("No trabajó", value=libre_default, key=f"libre_{i}")
    with col_entrada:
        h_entrada = st.time_input("Entrada", value=entrada_default, key=f"entrada_{i}", disabled=no_trabajo, label_visibility="collapsed")
    with col_salida:
        h_salida = st.time_input("Salida", value=salida_default, key=f"salida_{i}", disabled=no_trabajo, label_visibility="collapsed")

    valores_dia[fecha_str] = {"no_trabajo": no_trabajo, "entrada": h_entrada, "salida": h_salida}
    st.divider()

if st.button("💾 Guardar horario de la semana", type="primary", use_container_width=True):
    guardados = 0
    with get_connection() as conn:
        for fecha_str, datos in valores_dia.items():
            if datos["no_trabajo"]:
                continue

            entrada_dt = datetime.combine(date.today(), datos["entrada"])
            salida_dt = datetime.combine(date.today(), datos["salida"])
            tiempo_bruto = max(0, (salida_dt - entrada_dt).total_seconds() / 3600)
            horas_normales = min(tiempo_bruto, horas_normales_max)

            existente = existentes_por_fecha.get(fecha_str)
            if existente is not None:
                execute(conn, """
                    UPDATE horas SET hora_entrada=?, hora_salida=?, horas_normales=?
                    WHERE id=?
                """, (str(datos["entrada"]), str(datos["salida"]), round(horas_normales, 4), int(existente["id"])))
            else:
                execute(conn, """
                    INSERT INTO horas (empleado_id, fecha, hora_entrada, hora_salida, horas_normales,
                    horas_extra_diurna, horas_extra_nocturna, horas_extra_dominical_festivo,
                    horas_extra_dominical_festivo_nocturna, horas_recargo_nocturno, horas_recargo_dominical,
                    horas_recargo_dominical_festivo_nocturno, horas_descuento, bonificacion, deduccion)
                    VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
                """, (int(empleado_id), fecha_str, str(datos["entrada"]), str(datos["salida"]), round(horas_normales, 4)))
            guardados += 1

    st.success(f"Horario guardado: {guardados} día(s) registrados para la semana del {fecha_inicio_semana.strftime('%d/%m/%Y')}.")
    st.info("Las horas extra, recargos, tiempo a descontar y demás detalles de nómina se completan en el ERP principal.")
