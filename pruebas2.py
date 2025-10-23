import tkinter as tk
from tkinter import messagebox, simpledialog
import cv2
from PIL import Image, ImageTk
import asyncio
import threading
import socket
import json
import os
from aiortc import RTCPeerConnection, RTCIceCandidate, RTCSessionDescription
from aiortc.contrib.media import MediaRelay
import av

# Archivo para persistir usuarios
ARCHIVO_USUARIOS = 'usuarios.json'

# Cargar usuarios desde archivo
def cargar_usuarios():
    if os.path.exists(ARCHIVO_USUARIOS):
        with open(ARCHIVO_USUARIOS, 'r') as f:
            return json.load(f)
    return {}

# Guardar usuarios en archivo
def guardar_usuarios():
    with open(ARCHIVO_USUARIOS, 'w') as f:
        json.dump(usuarios_registrados, f, indent=4)

# Diccionario global para usuarios registrados
usuarios_registrados = cargar_usuarios()

# Variable global para el usuario actual
usuario_actual = None

# Servidor de señalización
senalizacion_server = None
senalizacion_thread = None
senalizacion_conexiones = {}

# Variables para WebRTC
peer_connections = {}
call_windows = {}
relay = MediaRelay()

# Función para verificar si el servidor ya está corriendo
def servidor_ya_corriendo(host='127.0.0.1', port=9999):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

# Función para iniciar servidor de señalización
def iniciar_senalizacion():
    global senalizacion_server, senalizacion_thread
    if servidor_ya_corriendo():
        print("Servidor de señalización ya corriendo. Actuando como cliente.")
        return
    senalizacion_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    senalizacion_server.bind(('127.0.0.1', 9999))
    senalizacion_server.listen(5)
    senalizacion_thread = threading.Thread(target=manejar_senalizacion, daemon=True)
    senalizacion_thread.start()
    print("Servidor de señalización iniciado.")

# Función para manejar señalización
def manejar_senalizacion():
    while True:
        client_socket, addr = senalizacion_server.accept()
        threading.Thread(target=manejar_cliente_senalizacion, args=(client_socket,), daemon=True).start()

def manejar_cliente_senalizacion(client_socket):
    username = client_socket.recv(1024).decode()
    senalizacion_conexiones[username] = client_socket
    print(f"Usuario {username} conectado al servidor.")
    while True:
        try:
            data = client_socket.recv(4096)
            if not data:
                break
            mensaje = json.loads(data.decode())
            destinatario = mensaje['to']
            print(f"Mensaje de {mensaje['from']} a {destinatario}: {mensaje['type']}")
            if destinatario in senalizacion_conexiones:
                senalizacion_conexiones[destinatario].sendall(data)
            if destinatario == usuario_actual:
                root.after(0, lambda: procesar_mensaje(mensaje))
        except Exception as e:
            print(f"Error en señalización: {e}")
            break
    del senalizacion_conexiones[username]
    client_socket.close()

# Función para procesar mensajes
def procesar_mensaje(mensaje):
    tipo = mensaje.get('type')
    remitente = mensaje.get('from')
    if tipo == 'offer':
        aceptar_llamada(remitente, mensaje['sdp'])
    elif tipo == 'answer' and remitente in peer_connections:
        asyncio.run(peer_connections[remitente].setRemoteDescription(RTCSessionDescription(sdp=mensaje['sdp'], type='answer')))
    elif tipo == 'ice-candidate' and remitente in peer_connections:
        candidate = RTCIceCandidate(
            sdp=mensaje['candidate'],
            sdpMid=mensaje['sdpMid'],
            sdpMLineIndex=mensaje['sdpMLineIndex']
        )
        asyncio.run(peer_connections[remitente].addIceCandidate(candidate))
    elif tipo == 'hangup':
        cortar_llamada(remitente)

