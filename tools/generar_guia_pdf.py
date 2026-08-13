from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph,
    Preformatted, Spacer, Table, TableStyle, KeepTogether
)


RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
SALIDA = RAIZ_PROYECTO / "docs" / "Guia_Cedula_Uruguaya_Arch.pdf"

pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/TTF/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DejaVuMono", "/usr/share/fonts/TTF/DejaVuSansMono.ttf"))

AZUL = colors.HexColor("#173F6D")
CELESTE = colors.HexColor("#2E86C1")
AMARILLO = colors.HexColor("#F4C542")
GRIS = colors.HexColor("#4A5560")
GRIS_CLARO = colors.HexColor("#EEF3F7")
ROJO_CLARO = colors.HexColor("#FFF0EE")
VERDE_CLARO = colors.HexColor("#EAF7EF")

estilos_base = getSampleStyleSheet()
titulo = ParagraphStyle(
    "Titulo", fontName="DejaVu-Bold", fontSize=24, leading=29,
    textColor=AZUL, alignment=TA_LEFT, spaceAfter=14
)
subtitulo = ParagraphStyle(
    "Subtitulo", fontName="DejaVu", fontSize=12, leading=17,
    textColor=GRIS, spaceAfter=18
)
h1 = ParagraphStyle(
    "H1", fontName="DejaVu-Bold", fontSize=17, leading=21,
    textColor=AZUL, spaceBefore=8, spaceAfter=10, keepWithNext=True
)
h2 = ParagraphStyle(
    "H2", fontName="DejaVu-Bold", fontSize=12.5, leading=16,
    textColor=CELESTE, spaceBefore=9, spaceAfter=5, keepWithNext=True
)
cuerpo = ParagraphStyle(
    "Cuerpo", fontName="DejaVu", fontSize=9.4, leading=14,
    textColor=colors.HexColor("#20262C"), spaceAfter=6
)
lista = ParagraphStyle(
    "Lista", parent=cuerpo, leftIndent=13, firstLineIndent=-8,
    bulletIndent=3, spaceAfter=4
)
codigo = ParagraphStyle(
    "Codigo", fontName="DejaVuMono", fontSize=7.4, leading=10.2,
    leftIndent=7, rightIndent=7, borderPadding=7,
    backColor=colors.HexColor("#18222C"), textColor=colors.HexColor("#F4F7FA"),
    borderColor=colors.HexColor("#18222C"), borderWidth=0.5,
    borderRadius=3, spaceBefore=4, spaceAfter=8
)
nota = ParagraphStyle(
    "Nota", parent=cuerpo, fontSize=8.7, leading=13,
    leftIndent=8, rightIndent=8, borderPadding=8,
    backColor=GRIS_CLARO, borderColor=CELESTE,
    borderWidth=0.7, borderRadius=3, spaceBefore=5, spaceAfter=9
)
alerta = ParagraphStyle(
    "Alerta", parent=nota, backColor=ROJO_CLARO,
    borderColor=colors.HexColor("#D85B4B")
)
exito = ParagraphStyle(
    "Exito", parent=nota, backColor=VERDE_CLARO,
    borderColor=colors.HexColor("#2D8A57")
)
pie = ParagraphStyle(
    "Pie", fontName="DejaVu", fontSize=7.2, leading=9,
    textColor=colors.HexColor("#66727D"), alignment=TA_CENTER
)


