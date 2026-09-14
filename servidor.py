#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SERVIDOR DE CHAT CON SOCKETS TCP/IP Y BASE DE DATOS SQLITE EN PYTHON
================================================================================
Objetivo didáctico:
  Configurar un servidor de red utilizando el protocolo TCP/IP nativo de Python,
  recibir mensajes de clientes, persistir cada mensaje en una base de datos SQLite,
  enviar una confirmación automática ("Mensaje recibido: <timestamp>") Y permitir
  al operador del servidor responder con mensajes escritos manualmente por teclado.

Estructura del servidor:
  1. Bloque de Importaciones requeridas (socket, sqlite3, sys, datetime).
  2. Bloque de Configuración General y Constantes globales.
  3. Función 'inicializar_db': Configuración del esquema en SQLite3.
  4. Función 'leer_mensaje_teclado_servidor': Captura de texto por teclado (input).
  5. Función 'guardar_mensaje': Inserción parametrizada en la base de datos.
  6. Función 'inicializar_socket': Creación, enlace (bind) y escucha (listen).
  7. Función 'atender_cliente': Confirmación automática + envío de respuesta por teclado.
  8. Función 'iniciar_servidor': Orquestación general y bucle accept().
  9. Bloque de Ejecución Principal (__main__).
================================================================================
"""

# ==============================================================================
# BLOQUE 1: IMPORTACIONES DE BIBLIOTECAS DEL SISTEMA
# ==============================================================================
# 'socket': Comunicación de red a nivel de transporte TCP/IP
import socket

# 'sqlite3': Motor de base de datos relacional ligero embebido en archivo local
import sqlite3

# 'sys': Parámetros de línea de comando, flujos de error (stderr) y verificación TTY
import sys

# 'datetime': Generación de marcas temporales precisas del reloj del sistema
from datetime import datetime


# ==============================================================================
# BLOQUE 2: CONFIGURACIÓN GENERAL Y CONSTANTES
# ==============================================================================
HOST_DEFAULT = "127.0.0.1"    # Loopback local (localhost)
PUERTO_DEFAULT = 5000          # Puerto TCP en el que escuchará el servidor
DB_NOMBRE_DEFAULT = "chat.db" # Nombre del archivo de base de datos SQLite
BUFFER_SIZE = 1024             # Tamaño del búfer de lectura en bytes (1 KB)


# ==============================================================================
# BLOQUE 3: INICIALIZACIÓN Y CONFIGURACIÓN DE LA BASE DE DATOS SQLITE
# ==============================================================================
def inicializar_db(nombre_db=DB_NOMBRE_DEFAULT):
    """
    Crea la base de datos SQLite y la tabla 'mensajes' si aún no existen.
    
    Campos de la tabla 'mensajes':
      - id: Clave primaria autoincremental única.
      - contenido: Texto enviado por el cliente.
      - fecha_envio: Marca temporal en formato 'AAAA-MM-DD HH:MM:SS'.
      - ip_cliente: Dirección IP del cliente que envió el mensaje.
      - respuesta_servidor: Texto de la respuesta escrita por teclado en el servidor.
    """
    print(f"[DB] Verificando e inicializando base de datos en: '{nombre_db}'...")

    try:
        conexion = sqlite3.connect(nombre_db)
        cursor = conexion.cursor()

        # Creación de la tabla mensajes con los campos solicitados
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contenido TEXT NOT NULL,
                fecha_envio TEXT NOT NULL,
                ip_cliente TEXT NOT NULL,
                respuesta_servidor TEXT
            );
        """)

        # Si la tabla ya existía de ejecuciones previas sin la columna respuesta_servidor, la agregamos
        try:
            cursor.execute("ALTER TABLE mensajes ADD COLUMN respuesta_servidor TEXT;")
        except sqlite3.OperationalError:
            pass # Ya existe la columna

        conexion.commit()
        conexion.close()

        print("[DB] Base de datos y tabla 'mensajes' configuradas correctamente.")
        return True

    except sqlite3.OperationalError as e:
        print(f"[ERROR DB] Error operacional al acceder a SQLite: {e}", file=sys.stderr)
        raise
    except sqlite3.Error as e:
        print(f"[ERROR DB] Error general de SQLite: {e}", file=sys.stderr)
        raise