# Función para mostrar vista previa de cámara
def mostrar_camara():
    if not usuario_actual:
        messagebox.showwarning("Advertencia", "Debes iniciar sesión.")
        return
    ventana_camara = tk.Toplevel(root)
    ventana_camara.title("Vista Previa de Cámara")
    etiqueta_video = tk.Label(ventana_camara)
    etiqueta_video.pack()
    cap = cv2.VideoCapture(0)
    def actualizar_frame():
        ret, frame = cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img_tk = ImageTk.PhotoImage(image=img)
            etiqueta_video.img_tk = img_tk
            etiqueta_video.config(image=img_tk)
            etiqueta_video.after(10, actualizar_frame)
        else:
            messagebox.showerror("Error", "No se pudo acceder a la cámara.")
    actualizar_frame()

# Función para registrar usuario
def registrar_usuario():
    username = simpledialog.askstring("Registro", "Ingrese un nombre de usuario:")
    if not username:
        messagebox.showwarning("Advertencia", "El nombre de usuario no puede estar vacío.")
        return
    if username in usuarios_registrados:
        messagebox.showerror("Error", "El nombre de usuario ya existe.")
        return
    password = simpledialog.askstring("Registro", "Ingrese una contraseña:", show='*')
    if not password:
        messagebox.showwarning("Advertencia", "La contraseña no puede estar vacía.")
        return
    ip = simpledialog.askstring("Registro", "Ingrese su dirección IP:")
    if not ip:
        messagebox.showwarning("Advertencia", "La IP no puede estar vacía.")
        return
    port_str = simpledialog.askstring("Registro", "Ingrese un puerto:")
    if not port_str or not port_str.isdigit():
        messagebox.showwarning("Advertencia", "El puerto debe ser un número válido.")
        return
    port = int(port_str)
    usuarios_registrados[username] = {'password': password, 'ip': ip, 'port': port}
    guardar_usuarios()
    messagebox.showinfo("Éxito", f"Usuario '{username}' registrado.")

# Función para iniciar sesión
def iniciar_sesion():
    global usuario_actual
    username = simpledialog.askstring("Iniciar Sesión", "Ingrese su nombre de usuario:")
    if not username:
        messagebox.showwarning("Advertencia", "El nombre de usuario no puede estar vacío.")
        return False
    if username not in usuarios_registrados:
        messagebox.showerror("Error", "Usuario no encontrado.")
        return False
    password = simpledialog.askstring("Iniciar Sesión", "Ingrese su contraseña:", show='*')
    if not password:
        messagebox.showwarning("Advertencia", "La contraseña no puede estar vacía.")
        return False
    if usuarios_registrados[username]['password'] == password:
        usuario_actual = username
        messagebox.showinfo("Éxito", f"Bienvenido, {username}!")
        conectar_senalizacion()
        return True
    else:
        messagebox.showerror("Error", "Contraseña incorrecta.")
        return False

# Función para conectar a señalización
def conectar_senalizacion():
    if not usuario_actual:
        return
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('127.0.0.1', 9999))
        client_socket.sendall(usuario_actual.encode())
        senalizacion_conexiones[usuario_actual] = client_socket
        print(f"Conectado al servidor como {usuario_actual}.")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo conectar al servidor de señalización: {e}")

# Función para iniciar llamada
def iniciar_llamada():
    if not usuario_actual:
        messagebox.showwarning("Advertencia", "Debes iniciar sesión.")
        return
    if len(usuarios_registrados) <= 1:
        messagebox.showwarning("Advertencia", "No hay otros usuarios registrados.")
        return
    
    ventana_llamada = tk.Toplevel(root)
    ventana_llamada.title("Seleccionar Usuario")
    tk.Label(ventana_llamada, text="Seleccione un usuario:").pack(pady=10)
    lista_usuarios = tk.Listbox(ventana_llamada)
    for user in usuarios_registrados.keys():
        if user != usuario_actual:
            lista_usuarios.insert(tk.END, user)
    lista_usuarios.pack(pady=10)
    
    def llamar_seleccionado():
        seleccionado = lista_usuarios.get(tk.ACTIVE)
        if seleccionado:
            asyncio.run(iniciar_llamada_webrtc(seleccionado))
            ventana_llamada.destroy()
        else:
            messagebox.showwarning("Advertencia", "Seleccione un usuario válido.")
    
    tk.Button(ventana_llamada, text="Llamar", command=llamar_seleccionado).pack(pady=10)

