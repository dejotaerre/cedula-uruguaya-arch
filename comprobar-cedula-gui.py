#!/usr/bin/env python3
"""Interfaz GTK 4 para comprobar la cédula y verificar opcionalmente el PIN."""

from __future__ import annotations

import importlib.util
import errno
import os
import pty
import select
import subprocess
import sys
import threading
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402


RAIZ = Path(__file__).resolve().parent
RUTA_NUCLEO = RAIZ / "comprobar-cedula.py"
MODULO_PKCS11 = Path("/usr/lib/pkcs11/libgclib.so")


def cargar_nucleo():
    especificacion = importlib.util.spec_from_file_location("comprobar_cedula", RUTA_NUCLEO)
    if especificacion is None or especificacion.loader is None:
        raise RuntimeError(f"No se pudo cargar {RUTA_NUCLEO}")
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


NUCLEO = cargar_nucleo()


def estado_pin_riesgoso(estado: str) -> bool:
    normalizado = estado.lower()
    riesgos = ("pin count low", "pin final try", "pin locked")
    return any(riesgo in normalizado for riesgo in riesgos)


def ejecutar_con_pin_pty(argumentos: list[str], pin: bytearray, timeout: int = 30) -> str:
    maestro, esclavo = pty.openpty()
    proceso: subprocess.Popen[bytes] | None = None
    salida = bytearray()
    enviado = False
    try:
        proceso = subprocess.Popen(
            argumentos,
            stdin=esclavo,
            stdout=esclavo,
            stderr=esclavo,
            close_fds=True,
        )
        os.close(esclavo)
        esclavo = -1
        limite = time.monotonic() + timeout
        while True:
            restante = limite - time.monotonic()
            if restante <= 0:
                proceso.terminate()
                proceso.wait(timeout=5)
                return "tiempo_agotado"
            legibles, _, _ = select.select([maestro], [], [], min(0.25, restante))
            if legibles:
                try:
                    bloque = os.read(maestro, 4096)
                except OSError as error:
                    if error.errno == errno.EIO:
                        break
                    raise
                if not bloque:
                    break
                salida.extend(bloque)
                if not enviado and b"Please enter User PIN:" in salida:
                    os.write(maestro, bytes(pin) + b"\n")
                    for indice in range(len(pin)):
                        pin[indice] = 0
                    enviado = True
            if proceso.poll() is not None and not legibles:
                break

        codigo = proceso.wait(timeout=5)
        texto = salida.decode("utf-8", errors="replace")
        if not enviado:
            return "sin_solicitud"
        if codigo == 0:
            return "correcto"
        if "CKR_PIN_LOCKED" in texto:
            return "bloqueado"
        if "CKR_PIN_INCORRECT" in texto or "CKR_PIN_INVALID" in texto:
            return "incorrecto"
        return "error"
    finally:
        for indice in range(len(pin)):
            pin[indice] = 0
        for indice in range(len(salida)):
            salida[indice] = 0
        if esclavo >= 0:
            os.close(esclavo)
        os.close(maestro)
        if proceso is not None and proceso.poll() is None:
            proceso.terminate()
            proceso.wait(timeout=5)


def autenticar_pin(pin: bytearray) -> str:
    return ejecutar_con_pin_pty(
        [
            "pkcs11-tool", "--module", str(MODULO_PKCS11), "--login",
            "--list-objects", "--type", "cert",
        ],
        pin,
    )