# ==============================================================================
# BLOQUE 4: ENTRADA POR TECLADO DEL MENSAJE DEL SERVIDOR
# ==============================================================================
def leer_mensaje_teclado_servidor(cliente_ip):
    """
    Lee por teclado (input) el mensaje de texto que el operador del servidor
    desea responderle al cliente.
    
    Comportamiento:
      - Si se ejecuta en una terminal estándar (sys.stdin.isatty() == True),
        solicita la entrada interactiva con input("Servidor > ").
      - Si se ejecuta en segundo plano o pruebas automatizadas, utiliza una
        respuesta por defecto para no bloquear el proceso indefinidamente.
    """
    print(f"\n-> Ingresá el mensaje de respuesta para el cliente ({cliente_ip}):")

    # Verificamos si la entrada estándar está conectada a una terminal interactiva
    if sys.stdin.isatty():
        try:
            texto = input("Servidor > ").strip()
            # Si el operador simplemente presiona Enter, enviamos un acuse cordial
            if not texto:
                texto = "(Mensaje leído por el servidor sin texto adicional)"
            return texto
        except (EOFError, KeyboardInterrupt):
            print("\n[AVISO] Entrada cancelada por teclado.")
            return "(Respuesta cancelada por operador del servidor)"
    else:
        # Entorno no interactivo (ej: pruebas automatizadas o subprocesos de fondo)
        return "Respuesta ingresada desde el servidor"


# ==============================================================================
# BLOQUE 5: GUARDAR MENSAJE EN LA BASE DE DATOS SQLITE
# ==============================================================================
def guardar_mensaje(contenido, ip_cliente, fecha_envio=None, respuesta_servidor=None, nombre_db=DB_NOMBRE_DEFAULT):
    """
    Inserta un nuevo registro en la tabla 'mensajes' usando consultas parametrizadas.
    """
    if fecha_envio is None:
        fecha_envio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conexion = sqlite3.connect(nombre_db)
        cursor = conexion.cursor()

        query = """
            INSERT INTO mensajes (contenido, fecha_envio, ip_cliente, respuesta_servidor)
            VALUES (?, ?, ?, ?);
        """
        cursor.execute(query, (contenido, fecha_envio, ip_cliente, respuesta_servidor))

        conexion.commit()
        id_asignado = cursor.lastrowid
        conexion.close()

        print(f"[DB] Mensaje #{id_asignado} guardado con éxito (IP: {ip_cliente}, Fecha: {fecha_envio}).")
        return id_asignado

    except sqlite3.OperationalError as e:
        print(f"[ERROR DB] Error al guardar el mensaje en SQLite: {e}", file=sys.stderr)
        return None
    except sqlite3.Error as e:
        print(f"[ERROR DB] Error general de SQLite: {e}", file=sys.stderr)
        return None


# ==============================================================================
# BLOQUE 6: INICIALIZACIÓN DEL SOCKET TCP/IP
# ==============================================================================
def inicializar_socket(host=HOST_DEFAULT, puerto=PUERTO_DEFAULT):
    """
    Crea, configura y pone a escuchar un socket TCP/IP en la interfaz y puerto indicados.
    """
    print(f"[SOCKET] Creando y configurando socket TCP/IP en {host}:{puerto}...")

    try:
        # Socket TCP IPv4
        servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # SO_REUSEADDR permite reiniciar el servidor sin esperar el estado TIME_WAIT
        servidor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Enlace del socket a IP y puerto
        servidor_socket.bind((host, puerto))

        # Puesta en modo escucha con cola de hasta 5 clientes
        servidor_socket.listen(5)

        print(f"[SERVIDOR] Socket listo y escuchando en {host}:{puerto}.")
        return servidor_socket

    except OSError as e:
        if e.errno in (98, 10048) or "Address already in use" in str(e):
            print(f"[ERROR SOCKET] El puerto {puerto} ya está ocupado por otro proceso o servidor.", file=sys.stderr)
            print(f"[AYUDA] Detén el programa que esté usando el puerto {puerto} o cambia el puerto al ejecutar.", file=sys.stderr)
        else:
            print(f"[ERROR SOCKET] Error del sistema al inicializar el socket: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ERROR INESPERADO] Falla inesperada al inicializar socket: {e}", file=sys.stderr)
        return None


