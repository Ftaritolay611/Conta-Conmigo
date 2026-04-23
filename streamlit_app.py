import streamlit as st
from datetime import date
import json
import os
import hashlib
import urllib.parse

st.set_page_config(page_title="Conta Conmigo", layout="centered")

telefono = "5493875213741"
DATA_FILE = "usuarios.json"

# -----------------------
# BASE DATOS
# -----------------------
def cargar():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def guardar(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verificar_password(password_guardada: str, password_ingresada: str) -> bool:
    # Compatibilidad con usuarios viejos guardados en texto plano
    if password_guardada == password_ingresada:
        return True
    return password_guardada == hash_password(password_ingresada)


def asegurar_campos_usuario(usuario: dict) -> dict:
    defaults = {
        "dni": "",
        "password": "",
        "nombre": "",
        "cuit": "",
        "categoria": "A",
        "actividad": "",
        "tipo_actividad": "Servicios",
        "direccion": "",
        "provincia": "",
        "cp": "",
        "veps": [],
        "ventas_mes": 0.0,
        "compras_mes": 0.0,
        "gastos_mes": 0.0,
    }
    for key, value in defaults.items():
        usuario.setdefault(key, value)
    return usuario


usuarios = cargar()
for key in list(usuarios.keys()):
    usuarios[key] = asegurar_campos_usuario(usuarios[key])

# -----------------------
# ESCALAS VIGENTES DESDE 01/02/2026
# -----------------------
# cat, limite ingresos anuales, cuota servicios, cuota productos
escalas = [
    ("A", 10277988.13, 42386.74, 42386.74),
    ("B", 15058447.71, 48250.78, 48250.78),
    ("C", 21113696.52, 56501.85, 55227.06),
    ("D", 26212853.42, 72414.10, 70661.26),
    ("E", 30833964.37, 102537.97, 92658.35),
    ("F", 38642048.36, 129045.32, 111198.27),
    ("G", 46211109.37, 197108.23, 135918.34),
    ("H", 70113407.33, 447346.93, 272063.40),
    ("I", 78479211.62, 824802.26, 406512.05),
    ("J", 89872640.30, 999007.65, 497059.41),
    ("K", 108357084.05, 1381687.90, 600879.51),
]

escalas_dict = {fila[0]: fila for fila in escalas}


def calcular_categoria(ingresos, tipo):
    for cat, lim, serv, prod in escalas:
        if ingresos <= lim:
            return cat, serv if tipo == "Servicios" else prod
    return None, None


def obtener_cuota(categoria, tipo_actividad):
    fila = escalas_dict.get(categoria)
    if not fila:
        return 0.0
    return fila[2] if tipo_actividad == "Servicios" else fila[3]


def obtener_limite_categoria(categoria):
    fila = escalas_dict.get(categoria)
    return fila[1] if fila else 0.0


def proximo_vencimiento():
    hoy = date.today()
    if hoy.day <= 20:
        venc = date(hoy.year, hoy.month, 20)
    else:
        if hoy.month == 12:
            venc = date(hoy.year + 1, 1, 20)
        else:
            venc = date(hoy.year, hoy.month + 1, 20)
    return venc


def analizar_recategorizacion(ventas_mes, categoria):
    limite = obtener_limite_categoria(categoria)
    if limite <= 0:
        return None

    proyeccion_anual = ventas_mes * 12
    uso = (proyeccion_anual / limite) * 100 if limite else 0
    promedio_maximo = limite / 12

    if uso >= 100:
        estado = "danger"
        mensaje = (
            f"⚠️ Riesgo alto: con ventas mensuales de ${ventas_mes:,.2f}, tu proyección anual sería "
            f"de ${proyeccion_anual:,.2f} y supera el tope de la categoría {categoria}."
        )
    elif uso >= 85:
        estado = "warning"
        mensaje = (
            f"🔎 Atención: estás usando aproximadamente el {uso:.1f}% del límite anual de tu categoría. "
            f"Si sostenés este nivel de facturación, podrías quedar cerca de una recategorización."
        )
    else:
        estado = "success"
        mensaje = (
            f"✅ Estás dentro de parámetros. Con el ritmo actual usarías cerca del {uso:.1f}% del límite anual "
            f"de tu categoría."
        )

    detalle = (
        f"Promedio mensual orientativo de tope para categoría {categoria}: ${promedio_maximo:,.2f}."
    )

    return {
        "estado": estado,
        "mensaje": mensaje,
        "detalle": detalle,
        "uso": uso,
        "proyeccion_anual": proyeccion_anual,
        "promedio_maximo": promedio_maximo,
    }


def diagnostico_negocio(ventas, compras, gastos):
    costo_total = compras + gastos
    ganancia = ventas - costo_total
    margen = (ganancia / ventas * 100) if ventas > 0 else 0
    rentabilidad = (ganancia / costo_total * 100) if costo_total > 0 else 0

    if ventas <= 0:
        salud = "Sin datos suficientes"
        mensaje = "Cargá ventas del mes para evaluar la salud del negocio."
    elif ganancia < 0:
        salud = "Crítico"
        mensaje = "Tu negocio está perdiendo dinero este mes. Tenés que revisar precios, costos o gastos urgente."
    elif margen < 10:
        salud = "Débil"
        mensaje = "Hay ganancia, pero el margen es bajo. El negocio tiene poco colchón ante imprevistos."
    elif margen < 20:
        salud = "Aceptable"
        mensaje = "La rentabilidad es razonable, aunque todavía hay espacio para mejorar precios o eficiencia."
    elif margen < 35:
        salud = "Saludable"
        mensaje = "Buen nivel de rentabilidad. El negocio muestra una estructura sana para seguir creciendo."
    else:
        salud = "Muy saludable"
        mensaje = "Excelente rentabilidad. Tenés un negocio con muy buen margen sobre ventas."

    return {
        "ganancia": ganancia,
        "margen": margen,
        "rentabilidad": rentabilidad,
        "salud": salud,
        "mensaje": mensaje,
        "costo_total": costo_total,
    }


# -----------------------
# SESSION
# -----------------------
if "user" not in st.session_state:
    st.session_state.user = None

# ======================
# LOGIN / REGISTRO
# ======================
if st.session_state.user is None:

    opcion = st.radio("Acceso", ["Iniciar sesión", "Registrarse"])

    # ---------------- REGISTRO
    if opcion == "Registrarse":

        st.title("📝 Registro")

        tipo_usuario = st.radio(
            "¿Qué querés hacer?",
            ["Ya soy monotributista", "Quiero darme de alta"]
        )

        celular = st.text_input("Celular")
        dni = st.text_input("DNI")
        password = st.text_input("Contraseña", type="password")

        # ================= YA ES MONOTRIBUTISTA
        if tipo_usuario == "Ya soy monotributista":

            nombre = st.text_input("Nombre y Apellido")
            cuit = st.text_input("CUIT")
            categoria = st.selectbox("Categoría", [x[0] for x in escalas])
            tipo_actividad = st.selectbox("Tipo de actividad", ["Servicios", "Venta de productos"])
            actividad = st.text_input("Actividad")
            direccion = st.text_input("Dirección")
            provincia = st.text_input("Provincia")
            cp = st.text_input("Código Postal")

            if st.button("Crear cuenta"):
                if not all([celular.strip(), dni.strip(), password.strip(), nombre.strip(), cuit.strip(), actividad.strip()]):
                    st.error("Completá todos los campos obligatorios.")
                elif celular in usuarios:
                    st.error("Ese celular ya está registrado.")
                else:
                    usuarios[celular] = {
                        "dni": dni.strip(),
                        "password": hash_password(password),
                        "nombre": nombre.strip(),
                        "cuit": cuit.strip(),
                        "categoria": categoria,
                        "actividad": actividad.strip(),
                        "tipo_actividad": tipo_actividad,
                        "direccion": direccion.strip(),
                        "provincia": provincia.strip(),
                        "cp": cp.strip(),
                        "veps": [],
                        "ventas_mes": 0.0,
                        "compras_mes": 0.0,
                        "gastos_mes": 0.0,
                    }
                    guardar(usuarios)
                    st.success("Cuenta creada con éxito.")

        # ================= DARSE DE ALTA
        else:

            st.subheader("📋 Requisitos")

            st.write("""
- DNI vigente  
- CUIT activo  
- Clave fiscal nivel 2 o superior  
- Domicilio fiscal actualizado  
- Datos bancarios  

Además:
- No superar ingresos máximos  
- No importar para reventa  
- Máx. 3 actividades
""")

            st.subheader("📊 Simulador")

            tipo = st.selectbox("Actividad", ["Servicios", "Venta de productos"])
            ingresos = st.number_input("Ingresos anuales estimados", min_value=0.0, step=10000.0)

            if ingresos > 0:
                cat, cuota = calcular_categoria(ingresos, tipo)
                if cat:
                    st.success(f"Categoría sugerida: {cat}")
                    st.info(f"Cuota estimada: ${cuota:,.2f}")
                else:
                    st.error("Tus ingresos superan las escalas cargadas en el simulador.")

            st.markdown("### 📎 Subir documentación")
            st.markdown("[Subir documentos](https://drive.google.com/)")

    # ---------------- LOGIN
    else:
        st.title("🔐 Login")

        celular = st.text_input("Celular")
        password = st.text_input("Contraseña", type="password")

        if st.button("Ingresar"):
            if celular in usuarios and verificar_password(usuarios[celular]["password"], password):
                # Migra password vieja a hash al iniciar sesión correctamente
                if usuarios[celular]["password"] == password:
                    usuarios[celular]["password"] = hash_password(password)
                    guardar(usuarios)
                st.session_state.user = celular
                st.rerun()
            else:
                st.error("Celular o contraseña incorrectos.")

# ======================
# HOME
# ======================
else:
    usuario_id = st.session_state.user
    usuarios = cargar()
    u = asegurar_campos_usuario(usuarios[usuario_id])

    st.title("🏠 Home del Contribuyente")

    hoy = date.today()
    venc = proximo_vencimiento()
    dias = (venc - hoy).days

    st.markdown(f"### 📅 {hoy.strftime('%d/%m/%Y')}")
    st.warning(f"⏳ Faltan {dias} días para el próximo vencimiento ({venc.strftime('%d/%m/%Y')})")

    st.success(f"👤 {u['nombre']}")
    st.write(f"CUIT: {u['cuit']}")
    st.write(f"Categoría: {u['categoria']}")
    st.write(f"Actividad: {u['actividad']}")
    st.write(f"Tipo: {u['tipo_actividad']}")

    cuota = obtener_cuota(u["categoria"], u["tipo_actividad"])
    st.info(f"💰 Cuota mensual estimada: ${cuota:,.2f}")

    st.subheader("📈 Panel mensual")

    col1, col2, col3 = st.columns(3)
    col1.metric("Ventas del mes", f"${u['ventas_mes']:,.2f}")
    col2.metric("Compras del mes", f"${u['compras_mes']:,.2f}")
    col3.metric("Gastos del mes", f"${u['gastos_mes']:,.2f}")

    with st.expander("Actualizar datos del mes"):
        ventas_mes = st.number_input(
            "Ventas del mes",
            min_value=0.0,
            value=float(u.get("ventas_mes", 0.0)),
            step=1000.0,
        )
        compras_mes = st.number_input(
            "Compras del mes",
            min_value=0.0,
            value=float(u.get("compras_mes", 0.0)),
            step=1000.0,
        )
        gastos_mes = st.number_input(
            "Gastos operativos del mes (envíos, publicidad, alquiler, etc.)",
            min_value=0.0,
            value=float(u.get("gastos_mes", 0.0)),
            step=1000.0,
        )

        if st.button("Guardar datos del mes"):
            usuarios[usuario_id]["ventas_mes"] = float(ventas_mes)
            usuarios[usuario_id]["compras_mes"] = float(compras_mes)
            usuarios[usuario_id]["gastos_mes"] = float(gastos_mes)
            guardar(usuarios)
            st.success("Datos mensuales actualizados.")
            st.rerun()

    # Recategorización
    st.subheader("🔄 Seguimiento de recategorización")
    st.info("La recategorización del Monotributo se realiza en febrero y agosto.")

    analisis = analizar_recategorizacion(float(u.get("ventas_mes", 0.0)), u["categoria"])
    if analisis:
        if analisis["estado"] == "danger":
            st.error(analisis["mensaje"])
        elif analisis["estado"] == "warning":
            st.warning(analisis["mensaje"])
        else:
            st.success(analisis["mensaje"])
        st.caption(analisis["detalle"])
        st.write(
            f"Proyección anual estimada según ventas del mes: **${analisis['proyeccion_anual']:,.2f}**"
        )

    # Panel emprendedor
    st.subheader("💼 Panel práctico para emprendedores")
    st.caption("Este cálculo es orientativo. Usa ventas, compras y gastos del mes para estimar margen y salud del negocio.")

    resultado = diagnostico_negocio(
        float(u.get("ventas_mes", 0.0)),
        float(u.get("compras_mes", 0.0)),
        float(u.get("gastos_mes", 0.0)),
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Ganancia estimada", f"${resultado['ganancia']:,.2f}")
    c2.metric("Margen sobre ventas", f"{resultado['margen']:.1f}%")
    c3.metric("Rentabilidad sobre costo", f"{resultado['rentabilidad']:.1f}%")

    if resultado["salud"] == "Crítico":
        st.error(f"Salud del negocio: {resultado['salud']}. {resultado['mensaje']}")
    elif resultado["salud"] in ["Débil", "Aceptable"]:
        st.warning(f"Salud del negocio: {resultado['salud']}. {resultado['mensaje']}")
    elif resultado["salud"] in ["Saludable", "Muy saludable"]:
        st.success(f"Salud del negocio: {resultado['salud']}. {resultado['mensaje']}")
    else:
        st.info(f"Salud del negocio: {resultado['salud']}. {resultado['mensaje']}")

    with st.expander("Cómo se calcula"):
        st.write(
            "**Ganancia estimada = Ventas del mes - Compras del mes - Gastos operativos del mes**"
        )
        st.write("**Margen sobre ventas = Ganancia / Ventas**")
        st.write("**Rentabilidad sobre costo = Ganancia / (Compras + Gastos)**")

    st.subheader("⚡ Acciones")

    msg = f"Hola, soy {u['nombre']}, CUIT {u['cuit']}. Quiero generar VEP."
    link = f"https://wa.me/{telefono}?text={urllib.parse.quote(msg)}"

    st.markdown(
        f"""
        <a href="{link}">
        <button style="background:green;color:white;padding:15px;border-radius:10px;border:none;cursor:pointer;">
        💳 Generar VEP / Pagar
        </button></a>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("📄 Historial VEP")
    if u["veps"]:
        for v in u["veps"]:
            st.write(v)
    else:
        st.write("Sin historial")

    st.markdown(f"[💬 Consultas](https://wa.me/{telefono})")

    st.subheader("📌 Más opciones")
    st.markdown(f"[❌ Quiero la baja](https://wa.me/{telefono})")
    st.markdown(f"[📑 Problemas con facturación](https://wa.me/{telefono})")
    st.markdown(f"[🔄 Necesito recategorización](https://wa.me/{telefono})")

    if st.button("Cerrar sesión"):
        st.session_state.user = None
        st.rerun()