def cabecera_pie(canvas, doc):
    canvas.saveState()
    ancho, alto = A4
    canvas.setFillColor(AZUL)
    canvas.rect(0, alto - 12 * mm, ancho, 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(AMARILLO)
    canvas.rect(0, alto - 12 * mm, 7 * mm, 12 * mm, fill=1, stroke=0)
    canvas.setFont("DejaVu-Bold", 8)
    canvas.setFillColor(colors.white)
    canvas.drawString(15 * mm, alto - 8 * mm, "Cédula uruguaya con chip en Arch Linux")
    canvas.setStrokeColor(colors.HexColor("#CBD5DF"))
    canvas.line(18 * mm, 13 * mm, ancho - 18 * mm, 13 * mm)
    canvas.setFont("DejaVu", 7)
    canvas.setFillColor(colors.HexColor("#64717D"))
    canvas.drawString(18 * mm, 8.5 * mm, "Guía comunitaria - versión verificada en agosto de 2026")
    canvas.drawRightString(ancho - 18 * mm, 8.5 * mm, f"Página {doc.page}")
    canvas.restoreState()


doc = BaseDocTemplate(
    str(SALIDA), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
    topMargin=19 * mm, bottomMargin=18 * mm,
    title="Guía para usar la cédula uruguaya con chip en Arch Linux",
    author="Guía comunitaria para usuarios de Arch Linux y derivados"
)
marco = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
doc.addPageTemplates([PageTemplate(id="guia", frames=[marco], onPage=cabecera_pie)])

historia = []


def P(texto, estilo=cuerpo):
    historia.append(Paragraph(texto, estilo))


def H1(texto):
    historia.append(Paragraph(texto, h1))


def H2(texto):
    historia.append(Paragraph(texto, h2))


def C(texto):
    bloque = Preformatted(texto.strip("\n"), codigo)
    caja = Table([[bloque]], colWidths=[doc.width])
    caja.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#18222C")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#18222C")),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    historia.append(KeepTogether([caja, Spacer(1, 3 * mm)]))


def B(texto):
    historia.append(Paragraph("• " + texto, lista))


def N(texto, estilo=nota):
    historia.append(Paragraph(texto, estilo))


historia.append(Spacer(1, 13 * mm))
P("GUÍA PRÁCTICA", ParagraphStyle(
    "Kicker", fontName="DejaVu-Bold", fontSize=9, textColor=CELESTE,
    tracking=1.2, spaceAfter=8
))
P("Cédula uruguaya con chip en Arch Linux y derivados", titulo)
P(
    "Instalación segura de Classic Client 7.5, integración con Brave y Google Chrome, "
    "firma oficial mediante firma.gub.uy y firma local de PDF con Okular.", subtitulo
)
tabla_portada = Table([
    [Paragraph("Probado con", h2), Paragraph("CachyOS x86-64; diseñado para Arch Linux y derivados compatibles. Classic Client 7.5, Brave/Chromium, SConnect 2.16.1 y Okular 26.04", cuerpo)],
    [Paragraph("Nivel", h2), Paragraph("Intermedio. Requiere utilizar la terminal y revisar cuidadosamente nombres de archivo y hashes.", cuerpo)],
    [Paragraph("Objetivo", h2), Paragraph("Crear una instalación administrada por pacman, reversible y sin ejecutar los scripts incompatibles del paquete Ubuntu.", cuerpo)],
], colWidths=[34 * mm, 122 * mm])
tabla_portada.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), GRIS_CLARO),
    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5DF")),
    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5DF")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
historia.append(tabla_portada)
historia.append(Spacer(1, 9 * mm))
N(
    "<b>Privacidad:</b> esta guía no contiene nombres, números de documento ni datos de certificados personales. "
    "La clave privada permanece dentro del chip de la cédula.", exito
)
N(
    "<b>Importante:</b> no instalar el DEB directamente ni ejecutar sus scripts con sudo. El instalador oficial fue creado para Ubuntu y contiene acciones incompatibles con Arch Linux y sus derivados.",
    alerta
)
P("Fuentes oficiales", h2)
P(
    "Descarga directa de Classic Client 7.5: https://archivos.agesic.gub.uy/nextcloud/index.php/s/8kqSb9z4xKABM8T<br/>"
    "Página institucional de drivers: https://www.gub.uy/agencia-gobierno-electronico-sociedad-informacion-conocimiento/firma-digital/drivers-para-usar-cedula-digital<br/>"
    "Firma oficial: https://firma.gub.uy/<br/>"
    "Actualización SConnect: https://www.sconnect.com/update/",
    cuerpo
)
historia.append(PageBreak())
historia.append(Spacer(1, 12 * mm))

H1("1. Qué se instalará")
P("La solución completa tiene cuatro capas independientes:")
for item in [
    "<b>PC/SC y CCID:</b> permiten que Linux detecte el lector y la tarjeta.",
    "<b>Classic Client:</b> aporta el módulo privativo PKCS#11 para la cédula uruguaya.",
    "<b>NSS:</b> permite que Brave, Chrome, Poppler y Okular encuentren el certificado.",
    "<b>SConnect:</b> conecta firma.gub.uy con el dispositivo local desde el navegador."
]:
    B(item)
