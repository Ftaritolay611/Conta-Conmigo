import streamlit as st
from datetime import date
import json
import os

st.set_page_config(page_title="Conta Conmigo", layout="centered")

telefono = "5493875213741"
DATA_FILE = "usuarios.json"

# -----------------------
# BASE DATOS
# -----------------------
def cargar():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE))
    return {}

def guardar(data):
    json.dump(data, open(DATA_FILE, "w"))

usuarios = cargar()

# -----------------------
# ESCALAS
# -----------------------
escalas = [
    ("A", 10277988.13, 42386.74, 42386.74),
    ("B", 15058447.71, 48250.78, 48250.78),
    ("C", 21113696.52, 56501.85, 48320.22),
    ("D", 26212853.42, 72414.10, 61824.18),
]

def calcular_categoria(ingresos, tipo):
    for cat, lim, serv, prod in escalas:
        if ingresos <= lim:
            return cat, serv if tipo=="Servicios" else prod
    return None, None

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
            categoria = st.selectbox("Categoría", list("ABCDEFGHIJ"))
            actividad = st.text_input("Actividad")
            direccion = st.text_input("Dirección")
            provincia = st.text_input("Provincia")
            cp = st.text_input("Código Postal")

            if st.button("Crear cuenta"):
                usuarios[celular] = {
                    "dni": dni,
                    "password": password,
                    "nombre": nombre,
                    "cuit": cuit,
                    "categoria": categoria,
                    "actividad": actividad,
                    "direccion": direccion,
                    "provincia": provincia,
                    "cp": cp,
                    "veps": []
                }
                guardar(usuarios)
                st.success("Cuenta creada")

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
- Máx 3 actividades
""")

            st.subheader("📊 Simulador")

            tipo = st.selectbox("Actividad", ["Servicios", "Venta de productos"])
            ingresos = st.number_input("Ingresos anuales", min_value=0)

            if ingresos > 0:
                cat, cuota = calcular_categoria(ingresos, tipo)
                if cat:
                    st.success(f"Categoría sugerida: {cat}")
                    st.info(f"Cuota estimada: ${cuota:,.2f}")

            st.markdown("### 📎 Subir documentación")
            st.markdown("[Subir documentos](https://drive.google.com/)")

    # ---------------- LOGIN
    else:
        st.title("🔐 Login")

        celular = st.text_input("Celular")
        password = st.text_input("Contraseña", type="password")

        if st.button("Ingresar"):
            if celular in usuarios and usuarios[celular]["password"] == password:
                st.session_state.user = celular
                st.rerun()
            else:
                st.error("Error")

# ======================
# HOME
# ======================
else:
    u = usuarios[st.session_state.user]

    st.title("🏠 Home del Contribuyente")

    hoy = date.today()
    venc = date(hoy.year, hoy.month, 20)
    dias = (venc - hoy).days

    st.markdown(f"### 📅 {hoy.strftime('%d/%m/%Y')}")
    st.warning(f"⏳ Faltan {dias} días para el vencimiento")

    st.success(f"👤 {u['nombre']}")
    st.write(f"CUIT: {u['cuit']}")
    st.write(f"Categoría: {u['categoria']}")
    st.write(f"Actividad: {u['actividad']}")

    # CUOTA
    cuota = 0
    for e in escalas:
        if e[0] == u["categoria"]:
            cuota = e[2]

    st.info(f"💰 A pagar: ${cuota:,.2f}")

    st.subheader("⚡ Acciones")

    # BOTON VEP
    msg = f"Hola, soy {u['nombre']}, CUIT {u['cuit']}. Quiero generar VEP."
    link = f"https://wa.me/{telefono}?text={msg}"

    st.markdown(f"""
    <a href="{link}">
    <button style="background:green;color:white;padding:15px;border-radius:10px;">
    💳 Generar VEP / Pagar
    </button></a>
    """, unsafe_allow_html=True)

    # HISTORIAL
    st.subheader("📄 Historial VEP")
    if u["veps"]:
        for v in u["veps"]:
            st.write(v)
    else:
        st.write("Sin historial")

    # CONSULTAS
    st.markdown(f"[💬 Consultas](https://wa.me/{telefono})")

    # BOTONES EXTRA
    st.subheader("📌 Más opciones")

    st.markdown(f"[❌ Quiero la baja](https://wa.me/{telefono})")
    st.markdown(f"[📑 Problemas con facturación](https://wa.me/{telefono})")
    st.markdown(f"[🔄 Necesito recategorización](https://wa.me/{telefono})")

    if st.button("Cerrar sesión"):
        st.session_state.user = None
        st.rerun()