def recopilar_informacion() -> dict[str, object]:
    NUCLEO.exigir_herramientas()
    if not MODULO_PKCS11.is_file():
        raise NUCLEO.ErrorComprobacion(f"No existe el módulo PKCS#11: {MODULO_PKCS11}")

    servicio = NUCLEO.ejecutar(["systemctl", "is-active", "pcscd.socket"], timeout=5)
    if servicio.returncode != 0:
        raise NUCLEO.ErrorComprobacion("El servicio pcscd.socket no está activo.")

    salida_lectores = NUCLEO.ejecutar(["opensc-tool", "--list-readers"])
    lectores = NUCLEO.analizar_lectores(salida_lectores.stdout)
    if not lectores:
        return {"lector": False, "tarjeta": False, "token": False, "estado_token": "", "lectores": [], "texto": ""}

    con_tarjeta = [lector for lector in lectores if lector["tarjeta"]]
    if not con_tarjeta:
        return {"lector": True, "tarjeta": False, "token": False, "estado_token": "", "lectores": lectores, "texto": ""}

    slots = NUCLEO.ejecutar([
        "pkcs11-tool", "--module", str(MODULO_PKCS11), "--list-slots",
    ])
    token = NUCLEO.campos_token(slots.stdout)
    if slots.returncode != 0 or not token:
        return {"lector": True, "tarjeta": True, "token": False, "estado_token": "", "lectores": lectores, "texto": ""}

    listado = NUCLEO.ejecutar([
        "pkcs11-tool", "--module", str(MODULO_PKCS11),
        "--list-objects", "--type", "cert",
    ])
    objetos = NUCLEO.objetos_certificado(listado.stdout)
    certificados: list[dict[str, str]] = []
    for objeto in objetos:
        der = NUCLEO.leer_certificado(MODULO_PKCS11, objeto["id"])
        datos = NUCLEO.describir_certificado(der)
        datos = {"Certificado": objeto["etiqueta"], **datos}
        certificados.append(datos)

    lineas = ["INFORMACIÓN DEL CHIP / TOKEN", ""]
    lineas.extend(f"{clave}: {valor}" for clave, valor in token.items())
    for numero, certificado in enumerate(certificados, start=1):
        lineas.extend(["", f"CERTIFICADO PÚBLICO {numero}", ""])
        lineas.extend(f"{clave}: {valor}" for clave, valor in certificado.items())

    return {
        "lector": True,
        "tarjeta": True,
        "token": True,
        "estado_token": token.get("Estado", ""),
        "lectores": lectores,
        "certificados": certificados,
        "texto": "\n".join(lineas),
    }


