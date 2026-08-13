#!/usr/bin/env python3
"""Instala y diagnostica la cédula uruguaya con chip en Arch Linux y derivados."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


VERSION = "1.0.0"
PAQUETE = "libclassicclient-uruguay"
VERSION_PAQUETE = "7.5.0_b01.02-2"
MODULO_NSS = "Cedula Uruguay Classic Client"
RUTA_PKCS11 = Path("/usr/lib/pkcs11/libgclib.so")

URL_DEB_PUBLICA = "https://archivos.agesic.gub.uy/nextcloud/index.php/s/8kqSb9z4xKABM8T"
URL_DEB_DESCARGA = URL_DEB_PUBLICA + "/download"
URL_DRIVERS = (
    "https://www.gub.uy/agencia-gobierno-electronico-sociedad-informacion-conocimiento/"
    "firma-digital/drivers-para-usar-cedula-digital"
)
SHA256_DEB = "b6fd0150fcea2b952b0d82027324cf3250dea6f42eaac430d6d08ea22eb840ed"

VERSION_SCONNECT = "2.16.1.0"
URL_SCONNECT = (
    "https://www.sconnect.com/extensions/"
    "sconnect-host-v2.16.1.0.tar.gz"
)
SHA256_SCONNECT_TAR = "9c711faee11c193a667ff8be01948eb4f70d9a10b043aa61172bc2bbbcddeef6"
SHA256_SCONNECT_BIN = "48afbe8bea0290dc46e2b2a8a62e40874bced0ddbe1e31eed8dc7dbe4dcfb773"
ID_EXTENSION = "mjhbkkaddmmnkghdnnmkjcgpphnopnfk"

DEPENDENCIAS = [
    "pcsclite", "ccid", "opensc", "nss", "gtk2", "qt5-base", "base-devel"
]

HOME = Path.home()
DATOS = HOME / ".local" / "share" / "cedula-uruguaya-arch"
CACHE = HOME / ".cache" / "cedula-uruguaya-arch"
BACKUPS = DATOS / "backups"
NSSDB = HOME / ".pki" / "nssdb"
HOST_SCONNECT = HOME / ".sconnect" / "sconnect_host_linux"
MANIFIESTOS = {
    "Brave": HOME / ".config" / "BraveSoftware" / "Brave-Browser"
    / "NativeMessagingHosts" / "com.gemalto.sconnect.json",
    "Google Chrome": HOME / ".config" / "google-chrome"
    / "NativeMessagingHosts" / "com.gemalto.sconnect.json",
}


PKGBUILD = f'''pkgname={PAQUETE}
pkgver=7.5.0_b01.02
pkgrel=2
pkgdesc="Thales Classic Client 7.5 para la cedula de identidad uruguaya"
arch=('x86_64')
url="https://www.gub.uy/"
license=('LicenseRef-Thales-Proprietary')
depends=('glibc' 'gcc-libs' 'pcsclite' 'qt5-base' 'gtk2')
optdepends=('ccid: controlador CCID para lectores USB de tarjetas inteligentes')
source=('libclassicclient.deb')
sha256sums=('{SHA256_DEB}')
options=('!strip')

package() {{
  bsdtar -xf data.tar.gz -C "$pkgdir"
  find "$pkgdir" -type d -exec chmod 755 {{}} +
}}
'''


class ErrorInstalacion(RuntimeError):
    pass


def marca(estado: bool) -> str:
    return "[✓]" if estado else "[✗]"


def ejecutar(
    argumentos: list[str], *, comprobar: bool = True, capturar: bool = False,
    timeout: int | None = None, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argumentos,
        check=comprobar,
        text=True,
        stdout=subprocess.PIPE if capturar else None,
        stderr=subprocess.STDOUT if capturar else None,
        timeout=timeout,
        cwd=cwd,
    )


def salida(argumentos: list[str], timeout: int = 15) -> str:
    resultado = ejecutar(
        argumentos, comprobar=False, capturar=True, timeout=timeout
    )
    return resultado.stdout or ""


def existe_comando(nombre: str) -> bool:
    return shutil.which(nombre) is not None


def sha256(ruta: Path) -> str:
    resumen = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def exigir_hash(ruta: Path, esperado: str, descripcion: str) -> None:
    obtenido = sha256(ruta)
    if obtenido != esperado:
        raise ErrorInstalacion(
            f"Hash inesperado para {descripcion}.\n"
            f"Esperado: {esperado}\nObtenido: {obtenido}\n"
            "No se utilizará el archivo. Revise si el proveedor publicó otra versión."
        )


def leer_os_release() -> dict[str, str]:
    datos: dict[str, str] = {}
    for linea in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
        if "=" in linea:
            clave, valor = linea.split("=", 1)
            datos[clave] = valor.strip('"')
    return datos


def sistema_arch_compatible(datos: dict[str, str]) -> bool:
    return datos.get("ID") in {"arch", "cachyos"} or "arch" in datos.get("ID_LIKE", "")


def comprobar_sistema() -> None:
    datos = leer_os_release()
    if not sistema_arch_compatible(datos):
        raise ErrorInstalacion(
            "Este automatizador sólo admite Arch Linux o distribuciones basadas en Arch."
        )
    if platform.machine() != "x86_64":
        raise ErrorInstalacion("Classic Client 7.5 requiere arquitectura x86-64.")
    if os.geteuid() == 0:
        raise ErrorInstalacion(
            "No ejecute todo el script como root. El propio script solicitará sudo para pacman."
        )


def navegadores_abiertos() -> list[str]:
    procesos = salida(["ps", "-eo", "args="], timeout=5).splitlines()
    encontrados: list[str] = []
    if any("/opt/brave" in p or p.strip().startswith("brave") for p in procesos):
        encontrados.append("Brave")
    if any("/opt/google/chrome" in p or p.strip().startswith("google-chrome") for p in procesos):
        encontrados.append("Google Chrome")
    return encontrados


def exigir_navegadores_cerrados() -> None:
    abiertos = navegadores_abiertos()
    if abiertos:
        raise ErrorInstalacion(
            "Cierre completamente estos navegadores antes de continuar: "
            + ", ".join(abiertos)
        )


def nuevo_backup(etiqueta: str) -> Path:
    instante = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = BACKUPS / f"{instante}_{etiqueta}"
    destino.mkdir(parents=True, exist_ok=False)
    return destino


def respaldar_ruta(origen: Path, destino: Path) -> None:
    if not origen.exists() and not origen.is_symlink():
        return
    destino.mkdir(parents=True, exist_ok=True)
    final = destino / origen.name
    if origen.is_dir() and not origen.is_symlink():
        shutil.copytree(origen, final, symlinks=True)
    else:
        shutil.copy2(origen, final, follow_symlinks=False)


def descargar(url: str, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(destino.suffix + ".parcial")
    if temporal.exists():
        temporal.unlink()
    ejecutar([
        "curl", "--fail", "--location", "--show-error", "--progress-bar",
        "--output", str(temporal), url
    ])
    temporal.replace(destino)


def obtener_deb(ruta_indicada: Path | None) -> Path:
    if ruta_indicada:
        ruta = ruta_indicada.expanduser().resolve()
        if not ruta.is_file():
            raise ErrorInstalacion(f"No existe el DEB indicado: {ruta}")
    else:
        ruta = CACHE / "libclassicclient.deb"
        if not ruta.exists() or sha256(ruta) != SHA256_DEB:
            print(f"Descargando Classic Client desde:\n{URL_DEB_PUBLICA}")
            descargar(URL_DEB_DESCARGA, ruta)
    exigir_hash(ruta, SHA256_DEB, "Classic Client 7.5")
    return ruta


def instalar_dependencias(con_okular: bool) -> None:
    paquetes = DEPENDENCIAS + (["okular"] if con_okular else [])
    ejecutar(["sudo", "pacman", "--needed", "-S", *paquetes])
    ejecutar(["sudo", "systemctl", "enable", "--now", "pcscd.socket"])


def paquete_instalado() -> bool:
    return ejecutar(
        ["pacman", "-Q", PAQUETE], comprobar=False, capturar=True
    ).returncode == 0


def construir_e_instalar(deb: Path) -> None:
    if paquete_instalado() and RUTA_PKCS11.is_file():
        print(f"{marca(True)} {PAQUETE} ya está instalado; no se reconstruye.")
        return
    trabajo = CACHE / "build-classicclient"
    if trabajo.exists():
        shutil.rmtree(trabajo)
    trabajo.mkdir(parents=True)
    shutil.copy2(deb, trabajo / "libclassicclient.deb")
    (trabajo / "PKGBUILD").write_text(PKGBUILD, encoding="utf-8")
    ejecutar(["makepkg", "--cleanbuild", "--clean", "--force"], cwd=trabajo)
    candidatos = list(trabajo.glob(f"{PAQUETE}-*.pkg.tar.zst"))
    if len(candidatos) != 1:
        raise ErrorInstalacion("No se encontró exactamente un paquete construido.")
    ejecutar(["sudo", "pacman", "-U", str(candidatos[0])])


def base_nss_inicializada() -> bool:
    return (NSSDB / "cert9.db").is_file() and (NSSDB / "pkcs11.txt").is_file()


def listar_modulos_nss() -> str:
    if not base_nss_inicializada():
        return ""
    return salida(["modutil", "-dbdir", f"sql:{NSSDB}", "-list"], timeout=20)


def configurar_nss() -> None:
    exigir_navegadores_cerrados()
    backup = nuevo_backup("nss")
    respaldar_ruta(NSSDB, backup)
    NSSDB.mkdir(parents=True, exist_ok=True)
    if not base_nss_inicializada():
        ejecutar(["certutil", "-N", "-d", f"sql:{NSSDB}", "--empty-password"])
    if MODULO_NSS not in listar_modulos_nss():
        ejecutar([
            "modutil", "-dbdir", f"sql:{NSSDB}", "-add", MODULO_NSS,
            "-libfile", str(RUTA_PKCS11), "-force"
        ])
    print(f"{marca(True)} NSS configurado. Backup: {backup}")


def extraer_tar_seguro(archivo: Path, destino: Path) -> None:
    with tarfile.open(archivo, "r:gz") as tar:
        raiz = destino.resolve()
        for miembro in tar.getmembers():
            final = (destino / miembro.name).resolve()
            if raiz not in final.parents and final != raiz:
                raise ErrorInstalacion("El TAR contiene una ruta insegura.")
            if miembro.issym() or miembro.islnk():
                raise ErrorInstalacion("El TAR contiene enlaces no admitidos.")
        tar.extractall(destino, filter="data")


def manifiesto_sconnect() -> dict[str, object]:
    return {
        "name": "com.gemalto.sconnect",
        "description": "SConnect Native Messaging Host",
        "path": str(HOST_SCONNECT),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{ID_EXTENSION}/"],
    }


def configurar_sconnect() -> None:
    exigir_navegadores_cerrados()
    archivo = CACHE / f"sconnect-host-v{VERSION_SCONNECT}.tar.gz"
    if not archivo.exists() or sha256(archivo) != SHA256_SCONNECT_TAR:
        print(f"Descargando SConnect {VERSION_SCONNECT} desde Thales.")
        descargar(URL_SCONNECT, archivo)
    exigir_hash(archivo, SHA256_SCONNECT_TAR, "archivo SConnect")
    backup = nuevo_backup("sconnect")
    respaldar_ruta(HOST_SCONNECT, backup)
    for ruta in MANIFIESTOS.values():
        respaldar_ruta(ruta, backup)
    with tempfile.TemporaryDirectory(prefix="cedula-sconnect-") as temporal:
        raiz = Path(temporal)
        extraer_tar_seguro(archivo, raiz)
        candidatos = list(raiz.rglob("sconnect_host_linux"))
        if len(candidatos) != 1:
            raise ErrorInstalacion("No se encontró exactamente un host SConnect en el TAR.")
        exigir_hash(candidatos[0], SHA256_SCONNECT_BIN, "binario SConnect")
        HOST_SCONNECT.parent.mkdir(parents=True, exist_ok=True)
        temporal_host = HOST_SCONNECT.with_suffix(".nuevo")
        shutil.copy2(candidatos[0], temporal_host)
        temporal_host.chmod(0o755)
        temporal_host.replace(HOST_SCONNECT)
    contenido = json.dumps(manifiesto_sconnect(), indent=2, ensure_ascii=False) + "\n"
    for navegador, ruta in MANIFIESTOS.items():
        ruta.parent.mkdir(parents=True, exist_ok=True)
        temporal_json = ruta.with_suffix(".json.nuevo")
        temporal_json.write_text(contenido, encoding="utf-8")
        json.loads(temporal_json.read_text(encoding="utf-8"))
        temporal_json.replace(ruta)
        print(f"{marca(True)} Manifiesto preparado para {navegador}.")
    print(f"{marca(True)} SConnect instalado. Backup: {backup}")
    print(
        "Acción manual pendiente: instalar la extensión SConnect oficial en cada "
        f"navegador que se utilizará. ID: {ID_EXTENSION}"
    )


def diagnosticar() -> bool:
    datos = leer_os_release()
    resultados: list[tuple[str, bool, str]] = []
    resultados.append((
        "Sistema",
        sistema_arch_compatible(datos),
        datos.get("PRETTY_NAME", datos.get("ID", "desconocido")),
    ))
    resultados.append(("Arquitectura", platform.machine() == "x86_64", platform.machine()))
    for comando in ["pacman", "makepkg", "curl", "modutil", "pkcs11-tool"]:
        resultados.append((f"Comando {comando}", existe_comando(comando), shutil.which(comando) or "ausente"))
    resultados.append(("Classic Client", paquete_instalado(), salida(["pacman", "-Q", PAQUETE], 5).strip() or "no instalado"))
    resultados.append(("Módulo PKCS#11", RUTA_PKCS11.is_file(), str(RUTA_PKCS11)))
    activo = salida(["systemctl", "is-active", "pcscd.socket"], 5).strip() == "active"
    resultados.append(("pcscd.socket", activo, "activo" if activo else "inactivo"))
    modulos = listar_modulos_nss()
    resultados.append(("Módulo en NSS", MODULO_NSS in modulos, str(NSSDB)))
    host_ok = HOST_SCONNECT.is_file() and sha256(HOST_SCONNECT) == SHA256_SCONNECT_BIN
    resultados.append(("SConnect host", host_ok, str(HOST_SCONNECT)))
    for navegador, ruta in MANIFIESTOS.items():
        correcto = False
        if ruta.is_file():
            try:
                correcto = json.loads(ruta.read_text(encoding="utf-8")) == manifiesto_sconnect()
            except (json.JSONDecodeError, OSError):
                pass
        resultados.append((f"SConnect {navegador}", correcto, str(ruta)))
    print("\nDiagnóstico de cédula uruguaya en Arch Linux y derivados\n")
    for nombre, correcto, detalle in resultados:
        print(f"{marca(correcto)} {nombre}: {detalle}")
    return all(resultado[1] for resultado in resultados)


def verificar_token() -> bool:
    if not RUTA_PKCS11.is_file():
        print(f"{marca(False)} No existe {RUTA_PKCS11}")
        return False
    resultado = ejecutar([
        "timeout", "20s", "pkcs11-tool", "--module", str(RUTA_PKCS11),
        "--list-slots"
    ], comprobar=False, capturar=True)
    print(resultado.stdout or "")
    correcto = resultado.returncode == 0 and "token" in (resultado.stdout or "").lower()
    print(f"{marca(correcto)} Verificación PKCS#11")
    return correcto


def instalar(args: argparse.Namespace) -> None:
    comprobar_sistema()
    instalar_dependencias(args.con_okular)
    deb = obtener_deb(args.deb)
    construir_e_instalar(deb)
    if not RUTA_PKCS11.is_file():
        raise ErrorInstalacion("La instalación no produjo el módulo PKCS#11 esperado.")
    configurar_nss()
    if not args.sin_sconnect:
        configurar_sconnect()
    print("\nInstalación automatizada terminada.")
    diagnosticar()
    print("\nConecte el lector e inserte la cédula para ejecutar: verificar")


def eliminar_archivo_exacto(ruta: Path) -> None:
    if ruta.is_file() or ruta.is_symlink():
        ruta.unlink()


def desinstalar(args: argparse.Namespace) -> None:
    comprobar_sistema()
    if not args.confirmar:
        raise ErrorInstalacion(
            "La desinstalación requiere --confirmar. Primero revise el modo diagnosticar."
        )
    exigir_navegadores_cerrados()
    backup = nuevo_backup("desinstalacion")
    respaldar_ruta(NSSDB, backup)
    respaldar_ruta(HOST_SCONNECT, backup)
    for ruta in MANIFIESTOS.values():
        respaldar_ruta(ruta, backup)
    if MODULO_NSS in listar_modulos_nss():
        ejecutar([
            "modutil", "-dbdir", f"sql:{NSSDB}", "-delete", MODULO_NSS, "-force"
        ])
    for ruta in MANIFIESTOS.values():
        eliminar_archivo_exacto(ruta)
    eliminar_archivo_exacto(HOST_SCONNECT)
    if paquete_instalado():
        ejecutar(["sudo", "pacman", "-Rns", PAQUETE])
    if args.quitar_okular:
        ejecutar(["sudo", "pacman", "-Rns", "okular"], comprobar=False)
    print(f"Desinstalación terminada. Backup: {backup}")


def auto_prueba() -> None:
    assert hashlib.sha256(b"abc").hexdigest() == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    manifiesto = manifiesto_sconnect()
    assert manifiesto["name"] == "com.gemalto.sconnect"
    assert str(HOME) in str(manifiesto["path"])
    assert ID_EXTENSION in str(manifiesto["allowed_origins"])
    assert "install_sconnect_host.sh" not in PKGBUILD
    assert SHA256_DEB in PKGBUILD
    assert sistema_arch_compatible({"ID": "arch"})
    assert sistema_arch_compatible({"ID": "cachyos"})
    assert sistema_arch_compatible({"ID": "endeavouros", "ID_LIKE": "arch"})
    assert not sistema_arch_compatible({"ID": "ubuntu", "ID_LIKE": "debian"})
    with tempfile.TemporaryDirectory() as temporal:
        ruta = Path(temporal) / "archivo"
        ruta.write_bytes(b"abc")
        exigir_hash(ruta, hashlib.sha256(b"abc").hexdigest(), "autoprueba")
    print(f"{marca(True)} Autopruebas internas completadas.")


def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Automatiza la cédula uruguaya con chip en Arch Linux y derivados."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    sub = parser.add_subparsers(dest="accion", required=True)
    instalar_p = sub.add_parser("instalar", help="instala y configura los componentes")
    instalar_p.add_argument("--deb", type=Path, help="usa un DEB local en lugar de descargarlo")
    instalar_p.add_argument("--con-okular", action="store_true", help="instala también Okular")
    instalar_p.add_argument("--sin-sconnect", action="store_true", help="omite el host web SConnect")
    sub.add_parser("diagnosticar", help="muestra el estado sin modificar el sistema")
    sub.add_parser("verificar", help="comprueba el token PKCS#11 sin solicitar PIN")
    sub.add_parser("autoprueba", help="ejecuta pruebas internas sin modificar el sistema")
    quitar = sub.add_parser("desinstalar", help="retira lo instalado por el automatizador")
    quitar.add_argument("--confirmar", action="store_true", help="confirma la operación")
    quitar.add_argument("--quitar-okular", action="store_true", help="también solicita retirar Okular")
    return parser


def main() -> int:
    args = crear_parser().parse_args()
    try:
        if args.accion == "instalar":
            instalar(args)
        elif args.accion == "diagnosticar":
            return 0 if diagnosticar() else 2
        elif args.accion == "verificar":
            return 0 if verificar_token() else 3
        elif args.accion == "desinstalar":
            desinstalar(args)
        elif args.accion == "autoprueba":
            auto_prueba()
        return 0
    except (ErrorInstalacion, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