N("SConnect sólo es necesario para el flujo web de firma.gub.uy. Okular firma localmente mediante NSS y no necesita SConnect.")

H1("2. Preparar Arch Linux o un derivado")
H2("2.1 Instalar dependencias")
C("""sudo pacman -S --needed pcsclite ccid opensc nss gtk2 qt5-base base-devel
sudo systemctl enable --now pcscd.socket""")
H2("2.2 Comprobar lector y tarjeta")
C("pcsc_scan")
P("Con el lector conectado y la cédula insertada debe aparecer un lector y el estado <b>Card inserted</b>. Salir con Ctrl+C.")
N("Si el lector no aparece aquí, todavía no es momento de instalar Classic Client. Primero debe resolverse la detección USB/PCSC.", alerta)

H1("3. Descargar Classic Client 7.5")
P("Descargar <b>Classic Client versión 7.5 para Ubuntu 64 bits</b> desde este enlace directo de AGESIC:")
C("https://archivos.agesic.gub.uy/nextcloud/index.php/s/8kqSb9z4xKABM8T")
N(
    "<b>Si la URL de descarga directa no funciona:</b> revisar la página institucional de drivers para obtener el enlace vigente:<br/>"
    "https://www.gub.uy/agencia-gobierno-electronico-sociedad-informacion-conocimiento/firma-digital/drivers-para-usar-cedula-digital"
)
C("""file ~/Descargas/libclassicclient_7.5.0-b01.02_Uruguay_ubuntu.amd64.deb
sha256sum ~/Descargas/libclassicclient_7.5.0-b01.02_Uruguay_ubuntu.amd64.deb""")
P("El paquete verificado durante la preparación de esta guía produjo:")
C("b6fd0150fcea2b952b0d82027324cf3250dea6f42eaac430d6d08ea22eb840ed")
N("Si AGESIC publica otra versión, el nombre y el hash cambiarán. No reutilizar este hash para un archivo distinto.", alerta)

historia.append(PageBreak())
historia.append(Spacer(1, 12 * mm))
H1("4. Convertir el DEB en un paquete nativo de pacman")
H2("4.1 Crear el directorio")
C("""mkdir -p ~/classicclient-uruguay-arch
cd ~/classicclient-uruguay-arch
cp ~/Descargas/libclassicclient_7.5.0-b01.02_Uruguay_ubuntu.amd64.deb \\
   ./libclassicclient.deb""")
H2("4.2 Crear PKGBUILD")
P("Crear el archivo <b>~/classicclient-uruguay-arch/PKGBUILD</b> con este contenido:")
C("""pkgname=libclassicclient-uruguay
pkgver=7.5.0_b01.02
pkgrel=2
pkgdesc="Thales Classic Client 7.5 para la cedula uruguaya"
arch=('x86_64')
url="https://www.gub.uy/"
license=('LicenseRef-Thales-Proprietary')
depends=('glibc' 'gcc-libs' 'pcsclite' 'qt5-base' 'gtk2')
optdepends=('ccid: controlador CCID para lectores USB')
source=('libclassicclient.deb')
sha256sums=('b6fd0150fcea2b952b0d82027324cf3250dea6f42eaac430d6d08ea22eb840ed')
options=('!strip')

package() {
  bsdtar -xf data.tar.gz -C "$pkgdir"
  find "$pkgdir" -type d -exec chmod 755 {} +
}""")
H2("4.3 Construir e instalar")
C("""makepkg --cleanbuild --clean
sudo pacman -U ./libclassicclient-uruguay-7.5.0_b01.02-2-x86_64.pkg.tar.zst""")
N("Este método instala el contenido oficial pero omite los scripts Debian que intentan detener udev, usan sudo internamente y crean enlaces biométricos innecesarios.", exito)

H1("5. Verificar Classic Client")
C("""pkcs11-tool --module /usr/lib/pkcs11/libgclib.so --list-slots

pkcs11-tool --module /usr/lib/pkcs11/libgclib.so \\
  --list-objects --type cert""")