class VentanaCedula(Adw.ApplicationWindow):
    def __init__(self, aplicacion: Adw.Application) -> None:
        super().__init__(application=aplicacion)
        self.set_title("Cédula uruguaya")
        self.set_default_size(780, 720)
        self.set_size_request(580, 520)
        self.estado_token = ""
        self.pin_intentado = False

        barra = Adw.HeaderBar()
        barra.set_title_widget(Adw.WindowTitle(title="Cédula uruguaya", subtitle="Comprobador para Arch Linux"))

        self.boton_actualizar = Gtk.Button(label="Comprobar")
        self.boton_actualizar.add_css_class("suggested-action")
        self.boton_actualizar.connect("clicked", self.al_comprobar)
        barra.pack_end(self.boton_actualizar)

        self.spinner = Gtk.Spinner()
        barra.pack_end(self.spinner)

        vista = Adw.ToolbarView()
        vista.add_top_bar(barra)

        barra_inferior = Gtk.ActionBar()
        self.boton_copiar = Gtk.Button(label="Copiar información")
        self.boton_copiar.set_sensitive(False)
        self.boton_copiar.connect("clicked", self.al_copiar)
        barra_inferior.pack_end(self.boton_copiar)
        vista.add_bottom_bar(barra_inferior)

        self.toast = Adw.ToastOverlay()
        vista.set_content(self.toast)
        self.set_content(vista)

        desplazamiento = Gtk.ScrolledWindow(vexpand=True)
        self.toast.set_child(desplazamiento)

        contenido = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        contenido.set_margin_top(24)
        contenido.set_margin_bottom(24)
        contenido.set_margin_start(24)
        contenido.set_margin_end(24)
        desplazamiento.set_child(contenido)

        aviso = Adw.Banner(title="La consulta pública no pide PIN. La verificación opcional permite un solo intento.")
        aviso.set_revealed(True)
        contenido.append(aviso)

        grupo_estado = Adw.PreferencesGroup(title="Estado")
        contenido.append(grupo_estado)
        self.fila_lector = self.crear_fila("Lector", "Pendiente de comprobación")
        self.fila_tarjeta = self.crear_fila("Cédula insertada", "Pendiente de comprobación")
        self.fila_token = self.crear_fila("Chip y certificado", "Pendiente de comprobación")
        grupo_estado.add(self.fila_lector)
        grupo_estado.add(self.fila_tarjeta)
        grupo_estado.add(self.fila_token)

        grupo_pin = Adw.PreferencesGroup(title="Verificación del PIN")
        contenido.append(grupo_pin)
        self.fila_pin = Adw.ActionRow(
            title="Comprobar el PIN de la cédula",
            subtitle="Opcional. Se permite un solo intento por apertura.",
        )
        grupo_pin.add(self.fila_pin)
        self.boton_pin = Gtk.Button(label="Introducir PIN…")
        self.boton_pin.add_css_class("suggested-action")
        self.boton_pin.set_valign(Gtk.Align.CENTER)
        self.boton_pin.set_sensitive(False)
        self.boton_pin.connect("clicked", self.al_verificar_pin)
        self.fila_pin.add_suffix(self.boton_pin)
        self.fila_pin.set_activatable_widget(self.boton_pin)

        grupo_datos = Adw.PreferencesGroup(title="Información pública")
        contenido.append(grupo_datos)

        caja_datos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        caja_datos.add_css_class("card")
        caja_datos.set_margin_top(4)
        grupo_datos.add(caja_datos)

        self.texto = Gtk.TextView(editable=False, cursor_visible=False, monospace=True)
        self.texto.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.texto.set_left_margin(14)
        self.texto.set_right_margin(14)
        self.texto.set_top_margin(14)
        self.texto.set_bottom_margin(14)
        self.texto.get_buffer().set_text("Pulse Comprobar para leer el estado del dispositivo.")

        zona_texto = Gtk.ScrolledWindow(min_content_height=280, vexpand=True)
        zona_texto.set_child(self.texto)
        caja_datos.append(zona_texto)

        GLib.idle_add(self.iniciar_comprobacion)

    @staticmethod
    def crear_fila(titulo: str, subtitulo: str) -> Adw.ActionRow:
        fila = Adw.ActionRow(title=titulo, subtitle=subtitulo)
        icono = Gtk.Image.new_from_icon_name("content-loading-symbolic")
        icono.set_tooltip_text("Pendiente")
        fila.add_suffix(icono)
        fila.icono_estado = icono
        return fila

    @staticmethod
    def actualizar_fila(fila: Adw.ActionRow, correcto: bool, subtitulo: str) -> None:
        fila.set_subtitle(subtitulo)
        icono = "emblem-ok-symbolic" if correcto else "dialog-error-symbolic"
        fila.icono_estado.set_from_icon_name(icono)
        fila.icono_estado.set_tooltip_text("Correcto" if correcto else "No disponible")

    def al_comprobar(self, _boton: Gtk.Button) -> None:
        self.iniciar_comprobacion()

    def iniciar_comprobacion(self) -> bool:
        self.boton_actualizar.set_sensitive(False)
        self.boton_copiar.set_sensitive(False)
        self.spinner.start()
        self.texto.get_buffer().set_text("Comprobando lector y cédula…")
        hilo = threading.Thread(target=self.trabajo_comprobacion, daemon=True)
        hilo.start()
        return GLib.SOURCE_REMOVE

    def trabajo_comprobacion(self) -> None:
        try:
            resultado = recopilar_informacion()
            GLib.idle_add(self.mostrar_resultado, resultado)
        except Exception as error:
            GLib.idle_add(self.mostrar_error, str(error))

    def mostrar_resultado(self, resultado: dict[str, object]) -> bool:
        self.spinner.stop()
        self.boton_actualizar.set_sensitive(True)

        lectores = resultado.get("lectores", [])
        nombre_lector = lectores[0]["nombre"] if lectores else "No se encontró ningún lector"
        self.actualizar_fila(self.fila_lector, bool(resultado["lector"]), str(nombre_lector))

        tarjeta = bool(resultado["tarjeta"])
        self.actualizar_fila(
            self.fila_tarjeta, tarjeta,
            "Cédula o tarjeta presente" if tarjeta else "El lector está vacío",
        )

        token = bool(resultado["token"])
        self.estado_token = str(resultado.get("estado_token", ""))
        self.actualizar_fila(
            self.fila_token, token,
            "Cédula reconocida mediante PKCS#11" if token else "No se reconoció una cédula compatible",
        )
        puede_verificar = token and not estado_pin_riesgoso(self.estado_token) and not self.pin_intentado
        self.boton_pin.set_sensitive(puede_verificar)
        if estado_pin_riesgoso(self.estado_token):
            self.fila_pin.set_subtitle("Deshabilitado porque el token informa riesgo de bloqueo.")
        elif puede_verificar:
            self.fila_pin.set_subtitle("Disponible. Pulse Introducir PIN… para abrir el campo protegido.")
        elif self.pin_intentado:
            self.fila_pin.set_subtitle("Ya se utilizó el único intento permitido en esta apertura.")
        else:
            self.fila_pin.set_subtitle("Disponible cuando la cédula sea reconocida.")

        texto = str(resultado.get("texto", ""))
        hay_informacion = bool(texto)
        if not hay_informacion:
            texto = "No hay información pública disponible para mostrar."
        self.texto.get_buffer().set_text(texto)
        self.boton_copiar.set_sensitive(hay_informacion)
        return GLib.SOURCE_REMOVE

    def mostrar_error(self, mensaje: str) -> bool:
        self.spinner.stop()
        self.boton_actualizar.set_sensitive(True)
        self.boton_copiar.set_sensitive(False)
        self.texto.get_buffer().set_text(f"No se pudo completar la comprobación.\n\n{mensaje}")
        self.toast.add_toast(Adw.Toast(title="La comprobación encontró un error", timeout=4))
        return GLib.SOURCE_REMOVE

    def al_copiar(self, _boton: Gtk.Button) -> None:
        buffer = self.texto.get_buffer()
        texto = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
        portapapeles = Gdk.Display.get_default().get_clipboard()
        portapapeles.set(texto)
        self.toast.add_toast(Adw.Toast(title="Información copiada", timeout=2))

    def al_verificar_pin(self, _boton: Gtk.Button) -> None:
        if self.pin_intentado:
            self.toast.add_toast(Adw.Toast(title="Ya se realizó el único intento permitido", timeout=3))
            return
        if estado_pin_riesgoso(self.estado_token):
            self.toast.add_toast(Adw.Toast(title="El token informa riesgo de bloqueo; operación cancelada", timeout=4))
            return

        entrada = Gtk.Entry(
            editable=False,
            can_focus=True,
            placeholder_text="Escriba el PIN",
            width_chars=18,
            hexpand=True,
        )
        pin = bytearray()
        teclado = Gtk.EventControllerKey()
        teclado.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        entrada.add_controller(teclado)

        caja = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        etiqueta_pin = Gtk.Label(label="PIN de la cédula", xalign=0)
        caja.append(etiqueta_pin)
        caja.append(entrada)
        indicador = Gtk.Label(label="Ningún dígito introducido", xalign=0)
        indicador.add_css_class("dim-label")
        caja.append(indicador)
        teclado.connect("key-pressed", self.al_pulsar_tecla_pin, pin, entrada, indicador)
        nota = Gtk.Label(
            label="El PIN no se guardará. Un valor incorrecto consume un intento.",
            wrap=True,
            xalign=0,
        )
        nota.add_css_class("dim-label")
        caja.append(nota)

        dialogo = Adw.AlertDialog(
            heading="Verificar el PIN",
            body="Se realizará una sola autenticación de lectura. Revise el PIN antes de continuar.",
        )
        dialogo.set_extra_child(caja)
        dialogo.add_response("cancelar", "Cancelar")
        dialogo.add_response("verificar", "Verificar")
        dialogo.set_default_response("verificar")
        dialogo.set_close_response("cancelar")
        dialogo.set_response_appearance("verificar", Adw.ResponseAppearance.SUGGESTED)
        dialogo.connect("response", self.al_responder_pin, pin)
        dialogo.present(self)
        GLib.idle_add(entrada.grab_focus)

    def actualizar_indicador_pin(self, indicador: Gtk.Label, cantidad: int) -> None:
        if cantidad == 0:
            indicador.set_text("Ningún dígito introducido")
            return
        puntos = " ".join("●" for _ in range(cantidad))
        indicador.set_text(f"{puntos}  —  {cantidad} dígitos")

    def al_pulsar_tecla_pin(
        self,
        controlador: Gtk.EventControllerKey,
        tecla: int,
        _codigo: int,
        _estado: Gdk.ModifierType,
        pin: bytearray,
        entrada: Gtk.Entry,
        indicador: Gtk.Label,
    ) -> bool:
        if tecla == Gdk.KEY_BackSpace:
            if pin:
                pin.pop()
            entrada.set_text("●" * len(pin))
            entrada.set_position(-1)
            self.actualizar_indicador_pin(indicador, len(pin))
            return True
        caracter = chr(Gdk.keyval_to_unicode(tecla)) if Gdk.keyval_to_unicode(tecla) else ""
        if caracter.isascii() and caracter.isdigit():
            if len(pin) < 8:
                pin.extend(caracter.encode("ascii"))
            entrada.set_text("●" * len(pin))
            entrada.set_position(-1)
            self.actualizar_indicador_pin(indicador, len(pin))
            return True
        return False

    def al_responder_pin(
        self, _dialogo: Adw.AlertDialog, respuesta: str, pin: bytearray
    ) -> None:
        if respuesta != "verificar":
            for indice in range(len(pin)):
                pin[indice] = 0
            return
        if not pin:
            self.toast.add_toast(Adw.Toast(title="No se introdujo ningún PIN", timeout=3))
            return
        if not 4 <= len(pin) <= 8:
            self.toast.add_toast(Adw.Toast(title="El PIN debe contener entre 4 y 8 dígitos", timeout=4))
            for indice in range(len(pin)):
                pin[indice] = 0
            return
        self.pin_intentado = True
        self.boton_pin.set_sensitive(False)
        self.boton_actualizar.set_sensitive(False)
        self.spinner.start()
        hilo = threading.Thread(target=self.trabajo_pin, args=(pin,), daemon=True)
        hilo.start()

    def trabajo_pin(self, pin: bytearray) -> None:
        try:
            resultado = autenticar_pin(pin)
            GLib.idle_add(self.mostrar_resultado_pin, resultado)
        except Exception as error:
            GLib.idle_add(self.mostrar_error_pin, str(error))

    def mostrar_resultado_pin(self, resultado: str) -> bool:
        self.spinner.stop()
        self.boton_actualizar.set_sensitive(True)
        mensajes = {
            "correcto": "PIN correcto: autenticación exitosa",
            "incorrecto": "PIN rechazado. No vuelva a intentar sin comprobarlo",
            "bloqueado": "El token informa que el PIN está bloqueado",
            "sin_solicitud": "No se pudo abrir el diálogo seguro de PIN",
            "tiempo_agotado": "La solicitud de PIN agotó el tiempo de espera",
            "error": "La autenticación no pudo completarse",
        }
        mensaje = mensajes.get(resultado, "Resultado de autenticación desconocido")
        self.toast.add_toast(Adw.Toast(title=mensaje, timeout=5))
        if resultado == "correcto":
            self.actualizar_fila(self.fila_token, True, "Cédula reconocida y PIN verificado")
            self.fila_pin.set_subtitle("PIN verificado correctamente.")
        else:
            self.fila_pin.set_subtitle("Intento finalizado. Cierre y reabra sólo después de comprobar el PIN.")
        return GLib.SOURCE_REMOVE

    def mostrar_error_pin(self, mensaje: str) -> bool:
        self.spinner.stop()
        self.boton_actualizar.set_sensitive(True)
        self.fila_pin.set_subtitle("No se pudo completar la verificación del PIN.")
        self.toast.add_toast(Adw.Toast(title=f"No se pudo verificar el PIN: {mensaje}", timeout=5))
        return GLib.SOURCE_REMOVE


class AplicacionCedula(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id="io.github.dejotaerre.CedulaUruguayaArch")

    def do_activate(self) -> None:
        ventana = self.props.active_window
        if ventana is None:
            ventana = VentanaCedula(self)
        ventana.present()


def main() -> int:
    aplicacion = AplicacionCedula()
    return aplicacion.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