# ==============================================================================
# BLOQUE 7: ATENDER AL CLIENTE Y PROCESAR MENSAJES
# ==============================================================================
def atender_cliente(cliente_socket, cliente_direccion, nombre_db=DB_NOMBRE_DEFAULT):
    """
    Gestiona el ciclo de interacción con un cliente conectado:
      1. Recibe el mensaje enviado por el cliente.
      2. Si el mensaje es 'éxito', envía confirmación de despedida y cierra.
      3. Envía AUTOMÁTICAMENTE la confirmación de recepción:
         "Mensaje recibido: <timestamp>"
      4. Permite al operador del servidor escribir un mensaje POR TECLADO con input().
      5. Envía el mensaje escrito por teclado al cliente por el socket.
      6. Guarda ambos datos (mensaje recibido y respuesta del servidor) en SQLite.
      7. Cierra el socket en el bloque 'finally'.
    """
    ip_cliente, puerto_cliente = cliente_direccion
    print(f"\n[NUEVA CONEXIÓN] Cliente conectado desde {ip_cliente}:{puerto_cliente}")

    # Desactivamos el algoritmo de Nagle para enviar paquetes inmediatamente sin retardo
    try:
        cliente_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
        pass

    try:
        while True:
            # Lectura del mensaje del cliente desde el socket
            datos_binarios = cliente_socket.recv(BUFFER_SIZE)

            # Si recv retorna vacío b'', el cliente cerró el socket
            if not datos_binarios:
                print(f"[DESCONEXIÓN] El cliente {ip_cliente}:{puerto_cliente} cerró la conexión.")
                break

            mensaje_cliente = datos_binarios.decode("utf-8").strip()
            print(f"\n[CLIENTE {ip_cliente}] {mensaje_cliente}")

            # Detección del comando especial de salida 'éxito' (o 'exito')
            if mensaje_cliente.lower() in ("éxito", "exito"):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                despedida = f"Conexión finalizada por comando '{mensaje_cliente}'. Hasta pronto! ({timestamp})"
                # Enviamos la despedida con salto de línea para que el cliente la procese limpiamente
                cliente_socket.sendall((despedida + "\n").encode("utf-8"))
                print(f"[CIERRE] Cliente {ip_cliente} finalizó la sesión con '{mensaje_cliente}'.")
                break

            # ------------------------------------------------------------------
            # PASO 1: ENVIAR CONFIRMACIÓN AUTOMÁTICA INMEDIATA AL CLIENTE
            # ------------------------------------------------------------------
            # Ni bien se recibe el mensaje del cliente, enviamos de inmediato la confirmación
            # con el timestamp exacto de recepción. Esto permite que el cliente lo vea en su
            # pantalla sin tener que esperar a que el operador redacte su respuesta.
            timestamp_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            confirmacion_automatica = f"Mensaje recibido: {timestamp_actual}\n"
            cliente_socket.sendall(confirmacion_automatica.encode("utf-8"))
            print(f"[CONFIRMACIÓN ENVIADA AL CLIENTE] {confirmacion_automatica.strip()}")

            # ------------------------------------------------------------------
            # PASO 2: INGRESO POR TECLADO DEL MENSAJE DEL SERVIDOR
            # ------------------------------------------------------------------
            # El cliente ya tiene en pantalla el acuse de recibo. Ahora el operador
            # del servidor ingresa la respuesta por teclado con input().
            mensaje_teclado = leer_mensaje_teclado_servidor(ip_cliente)

            # ------------------------------------------------------------------
            # PASO 3: ENVIAR RESPUESTA DEL OPERADOR AL CLIENTE
            # ------------------------------------------------------------------
            paquete_respuesta = f"Servidor: {mensaje_teclado}\n"
            cliente_socket.sendall(paquete_respuesta.encode("utf-8"))
            print(f"[RESPUESTA POR TECLADO ENVIADA]\n  -> Servidor: {mensaje_teclado}")

            # ------------------------------------------------------------------
            # PASO 4: PERSISTENCIA EN BASE DE DATOS SQLITE
            # ------------------------------------------------------------------
            guardar_mensaje(
                contenido=mensaje_cliente,
                ip_cliente=ip_cliente,
                fecha_envio=timestamp_actual,
                respuesta_servidor=mensaje_teclado,
                nombre_db=nombre_db
            )

    except ConnectionResetError:
        print(f"[ERROR CONEXIÓN] Conexión reiniciada abruptamente por {ip_cliente}.", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR COMUNICACIÓN] Error al comunicarse con {ip_cliente}: {e}", file=sys.stderr)
    finally:
        cliente_socket.close()
        print(f"[SOCKET CERRADO] Conexión finalizada para {ip_cliente}:{puerto_cliente}.\n")