P("Debe mostrarse el lector, un token Gemalto/Classic y el certificado público. Estas pruebas no solicitan el PIN.")

historia.append(PageBreak())
H1("6. Registrar la cédula en NSS")
P("Cerrar completamente Brave y Chrome antes de modificar la base NSS.")
H2("6.1 Crear o inicializar la base")
C("""mkdir -p ~/.pki/nssdb

# Ejecutar sólo si cert9.db todavía no existe:
certutil -N -d sql:$HOME/.pki/nssdb --empty-password""")
H2("6.2 Agregar Classic Client")
C("""modutil -dbdir sql:$HOME/.pki/nssdb \\
  -add "Cedula Uruguay Classic Client" \\
  -libfile /usr/lib/pkcs11/libgclib.so \\
  -force

modutil -dbdir sql:$HOME/.pki/nssdb -list""")
P("La lista debe contener el módulo, el lector y el token de la cédula.")
N("Chromium moderno también puede usar ~/.local/share/pki/nssdb. Si ~/.pki/nssdb ya existe, suele conservar prioridad. Si el navegador no ve el certificado, revisar cuál base está usando.")

H1("7. Integrar firma.gub.uy con Brave y Chrome")
H2("7.1 Instalar la extensión")
P("Abrir firma.gub.uy, elegir <b>Cédula de Identidad con chip en Navegador</b> y pulsar <b>Firmar con navegador</b>. Instalar SConnect desde el flujo oficial.")
P("ID de la extensión Chromium verificada:")
C("mjhbkkaddmmnkghdnnmkjcgpphnopnfk")
H2("7.2 Descargar el host compatible")
C("""cd ~/Descargas
curl -LO https://www.sconnect.com/extensions/sconnect-host-v2.16.1.0.tar.gz
tar -xf sconnect-host-v2.16.1.0.tar.gz
find ~/Descargas -name sconnect_host_linux""")
P("La extensión 2.16.1.1 exige como mínimo el host 2.16.1.0.")
N("No ejecutar install_sconnect_host.sh: no contempla correctamente Brave y contiene borrados poco cuidadosos.", alerta)

historia.append(PageBreak())
H1("8. Instalar manualmente el host SConnect")
P("Usar la ruta que devolvió find. Si el TAR creó una carpeta, ajustar el origen del comando install.")
C("""mkdir -p ~/.sconnect
install -m 755 ~/Descargas/sconnect_host_linux \\
  ~/.sconnect/sconnect_host_linux""")
H2("8.1 Crear directorios para ambos navegadores")
C("""mkdir -p \\
  ~/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts \\
  ~/.config/google-chrome/NativeMessagingHosts""")
H2("8.2 Crear el manifiesto")
P("Crear <b>/tmp/com.gemalto.sconnect.json</b>. Sustituir USUARIO por el nombre real. La ruta debe ser absoluta.")
C("""{
  "name": "com.gemalto.sconnect",
  "description": "SConnect Native Messaging Host",
  "path": "/home/USUARIO/.sconnect/sconnect_host_linux",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://mjhbkkaddmmnkghdnnmkjcgpphnopnfk/"
  ]
}""")
H2("8.3 Copiar y validar")
C("""cp /tmp/com.gemalto.sconnect.json \\
  ~/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts/

cp /tmp/com.gemalto.sconnect.json \\
  ~/.config/google-chrome/NativeMessagingHosts/

python -m json.tool \\
  ~/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts/com.gemalto.sconnect.json""")
P("Cerrar completamente los navegadores y volver a abrirlos. En Chrome también debe estar instalada la extensión SConnect.")

H1("9. Firmar en firma.gub.uy")
for item in [
    "Conectar el lector e insertar la cédula antes de iniciar.",
    "Elegir Cédula de Identidad con chip en Navegador.",
    "Seleccionar el PDF y autorizar el acceso del sitio a SConnect.",
    "Introducir el PIN únicamente cuando lo solicite el componente local.",
    "Descargar el PDF firmado y validarlo en la sección Validar firmas."
]:
    B(item)
N("La clave privada no se copia al ordenador. El chip firma internamente el resumen criptográfico del documento.", exito)