# Función asíncrona para iniciar llamada WebRTC
async def iniciar_llamada_webrtc(seleccionado):
    pc = RTCPeerConnection()
    peer_connections[seleccionado] = pc
    
    # Crear oferta
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    
    # Enviar oferta
    mensaje = json.dumps({'from': usuario_actual, 'to': seleccionado, 'type': 'offer', 'sdp': offer.sdp})
    if usuario_actual in senalizacion_conexiones:
        senalizacion_conexiones[usuario_actual].sendall(mensaje.encode())
    
    # Mostrar ventana inmediatamente (sin esperar tracks)
    mostrar_llamada_activa(seleccionado, pc, None)
    
    # Configurar eventos
    @pc.on("track")
    def on_track(track):
        if track.kind == "video":
            # Actualizar si hay track remoto (placeholder)
            pass
    
    @pc.on("icecandidate")
    async def on_icecandidate(candidate):
        if candidate:
            mensaje = json.dumps({
                'from': usuario_actual,
                'to': seleccionado,
                'type': 'ice-candidate',
                'candidate': candidate.candidate,
                'sdpMid': candidate.sdpMid,
                'sdpMLineIndex': candidate.sdpMLineIndex
            })
            if usuario_actual in senalizacion_conexiones:
                senalizacion_conexiones[usuario_actual].sendall(mensaje.encode())

# Función para aceptar llamada
def aceptar_llamada(remitente, sdp):
    respuesta = messagebox.askyesno("Llamada entrante", f"Llamada de {remitente}. ¿Aceptar?")
    if respuesta:
        asyncio.run(aceptar_llamada_webrtc(remitente, sdp))
    else:
        mensaje = json.dumps({'from': usuario_actual, 'to': remitente, 'type': 'hangup'})
        if usuario_actual in senalizacion_conexiones:
            senalizacion_conexiones[usuario_actual].sendall(mensaje.encode())

async def aceptar_llamada_webrtc(remitente, sdp):
    pc = RTCPeerConnection()
    peer_connections[remitente] = pc
    
    await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type='offer'))
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    
    mensaje = json.dumps({'from': usuario_actual, 'to': remitente, 'type': 'answer', 'sdp': answer.sdp})
    if usuario_actual in senalizacion_conexiones:
        senalizacion_conexiones[usuario_actual].sendall(mensaje.encode())
    
    # Mostrar ventana inmediatamente
    mostrar_llamada_activa(remitente, pc, None)
    
    @pc.on("track")
    def on_track(track):
        if track.kind == "video":
            pass
    
    @pc.on("icecandidate")
    async def on_icecandidate(candidate):
        if candidate:
            mensaje = json.dumps({
                'from': usuario_actual,
                'to': remitente,
                'type': 'ice-candidate',
                'candidate': candidate.candidate,
                'sdpMid': candidate.sdpMid,
                'sdpMLineIndex': candidate.sdpMLineIndex
            })
            if usuario_actual in senalizacion_conexiones:
                senalizacion_conexiones[usuario_actual].sendall(mensaje.encode())

