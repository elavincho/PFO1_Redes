#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
CLIENTE DE CHAT CON SOCKETS TCP/IP EN PYTHON
================================================================================
Objetivo didáctico:
  Configurar un cliente de red TCP en Python capaz de conectarse a un servidor
  en localhost:5000, enviar múltiples mensajes interactivos ingresados por el
  usuario, imprimir las respuestas de confirmación ("Mensaje recibido: <timestamp>")
  y finalizar la conexión de forma limpia al escribir la palabra clave "éxito".

Estructura del cliente:
  1. Bloque de Importaciones requeridas.
  2. Bloque de Configuración General y Constantes globales.
  3. Función 'conectar_al_servidor': Creación del socket y 'connect()' con manejo de errores.
  4. Función 'iniciar_chat': Bucle interactivo de envío (sendall), recepción (recv) y comando 'éxito'.
  5. Función 'main' y Bloque de Ejecución Principal (__main__).
================================================================================
"""

# ==============================================================================
# BLOQUE 1: IMPORTACIONES DE BIBLIOTECAS DEL SISTEMA
# ==============================================================================
# 'socket': Módulo de red nativo de Python para crear y manipular puntos de conexión (sockets).
import socket

# 'sys': Módulo para interactuar con el entorno del sistema, parámetros y salidas de error (stderr).
import sys


# ==============================================================================
# BLOQUE 2: CONFIGURACIÓN GENERAL Y CONSTANTES DEL CLIENTE
# ==============================================================================
# Dirección IP del servidor al que nos conectaremos:
# '127.0.0.1' es la dirección de loopback local (localhost).
HOST_DEFAULT = "127.0.0.1"

# Puerto en el que el servidor está escuchando (definido en 5000).
PUERTO_DEFAULT = 5000

# Tamaño del búfer en bytes para recibir respuestas del servidor (1024 bytes = 1 KB).
BUFFER_SIZE = 1024


# ==============================================================================
# BLOQUE 3: CONEXIÓN CON EL SERVIDOR DE SOCKETS
# ==============================================================================
def conectar_al_servidor(host=HOST_DEFAULT, puerto=PUERTO_DEFAULT):
    """
    Crea un socket TCP/IP y establece conexión con el servidor remoto/local.
    
    Explicación de configuraciones clave:
      - 'socket.AF_INET': Familia de direcciones IPv4.
      - 'socket.SOCK_STREAM': Protocolo TCP orientado a la conexión y con garantía de entrega.
      - 'cliente_socket.connect((host, puerto))': Inicia el proceso de saludo de 3 vías (3-way handshake)
        con el servidor. Si el servidor está apagado, lanza 'ConnectionRefusedError'.
        
    Manejo de errores:
      - Captura 'ConnectionRefusedError' cuando el servidor no está en ejecución.
      - Captura 'socket.gaierror' cuando el nombre de host no puede ser resuelto por DNS.
      - Retorna el socket conectado si tuvo éxito, o None si ocurrió un error.
    """
    print(f"[CONECTANDO] Intentando establecer conexión TCP con {host}:{puerto}...")

    try:
        # Paso 1: Instanciar el objeto socket cliente TCP IPv4
        cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Paso 2: Intentar conectar con la tupla (IP, Puerto) del servidor
        cliente_socket.connect((host, puerto))

        print(f"[CONECTADO] Conexión establecida exitosamente con el servidor en {host}:{puerto}.")
        return cliente_socket

    except ConnectionRefusedError:
        # Error típico cuando el servidor no está encendido o el puerto 5000 está cerrado
        print(f"\n[ERROR DE CONEXIÓN] Conexión rechazada en {host}:{puerto}.", file=sys.stderr)
        print("-> Causa probable: El servidor ('servidor.py') no está corriendo.", file=sys.stderr)
        print("-> Solución: Abre otra terminal y ejecuta primero 'python3 servidor.py'.\n", file=sys.stderr)
        return None

    except socket.gaierror:
        # Error de resolución de nombre de host (DNS)
        print(f"\n[ERROR DNS] No se pudo resolver la dirección de host: '{host}'.", file=sys.stderr)
        return None

    except OSError as e:
        # Error genérico a nivel de sistema operativo
        print(f"\n[ERROR DE RED] Error del sistema al intentar conectar: {e}", file=sys.stderr)
        return None

    except Exception as e:
        # Captura de cualquier excepción imprevista
        print(f"\n[ERROR INESPERADO] Error al conectar con el servidor: {e}", file=sys.stderr)
        return None


# ==============================================================================
# BLOQUE 4: BUCLE INTERACTIVO DE ENVÍO Y RECEPCIÓN DE MENSAJES
# ==============================================================================
def iniciar_chat(cliente_socket):
    """
    Gestiona el ciclo de vida del chat interactivo del cliente:
      1. Lee texto del usuario por consola con 'input()'.
      2. Codifica el texto a bytes en formato UTF-8 y lo envía al servidor con 'sendall()'.
      3. Si el usuario escribe 'éxito' (o 'exito'), envía el comando, recibe la despedida y sale.
      4. Espera y muestra la confirmación enviada por el servidor ('Mensaje recibido: <timestamp>').
      5. En el bloque 'finally', cierra el socket para liberar recursos de red.
    """
    print("\n" + "=" * 65)
    print("   CHAT INTERACTIVO CON SERVIDOR TCP (localhost:5000)")
    print("   - Escribí tus mensajes y presioná Enter.")
    print("   - Para finalizar la sesión, escribí: éxito")
    print("=" * 65 + "\n")

    try:
        # Bucle continuo: permite enviar múltiples mensajes sin tener que reconectar cada vez
        while True:
            # Entrada de datos por teclado desde la consola
            try:
                mensaje_usuario = input("Vos > ").strip()
            except (EOFError, KeyboardInterrupt):
                # Si el usuario presiona Ctrl+C o Ctrl+D en la consola, asumimos salida
                print("\n[SALIR] Interrupción por teclado detectada.")
                mensaje_usuario = "éxito"

            # Validamos que el mensaje no esté completamente vacío
            if not mensaje_usuario:
                print("(!) Por favor ingresá algún texto antes de presionar Enter.")
                continue

            # Paso A: Enviar el mensaje codificado en bytes (UTF-8)
            # 'sendall()' asegura que todo el buffer sea transmitido sin fragmentaciones incompletas
            cliente_socket.sendall(mensaje_usuario.encode("utf-8"))

            # Paso B: Evaluar si el usuario envió el comando de salida 'éxito' (o 'exito')
            if mensaje_usuario.lower() in ("éxito", "exito"):
                print("\n[FINALIZANDO] Comando de salida detectado.")

                # Intentamos recibir la confirmación de despedida final enviada por el servidor
                try:
                    cliente_socket.settimeout(2.0)  # Tiempo de espera máximo de 2 segundos
                    despedida = cliente_socket.recv(BUFFER_SIZE).decode("utf-8")
                    if despedida:
                        print(f"Servidor > {despedida}")
                except (socket.timeout, Exception):
                    pass

                print("[DESCONECTADO] Sesión finalizada correctamente. ¡Hasta la próxima!\n")
                break

            # Paso C: Recibir y mostrar la confirmación de recepción INMEDIATAMENTE
            # 'recv()' recibe el primer paquete que el servidor envía en cuanto llega el mensaje
            primer_paquete = cliente_socket.recv(BUFFER_SIZE)

            # Si 'recv()' retorna bytes vacíos (b''), significa que el servidor cerró la conexión
            if not primer_paquete:
                print("\n[AVISO] El servidor cerró la conexión de forma inesperada.")
                break

            # Decodificamos y mostramos de inmediato la confirmación de recibido
            texto_primero = primer_paquete.decode("utf-8")
            lineas_primero = [l.strip() for l in texto_primero.splitlines() if l.strip()]

            tiene_respuesta_operador = False
            for linea in lineas_primero:
                if linea.startswith("Servidor:"):
                    print(f"Servidor > {linea.replace('Servidor:', '', 1).strip()}")
                    tiene_respuesta_operador = True
                elif linea.startswith("Servidor >"):
                    print(linea)
                    tiene_respuesta_operador = True
                else:
                    print(f"Servidor > {linea}")
                    if not linea.startswith("Mensaje recibido:"):
                        tiene_respuesta_operador = True

            # Paso D: Si aún no llegó la respuesta escrita por teclado del servidor,
            # esperamos a que el operador termine de escribir en su consola y presione Enter
            if not tiene_respuesta_operador:
                segundo_paquete = cliente_socket.recv(BUFFER_SIZE)
                if not segundo_paquete:
                    print("\n[AVISO] El servidor cerró la conexión antes de responder.")
                    break

                texto_segundo = segundo_paquete.decode("utf-8")
                lineas_segundo = [l.strip() for l in texto_segundo.splitlines() if l.strip()]
                for linea in lineas_segundo:
                    if linea.startswith("Servidor:"):
                        print(f"Servidor > {linea.replace('Servidor:', '', 1).strip()}")
                    elif linea.startswith("Servidor >"):
                        print(linea)
                    else:
                        print(f"Servidor > {linea}")

            print()

    except ConnectionResetError:
        # Ocurre si el servidor se apagó abruptamente mientras el cliente esperaba respuesta
        print("\n[ERROR] La conexión fue cerrada o reiniciada por el servidor.", file=sys.stderr)
    except BrokenPipeError:
        # Ocurre si intentamos escribir en un socket cuyo extremo remoto ya fue cerrado
        print("\n[ERROR] Tubería rota: el servidor ya no está recibiendo datos.", file=sys.stderr)
    except Exception as e:
        print(f"\n[ERROR] Error durante la transmisión de datos: {e}", file=sys.stderr)
    finally:
        # El bloque 'finally' se ejecuta siempre al salir del bucle
        cliente_socket.close()
        print("[SOCKET CERRADO] Socket del cliente liberado correctamente.")


# ==============================================================================
# BLOQUE 5: PUNTO DE ENTRADA PRINCIPAL DEL CLIENTE (__main__)
# ==============================================================================
def main():
    """
    Función de arranque del cliente:
      - Lee parámetros opcionales de la consola: python3 cliente.py [host] [puerto]
      - Llama a 'conectar_al_servidor()'
      - Si la conexión es exitosa, inicia la interacción con 'iniciar_chat()'
    """
    host = HOST_DEFAULT
    puerto = PUERTO_DEFAULT

    # Permite especificar el host por parámetro (ej: python3 cliente.py 192.168.1.50)
    if len(sys.argv) > 1:
        host = sys.argv[1]

    # Permite especificar el puerto por parámetro (ej: python3 cliente.py 127.0.0.1 5000)
    if len(sys.argv) > 2:
        try:
            puerto = int(sys.argv[2])
        except ValueError:
            print(f"[AVISO] Puerto ingresado '{sys.argv[2]}' no es un número válido. Se usará: {PUERTO_DEFAULT}")

    # Paso 1: Intentar conectarse al servidor
    socket_conectado = conectar_al_servidor(host, puerto)

    # Paso 2: Si el socket está activo, iniciar el bucle de mensajes
    if socket_conectado:
        iniciar_chat(socket_conectado)
    else:
        print("[FIN] No se pudo iniciar el chat debido a un error de conexión.")


# Este condicional ejecuta main() únicamente si el archivo se ejecuta directamente
if __name__ == "__main__":
    main()