historia.append(PageBreak())
H1("10. Firma local con Okular")
H2("10.1 Instalar")
C("sudo pacman -S okular")
P("Okular funciona en GNOME sin instalar el escritorio KDE, aunque añade dependencias Qt/KDE. En la prueba ocupó aproximadamente 311 MiB.")
H2("10.2 Configurar NSS")
P("En Okular abrir:")
C("""Preferencias -> Configurar motores -> PDF
Motor de firmas: NSS
Base de datos: Personalizado
/home/USUARIO/.pki/nssdb""")
P("Pulsar Aplicar con la cédula insertada. El certificado debe aparecer en la tabla.")
H2("10.3 Firmar")
C("Herramientas -> Firmar digitalmente")
P("Seleccionar el certificado, marcar el rectángulo visible de la firma, guardar como un PDF nuevo e introducir el PIN.")
P("Los campos <b>Motivo</b>, <b>Localización</b> y <b>Fondo</b> son opcionales. El fondo es sólo una imagen visible y no aporta validez criptográfica.")

H1("11. Diagnóstico rápido")
datos = [
    [Paragraph("Síntoma", h2), Paragraph("Comprobación", h2)],
    [Paragraph("No aparece el lector", cuerpo), Paragraph("Ejecutar pcsc_scan y revisar pcscd.socket/ccid.", cuerpo)],
    [Paragraph("PKCS#11 no ve la cédula", cuerpo), Paragraph("Verificar /usr/lib/pkcs11/libgclib.so y ejecutar pkcs11-tool --list-slots.", cuerpo)],
    [Paragraph("Brave no ve el certificado", cuerpo), Paragraph("Cerrar Brave, comprobar modutil y confirmar la base NSS activa.", cuerpo)],
    [Paragraph("SConnect muestra -99", cuerpo), Paragraph("Comprobar que el host sea 2.16.1.0 o posterior y reiniciar el navegador.", cuerpo)],
    [Paragraph("Okular no muestra certificados", cuerpo), Paragraph("Seleccionar manualmente /home/USUARIO/.pki/nssdb en el motor PDF.", cuerpo)],
]
tabla = Table(datos, colWidths=[55 * mm, 105 * mm], repeatRows=1)
tabla.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), AZUL),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C8D2DC")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 7),
    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLARO]),
]))
historia.append(tabla)

historia.append(PageBreak())
H1("12. Reversión")
H2("Retirar Classic Client")
C("sudo pacman -Rns libclassicclient-uruguay")
H2("Retirar el módulo NSS")
C("""modutil -dbdir sql:$HOME/.pki/nssdb \\
  -delete "Cedula Uruguay Classic Client" -force""")
H2("Retirar Okular")
C("sudo pacman -Rns okular")
H2("Retirar SConnect")
P("Con Brave y Chrome cerrados, retirar:")
C("""~/.sconnect/sconnect_host_linux
~/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts/com.gemalto.sconnect.json
~/.config/google-chrome/NativeMessagingHosts/com.gemalto.sconnect.json""")

H1("13. Recomendaciones de seguridad")
for item in [
    "No compartir el PIN ni escribirlo dentro de comandos o scripts.",
    "Varios intentos incorrectos pueden bloquear el PIN.",
    "Revisar el documento completo antes de firmarlo.",
    "Guardar el PDF original y el PDF firmado como archivos separados.",
    "Validar la firma antes de enviar el documento.",
    "Descargar Classic Client, SConnect y las extensiones sólo desde fuentes oficiales.",
    "Volver a auditar versiones nuevas antes de reutilizar este procedimiento."
]:
    B(item)

N(
    "<b>Resultado esperado:</b> Arch Linux o el derivado compatible reconoce la cédula mediante PKCS#11; Brave y Chrome acceden al certificado a través de NSS; firma.gub.uy funciona mediante SConnect; y Okular puede firmar PDF localmente.",
    exito
)
P("Fin de la guía", ParagraphStyle(
    "Fin", fontName="DejaVu-Bold", fontSize=13, leading=17,
    textColor=AZUL, alignment=TA_CENTER, spaceBefore=16
))

doc.build(historia)
print(SALIDA)