# Función para mostrar ventana de llamada activa
def mostrar_llamada_activa(seleccionado, pc, remote_track):
    ventana_llamada = tk.Toplevel(root)
    ventana_llamada.title(f"Llamada con {seleccionado}")
    call_windows[seleccionado] = ventana_llamada
    
    # Etiquetas para video
    etiqueta_local = tk.Label(ventana_llamada, text="Video Local")
    etiqueta_local.pack(side=tk.LEFT)
    etiqueta_remoto = tk.Label(ventana_llamada, text="Video Remoto")
    etiqueta_remoto.pack(side=tk.RIGHT)
    
    # Actualizar video local (de cámara)
    cap = cv2.VideoCapture(0)
    def actualizar_local():
        ret, frame = cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (320, 240))  # Redimensionar para la ventana
            img = Image.fromarray(frame)
            img_tk = ImageTk.PhotoImage(image=img)
            etiqueta_local.img_tk = img_tk
            etiqueta_local.config(image=img_tk)
            etiqueta_local.after(100, actualizar_local)
        else:
            etiqueta_local.config(text="Cámara no disponible")
    
    actualizar_local()
    
    # Video remoto placeholder
    def actualizar_remoto():
        etiqueta_remoto.config(text="Esperando video remoto...")
        etiqueta_remoto.after(1000, actualizar_remoto)
    actualizar_remoto()
    
    # Botón para cortar
    def cortar():
        cortar_llamada(seleccionado)
        ventana_llamada.destroy()
    
    tk.Button(ventana_llamada, text="Cortar Llamada", command=cortar).pack(pady=10)

# Función para cortar llamada
def cortar_llamada(seleccionado):
    if seleccionado in peer_connections:
        asyncio.run(peer_connections[seleccionado].close())
        del peer_connections[seleccionado]
    if seleccionado in call_windows:
        call_windows[seleccionado].destroy()
        del call_windows[seleccionado]
    mensaje = json.dumps({'from': usuario_actual, 'to': seleccionado, 'type': 'hangup'})
    if usuario_actual in senalizacion_conexiones:
        senalizacion_conexiones[usuario_actual].sendall(mensaje.encode())

# Función para opciones
def opciones():
    if not usuario_actual:
        messagebox.showwarning("Advertencia", "Debes iniciar sesión.")
        return
    messagebox.showinfo("Opciones", "Configuración: Volumen al 50%.")

# Función para mostrar login
def mostrar_login():
    root.title("Iniciar Sesión")
    tk.Label(root, text="Nombre de Usuario:").grid(row=0, column=0, padx=10, pady=10)
    entry_username = tk.Entry(root)
    entry_username.grid(row=0, column=1, padx=10, pady=10)
    tk.Label(root, text="Contraseña:").grid(row=1, column=0, padx=10, pady=10)
    entry_password = tk.Entry(root, show='*')
    entry_password.grid(row=1, column=1, padx=10, pady=10)
    
    def intentar_login():
        global usuario_actual
        username = entry_username.get()
        password = entry_password.get()
        if username in usuarios_registrados and usuarios_registrados[username]['password'] == password:
            usuario_actual = username
            messagebox.showinfo("Éxito", f"Bienvenido, {username}!")
            for widget in root.winfo_children():
                widget.destroy()
            configurar_app_principal()
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos.")
    
    tk.Button(root, text="Iniciar Sesión", command=intentar_login).grid(row=2, column=0, columnspan=2, pady=10)
    tk.Button(root, text="Registrarse", command=lambda: [registrar_usuario(), mostrar_login()]).grid(row=3, column=0, columnspan=2, pady=10)

# Función para configurar app principal
def configurar_app_principal():
    root.title("Aplicación de Llamadas")
    menubar = tk.Menu(root)
    root.config(menu=menubar)
    menu_archivo = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Archivo", menu=menu_archivo)
    menu_archivo.add_command(label="Vista Previa de Cámara", command=mostrar_camara)
    menu_archivo.add_command(label="Iniciar Llamada", command=iniciar_llamada)
    menu_archivo.add_command(label="Opciones", command=opciones)
    menu_archivo.add_separator()
    menu_archivo.add_command(label="Salir", command=root.quit)
    menu_usuario = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Usuario", menu=menu_usuario)
    menu_usuario.add_command(label="Registrarse", command=registrar_usuario)
    menu_usuario.add_command(label="Iniciar Sesión", command=iniciar_sesion)

# Iniciar servidor
iniciar_senalizacion()

# Crear ventana principal
root = tk.Tk()
root.title("Aplicación de Llamadas")
mostrar_login()
root.mainloop()