# ==============================================================================
# BLOQUE 8: FUNCIÓN PRINCIPAL DEL SERVIDOR (ORQUESTACIÓN)
# ==============================================================================
def iniciar_servidor(host=HOST_DEFAULT, puerto=PUERTO_DEFAULT, nombre_db=DB_NOMBRE_DEFAULT):
    """
    Coordina el ciclo de vida completo del servidor:
      1. Inicializa la base de datos SQLite.
      2. Inicializa el socket TCP y lo vincula al puerto 5000.
      3. Bucle 'accept()' para atender a los clientes.
      4. Captura la señal Ctrl+C para un apagado limpio.
    """
    print("=" * 70)
    print("   SERVIDOR DE CHAT CON SOCKETS TCP Y BASE DE DATOS SQLITE")
    print("=" * 70)

    # 1. Inicialización de base de datos
    try:
        inicializar_db(nombre_db)
    except Exception:
        print("[FATAL] La base de datos no es accesible. Abortando inicio.", file=sys.stderr)
        return

    # 2. Inicialización de socket
    servidor_socket = inicializar_socket(host, puerto)
    if not servidor_socket:
        print("[FATAL] No se pudo vincular el socket del servidor. Abortando.", file=sys.stderr)
        return

    print(f"\n[LISTO] Servidor escuchando peticiones en {host}:{puerto} (TCP).")
    print("-> El servidor confirmará automáticamente la recepción.")
    print("-> Luego podrás escribir tus respuestas por teclado para enviarlas al cliente.")
    print("Presioná [Ctrl + C] para detener el servidor.\n" + "-" * 70)

    try:
        while True:
            cliente_socket, cliente_direccion = servidor_socket.accept()
            atender_cliente(cliente_socket, cliente_direccion, nombre_db)

    except KeyboardInterrupt:
        print("\n\n[APAGANDO] Señal de interrupción por teclado recibida (Ctrl+C).")
    finally:
        servidor_socket.close()
        print("[SERVIDOR DETENIDO] Socket del servidor cerrado correctamente.\n")


# ==============================================================================
# BLOQUE 9: PUNTO DE ENTRADA DEL PROGRAMA (__main__)
# ==============================================================================
if __name__ == "__main__":
    puerto_config = PUERTO_DEFAULT
    db_config = DB_NOMBRE_DEFAULT

    # Soporta argumentos opcionales: python3 servidor.py [puerto] [nombre_db]
    if len(sys.argv) > 1:
        try:
            puerto_config = int(sys.argv[1])
        except ValueError:
            print(f"[AVISO] Puerto '{sys.argv[1]}' no válido. Usando {PUERTO_DEFAULT}.")

    if len(sys.argv) > 2:
        db_config = sys.argv[2]

    iniciar_servidor(host=HOST_DEFAULT, puerto=puerto_config, nombre_db=db_config)
