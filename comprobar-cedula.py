#!/usr/bin/env python3
"""Comprueba lector, cédula y certificados públicos sin solicitar el PIN."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


MODULO_PREDETERMINADO = Path("/usr/lib/pkcs11/libgclib.so")


class ErrorComprobacion(RuntimeError):
    pass


def ejecutar(argumentos: list[str], timeout: int = 15) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argumentos,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )


def exigir_herramientas() -> None:
    ausentes = [
        nombre for nombre in ("opensc-tool", "pkcs11-tool", "openssl")
        if shutil.which(nombre) is None
    ]
    if ausentes:
        raise ErrorComprobacion(
            "Faltan herramientas: " + ", ".join(ausentes)
            + ". Instale los paquetes opensc y openssl."
        )


def analizar_lectores(texto: str) -> list[dict[str, str | bool]]:
    lectores: list[dict[str, str | bool]] = []
    patron = re.compile(r"^\s*(\d+)\s+(Yes|No)\s+(.+?)\s*$", re.MULTILINE)
    for numero, tarjeta, nombre in patron.findall(texto):
        lectores.append({
            "numero": numero,
            "nombre": nombre,
            "tarjeta": tarjeta == "Yes",
        })
    return lectores


def campos_token(texto: str) -> dict[str, str]:
    equivalencias = {
        "token label": "Etiqueta",
        "token manufacturer": "Fabricante",
        "token model": "Modelo",
        "token flags": "Estado",
        "hardware version": "Versión de hardware",
        "firmware version": "Versión de firmware",
        "serial num": "Número de serie",
        "pin min/max": "Longitud del PIN",
    }
    encontrados: dict[str, str] = {}
    for linea in texto.splitlines():
        coincidencia = re.match(r"\s*([^:]+?)\s*:\s*(.*?)\s*$", linea)
        if not coincidencia:
            continue
        clave, valor = coincidencia.groups()
        if clave in equivalencias:
            encontrados[equivalencias[clave]] = valor
    return encontrados


def objetos_certificado(texto: str) -> list[dict[str, str]]:
    objetos: list[dict[str, str]] = []
    for bloque in re.split(r"(?=Certificate Object;)", texto):
        if not bloque.startswith("Certificate Object;"):
            continue
        etiqueta = re.search(r"^\s*label:\s*(.+)$", bloque, re.MULTILINE)
        identificador = re.search(r"^\s*ID:\s*([0-9a-fA-F:]+)\s*$", bloque, re.MULTILINE)
        if identificador:
            objetos.append({
                "etiqueta": etiqueta.group(1).strip() if etiqueta else "Sin etiqueta",
                "id": identificador.group(1).replace(":", "").lower(),
            })
    return objetos


def leer_certificado(modulo: Path, identificador: str) -> bytes:
    resultado = subprocess.run(
        [
            "pkcs11-tool", "--module", str(modulo), "--read-object",
            "--type", "cert", "--id", identificador,
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )
    if resultado.returncode != 0 or not resultado.stdout:
        detalle = resultado.stderr.decode("utf-8", errors="replace").strip()
        raise ErrorComprobacion(f"No se pudo leer el certificado público: {detalle}")
    return resultado.stdout


def describir_certificado(der: bytes) -> dict[str, str]:
    resultado = subprocess.run(
        [
            "openssl", "x509", "-inform", "DER", "-noout", "-nameopt", "utf8",
            "-subject", "-issuer", "-serial", "-dates", "-fingerprint", "-sha256",
        ],
        input=der,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )
    if resultado.returncode != 0:
        detalle = resultado.stderr.decode("utf-8", errors="replace").strip()
        raise ErrorComprobacion(f"OpenSSL no pudo interpretar el certificado: {detalle}")
    equivalencias = {
        "subject": "Titular",
        "issuer": "Emisor",
        "serial": "Serie del certificado",
        "notBefore": "Válido desde",
        "notAfter": "Válido hasta",
        "sha256 Fingerprint": "Huella SHA-256",
    }
    datos: dict[str, str] = {}
    for linea in resultado.stdout.decode("utf-8", errors="replace").splitlines():
        if "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        if clave in equivalencias:
            datos[equivalencias[clave]] = valor.strip()
    return datos


def imprimir_campos(datos: dict[str, str], sangria: str = "  ") -> None:
    for clave, valor in datos.items():
        print(f"{sangria}{clave}: {valor}")


def verificar_pin(modulo: Path, estado_token: str) -> int:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ErrorComprobacion(
            "La verificación del PIN debe ejecutarse directamente en una terminal interactiva."
        )
    estado_normalizado = estado_token.lower()
    riesgos = ("pin count low", "pin final try", "pin locked")
    if any(riesgo in estado_normalizado for riesgo in riesgos):
        raise ErrorComprobacion(
            "El token informa pocos intentos, último intento o bloqueo. No se probará el PIN."
        )
    print("\nADVERTENCIA: un PIN incorrecto consume un intento y varios errores pueden bloquearlo.")
    confirmacion = input("Escriba VERIFICAR para intentar una sola autenticación: ").strip()
    if confirmacion != "VERIFICAR":
        print("[!] Verificación del PIN cancelada; no se realizó ningún intento.")
        return 6
    print("\nEl PIN se solicitará a continuación con entrada oculta.")
    resultado = subprocess.run(
        [
            "pkcs11-tool", "--module", str(modulo), "--login",
            "--list-objects", "--type", "cert",
        ],
        check=False,
    )
    if resultado.returncode == 0:
        print("[✓] PIN correcto: la autenticación con la cédula fue exitosa.")
        return 0
    print(
        "[✗] La autenticación no fue aceptada. No vuelva a intentar sin comprobar el PIN.",
        file=sys.stderr,
    )
    return 7


def comprobar(modulo: Path) -> int:
    exigir_herramientas()
    if not modulo.is_file():
        raise ErrorComprobacion(f"No existe el módulo PKCS#11: {modulo}")

    servicio = ejecutar(["systemctl", "is-active", "pcscd.socket"], timeout=5)
    if servicio.returncode != 0:
        raise ErrorComprobacion(
            "pcscd.socket no está activo. Ejecute: "
            "sudo systemctl enable --now pcscd.socket"
        )

    salida_lectores = ejecutar(["opensc-tool", "--list-readers"])
    lectores = analizar_lectores(salida_lectores.stdout)
    if not lectores:
        print("[✗] No se encontró ningún lector de tarjetas conectado.")
        return 2

    print(f"[✓] Lectores conectados: {len(lectores)}")
    for lector in lectores:
        estado = "cédula o tarjeta insertada" if lector["tarjeta"] else "vacío"
        print(f"  Lector {lector['numero']}: {lector['nombre']} ({estado})")

    con_tarjeta = [lector for lector in lectores if lector["tarjeta"]]
    if not con_tarjeta:
        print("\n[✗] El lector está conectado, pero no tiene una cédula insertada.")
        return 3
    print("\n[✓] Hay una tarjeta insertada en el lector.")

    slots = ejecutar(["pkcs11-tool", "--module", str(modulo), "--list-slots"])
    token = campos_token(slots.stdout)
    if slots.returncode != 0 or not token:
        print("[✗] La tarjeta está presente, pero Classic Client no reconoció el token.")
        return 4

    print("[✓] La cédula fue reconocida mediante PKCS#11.\n")
    print("Información del chip/token:")
    imprimir_campos(token)

    listado = ejecutar([
        "pkcs11-tool", "--module", str(modulo),
        "--list-objects", "--type", "cert",
    ])
    certificados = objetos_certificado(listado.stdout)
    if listado.returncode != 0 or not certificados:
        print("\n[!] No se encontraron certificados públicos legibles sin PIN.")
        return 5

    print(f"\nCertificados públicos encontrados: {len(certificados)}")
    for numero, objeto in enumerate(certificados, start=1):
        print(f"\nCertificado {numero}: {objeto['etiqueta']}")
        der = leer_certificado(modulo, objeto["id"])
        imprimir_campos(describir_certificado(der))

    print("\n[✓] Comprobación terminada. No se solicitó el PIN ni se leyó la clave privada.")
    return 0


def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Comprueba lector, cédula y certificados públicos sin pedir el PIN."
    )
    parser.add_argument(
        "--modulo", type=Path, default=MODULO_PREDETERMINADO,
        help=f"módulo PKCS#11 (predeterminado: {MODULO_PREDETERMINADO})",
    )
    parser.add_argument(
        "--verificar-pin", action="store_true",
        help="solicita el PIN de forma oculta y comprueba una autenticación",
    )
    return parser


def main() -> int:
    args = crear_parser().parse_args()
    try:
        modulo = args.modulo.expanduser().resolve()
        resultado = comprobar(modulo)
        if resultado == 0 and args.verificar_pin:
            slots = ejecutar(["pkcs11-tool", "--module", str(modulo), "--list-slots"])
            token = campos_token(slots.stdout)
            return verificar_pin(modulo, token.get("Estado", ""))
        return resultado
    except subprocess.TimeoutExpired:
        print("ERROR: la comprobación excedió el tiempo de espera.", file=sys.stderr)
        return 1
    except ErrorComprobacion as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nComprobación cancelada.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
