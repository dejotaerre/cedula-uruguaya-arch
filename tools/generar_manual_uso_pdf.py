#!/usr/bin/env python3
"""Genera el manual de uso del automatizador de cédula para Arch y derivados."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
SALIDA = RAIZ_PROYECTO / "docs" / "Manual_uso_script_Cedula_Uruguaya_Arch.pdf"
AZUL = colors.HexColor("#173F73")
CELESTE = colors.HexColor("#EAF4FC")
VERDE = colors.HexColor("#267A55")
VERDE_CLARO = colors.HexColor("#EAF7F0")
NARANJA = colors.HexColor("#B85D0D")
NARANJA_CLARO = colors.HexColor("#FFF3E5")
ROJO = colors.HexColor("#A53636")
ROJO_CLARO = colors.HexColor("#FCEDED")
GRIS = colors.HexColor("#4C5662")
GRIS_CLARO = colors.HexColor("#F3F5F7")


def registrar_fuentes() -> None:
    base = Path("/usr/share/fonts/TTF")
    alternativas = Path("/usr/share/fonts/truetype/dejavu")
    carpeta = base if (base / "DejaVuSans.ttf").exists() else alternativas
    pdfmetrics.registerFont(TTFont("DejaVu", str(carpeta / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(carpeta / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVuMono", str(carpeta / "DejaVuSansMono.ttf")))


def estilos() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "Titulo", parent=base["Title"], fontName="DejaVu-Bold", fontSize=25,
            leading=30, textColor=AZUL, alignment=TA_LEFT, spaceAfter=8 * mm,
        ),
        "subtitulo": ParagraphStyle(
            "Subtitulo", parent=base["Normal"], fontName="DejaVu", fontSize=12,
            leading=18, textColor=GRIS, spaceAfter=7 * mm,
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontName="DejaVu-Bold", fontSize=18,
            leading=22, textColor=AZUL, spaceAfter=5 * mm,
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontName="DejaVu-Bold", fontSize=12.5,
            leading=16, textColor=AZUL, spaceBefore=3 * mm, spaceAfter=2 * mm,
        ),
        "normal": ParagraphStyle(
            "NormalManual", parent=base["BodyText"], fontName="DejaVu", fontSize=9.4,
            leading=14.2, textColor=colors.HexColor("#20252B"), spaceAfter=2.5 * mm,
        ),
        "pequeno": ParagraphStyle(
            "Pequeno", parent=base["BodyText"], fontName="DejaVu", fontSize=8,
            leading=11.5, textColor=GRIS,
        ),
        "codigo": ParagraphStyle(
            "Codigo", parent=base["Code"], fontName="DejaVuMono", fontSize=8.2,
            leading=12.2, textColor=colors.HexColor("#17212B"), leftIndent=3 * mm,
            rightIndent=3 * mm, borderPadding=4 * mm, backColor=GRIS_CLARO,
            borderColor=colors.HexColor("#D8DEE5"), borderWidth=0.5,
            borderRadius=2, spaceBefore=2 * mm, spaceAfter=4 * mm,
        ),
        "caja": ParagraphStyle(
            "Caja", parent=base["BodyText"], fontName="DejaVu", fontSize=9,
            leading=13.5, textColor=colors.HexColor("#20252B"), spaceAfter=0,
        ),
        "centro": ParagraphStyle(
            "Centro", parent=base["BodyText"], fontName="DejaVu-Bold", fontSize=10,
            leading=14, alignment=TA_CENTER, textColor=AZUL,
        ),
    }


def cabecera_pie(canvas, doc) -> None:
    canvas.saveState()
    ancho, alto = A4
    canvas.setFillColor(AZUL)
    canvas.rect(0, alto - 11 * mm, ancho, 11 * mm, stroke=0, fill=1)
    canvas.setFont("DejaVu-Bold", 7.5)
    canvas.setFillColor(colors.white)
    canvas.drawString(18 * mm, alto - 7 * mm, "CÉDULA URUGUAYA CON CHIP EN ARCH LINUX")
    canvas.setStrokeColor(colors.HexColor("#D8DEE5"))
    canvas.line(18 * mm, 14 * mm, ancho - 18 * mm, 14 * mm)
    canvas.setFont("DejaVu", 7.5)
    canvas.setFillColor(GRIS)
    canvas.drawString(18 * mm, 9 * mm, "Manual comunitario - Automatizador v1.0.0")
    canvas.drawRightString(ancho - 18 * mm, 9 * mm, f"Página {doc.page}")
    canvas.restoreState()


def caja(texto: str, color_fondo, color_borde, st) -> Table:
    tabla = Table([[Paragraph(texto, st["caja"])]], colWidths=[166 * mm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color_fondo),
        ("BOX", (0, 0), (-1, -1), 0.8, color_borde),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
    ]))
    return tabla


def lista(elementos: list[str], st, color=AZUL) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, st["normal"]), leftIndent=4 * mm) for item in elementos],
        bulletType="bullet", start="circle", bulletColor=color, leftIndent=6 * mm,
        bulletFontName="DejaVu-Bold", bulletFontSize=7, spaceAfter=2 * mm,
    )


def paso(numero: int, titulo: str, descripcion: str, accion: str, st) -> KeepTogether:
    encabezado = Table([
        [Paragraph(str(numero), st["centro"]), Paragraph(f"<b>{titulo}</b>", st["normal"])]
    ], colWidths=[12 * mm, 150 * mm])
    encabezado.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), CELESTE),
        ("BOX", (0, 0), (0, 0), 0.8, AZUL),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (1, 0), (1, 0), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
    ]))
    return KeepTogether([
        encabezado,
        Spacer(1, 1.5 * mm),
        Paragraph(descripcion, st["normal"]),
        caja(f"<b>Intervención del usuario:</b> {accion}", NARANJA_CLARO, NARANJA, st),
        Spacer(1, 4 * mm),
    ])


def generar() -> None:
    registrar_fuentes()
    st = estilos()
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(SALIDA), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=20 * mm, bottomMargin=19 * mm,
        title="Manual de uso del script de cédula uruguaya en Arch Linux",
        author="Guía comunitaria para usuarios de Arch Linux y derivados",
        subject="Instalación, intervención del usuario y firma digital",
    )
    marco = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="principal")
    doc.addPageTemplates([PageTemplate(id="manual", frames=[marco], onPage=cabecera_pie)])
    historia = []

    historia += [
        Spacer(1, 18 * mm),
        Paragraph("Manual de uso del automatizador", st["titulo"]),
        Paragraph("Cédula uruguaya con chip en Arch Linux y derivados", st["subtitulo"]),
        caja(
            "<b>Propósito.</b> Esta guía explica cómo usar <font name='DejaVuMono'>cedula-uruguaya-arch.py</font>, "
            "qué tareas realiza por sí mismo y cuándo necesita que la persona cierre programas, confirme "
            "operaciones, instale una extensión, conecte la cédula o introduzca su PIN.",
            CELESTE, AZUL, st,
        ),
        Spacer(1, 8 * mm),
        Paragraph("La idea esencial", st["h1"]),
        Paragraph(
            "El script automatiza la preparación técnica del sistema, pero no puede tomar decisiones "
            "personales ni actuar dentro de páginas web o cuadros protegidos del navegador. La firma "
            "continúa bajo el control del titular de la cédula.", st["normal"],
        ),
        Table([
            [Paragraph("AUTOMÁTICO", st["centro"]), Paragraph("REQUIERE AL USUARIO", st["centro"])],
            [Paragraph("Paquetes, servicio PC/SC, conversión del DEB, módulo PKCS#11, NSS, host y manifiestos SConnect.", st["normal"]),
             Paragraph("Cerrar navegadores, aceptar sudo, instalar la extensión, conectar el lector, elegir el PDF, introducir el PIN y guardar/verificar el resultado.", st["normal"])],
        ], colWidths=[83 * mm, 83 * mm], style=TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), VERDE_CLARO), ("TEXTCOLOR", (0, 0), (0, 0), VERDE),
            ("BACKGROUND", (1, 0), (1, 0), NARANJA_CLARO), ("TEXTCOLOR", (1, 0), (1, 0), NARANJA),
            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#CAD2DA")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8DEE5")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 3 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
        ])),
        Spacer(1, 8 * mm),
        caja(
            "<b>Seguridad:</b> el script nunca pide, lee ni almacena el PIN. El PIN se introduce solamente "
            "en el diálogo de firma del componente oficial cuando la persona decide firmar.",
            VERDE_CLARO, VERDE, st,
        ),
        Spacer(1, 10 * mm),
        Paragraph("Versión del manual: 1.0 - Agosto de 2026", st["pequeno"]),
        PageBreak(),
    ]

    historia += [
        Paragraph("1. Antes de comenzar", st["h1"]),
        Paragraph("Requisitos", st["h2"]),
        lista([
            "Arch Linux o una distribución compatible basada en Arch, arquitectura x86-64.",
            "Una cuenta con permiso para usar <font name='DejaVuMono'>sudo</font>.",
            "Conexión a Internet, salvo que ya se posean los archivos descargados.",
            "Brave o Google Chrome para la firma web; Okular es opcional para firmar PDF localmente.",
            "Un lector de tarjetas compatible y la cédula con chip, necesarios para probar y firmar, no para instalar.",
        ], st),
        Paragraph("Archivos recibidos", st["h2"]),
        Paragraph("El paquete compartible contiene:", st["normal"]),
        lista([
            "<font name='DejaVuMono'>cedula-uruguaya-arch.py</font>: programa principal.",
            "<font name='DejaVuMono'>README.md</font>: referencia breve en texto.",
            "<font name='DejaVuMono'>PKGBUILD</font>: receta auditable usada para adaptar el DEB.",
        ], st),
        Paragraph("Fuentes que utiliza", st["h2"]),
        Paragraph(
            "El DEB se obtiene desde <link href='https://archivos.agesic.gub.uy/nextcloud/index.php/s/8kqSb9z4xKABM8T' color='#173F73'><u>el enlace público de Agesic</u></link>. "
            "Si ese enlace deja de funcionar, consulte <link href='https://www.gub.uy/agencia-gobierno-electronico-sociedad-informacion-conocimiento/firma-digital/drivers-para-usar-cedula-digital' color='#173F73'><u>la página oficial de controladores</u></link>. "
            "SConnect se descarga desde el sitio de su fabricante.", st["normal"],
        ),
        caja(
            "<b>Importante:</b> las versiones y huellas SHA-256 están fijadas. Si un proveedor cambia un "
            "archivo, el script se detendrá. No es un error accidental: evita ejecutar un archivo distinto "
            "del que fue probado.", NARANJA_CLARO, NARANJA, st,
        ),
        Spacer(1, 5 * mm),
        Paragraph("Preparar la carpeta", st["h2"]),
        Paragraph("Abra una terminal en la carpeta donde descargó el archivo y ejecute:", st["normal"]),
        Paragraph("tar -xzf cedula-uruguaya-arch-1.0.0.tar.gz<br/>cd cedula-uruguaya-arch<br/>chmod +x cedula-uruguaya-arch.py", st["codigo"]),
        caja(
            "<b>Debe intervenir:</b> compruebe que está dentro de la carpeta correcta. No ejecute el programa "
            "con <font name='DejaVuMono'>sudo python...</font>; debe iniciarse como usuario normal.",
            NARANJA_CLARO, NARANJA, st,
        ),
        PageBreak(),
    ]

    historia += [
        Paragraph("2. Instalación guiada", st["h1"]),
        Paragraph("Opción recomendada", st["h2"]),
        Paragraph("Para preparar firma web y además instalar Okular:", st["normal"]),
        Paragraph("./cedula-uruguaya-arch.py instalar --con-okular", st["codigo"]),
        paso(1, "Comprobación inicial", "El programa verifica Arch Linux o un derivado compatible, x86-64, y que no se esté ejecutando completamente como root.", "Ninguna, salvo corregir el sistema equivocado o volver a abrir la terminal como usuario normal si aparece un error.", st),
        paso(2, "Instalación de paquetes", "Pacman instalará solamente las dependencias que falten. La opción <font name='DejaVuMono'>--con-okular</font> añade el visor PDF y sus dependencias.", "Leer la lista que muestra pacman, aceptar la operación y, si sudo lo solicita, escribir la contraseña de la cuenta. Esa contraseña no llega al script.", st),
        paso(3, "Descarga y verificación", "El programa descarga Classic Client y SConnect, calcula sus huellas y se detiene si no coinciden. También puede usar un DEB local.", "Si la descarga oficial falla o cambió la huella, no fuerce la instalación: revise la página oficial o consiga la versión documentada.", st),
        paso(4, "Cerrar los navegadores", "Antes de modificar NSS y los manifiestos, el programa comprueba que Brave y Chrome estén completamente cerrados.", "Cierre todas las ventanas de Brave y Chrome. Si el aviso persiste, espere unos segundos y vuelva a ejecutar el comando; no hace falta matar procesos a ciegas.", st),
        Paragraph("<b>Alternativa:</b> usar un DEB ya descargado.", st["normal"]),
        Spacer(1, 1.5 * mm),
        Paragraph("./cedula-uruguaya-arch.py instalar --deb ~/Descargas/libclassicclient_7.5.0-b01.02_Uruguay_ubuntu.amd64.deb --con-okular", st["codigo"]),
        PageBreak(),
    ]

    historia += [
        Paragraph("3. Qué ocurre automáticamente", st["h1"]),
        Paragraph("Durante una ejecución correcta el programa realiza estas tareas:", st["normal"]),
        lista([
            "Instala <font name='DejaVuMono'>pcsclite</font>, <font name='DejaVuMono'>ccid</font>, <font name='DejaVuMono'>opensc</font>, NSS y las bibliotecas necesarias.",
            "Activa <font name='DejaVuMono'>pcscd.socket</font>, que permite comunicarse con lectores de tarjetas.",
            "Extrae el contenido del DEB privativo y construye un paquete Arch administrado por pacman.",
            "Instala el módulo <font name='DejaVuMono'>/usr/lib/pkcs11/libgclib.so</font>.",
            "Crea o reutiliza <font name='DejaVuMono'>~/.pki/nssdb</font> y registra allí el módulo de la cédula.",
            "Instala el host nativo SConnect en la cuenta del usuario.",
            "Crea manifiestos de comunicación para Brave y Google Chrome.",
            "Respalda NSS y SConnect antes de reemplazar configuraciones existentes.",
        ], st, VERDE),
        caja(
            "<b>Los respaldos propios del automatizador</b> quedan bajo "
            "<font name='DejaVuMono'>~/.local/share/cedula-uruguaya-arch/backups/</font>.",
            VERDE_CLARO, VERDE, st,
        ),
        Spacer(1, 6 * mm),
        Paragraph("Lo que deliberadamente no hace", st["h1"]),
        lista([
            "No instala silenciosamente la extensión SConnect dentro del navegador.",
            "No abre firma.gub.uy, no elige documentos y no pulsa botones en nombre del usuario.",
            "No introduce el PIN ni puede recuperarlo si se olvidó.",
            "No comprueba la identidad del firmante ni decide dónde colocar una firma visible.",
            "No garantiza compatibilidad futura si Agesic o Thales cambian sus archivos o protocolos.",
            "No transforma DOCX u hojas de cálculo en documentos firmables; primero deben exportarse a PDF.",
        ], st, ROJO),
        caja(
            "<b>Resultado de esta etapa:</b> el sistema queda preparado. Todavía falta instalar o comprobar "
            "la extensión del navegador, conectar el dispositivo y realizar una firma de prueba.",
            NARANJA_CLARO, NARANJA, st,
        ),
        PageBreak(),
    ]

    historia += [
        Paragraph("4. Intervenciones después de instalar", st["h1"]),
        paso(1, "Instalar SConnect en el navegador", "Abra Brave o Chrome e instale la extensión oficial SConnect. El identificador esperado es <font name='DejaVuMono'>mjhbkkaddmmnkghdnnmkjcgpphnopnfk</font>.", "Confirmar personalmente la instalación de la extensión. El script sólo instala el programa nativo con el que ella se comunica.", st),
        paso(2, "Conectar el lector y la cédula", "Conecte el lector USB e inserte la cédula con chip en la orientación correcta.", "Manipular el dispositivo físico. Si no se detecta, pruebe otro puerto y compruebe que la tarjeta esté bien insertada.", st),
        paso(3, "Ejecutar la verificación", "Desde la carpeta del programa ejecute el comando siguiente. Enumera el token sin pedir el PIN.", "Leer el resultado y confirmar que aparece el lector o token de la cédula.", st),
        Paragraph("./cedula-uruguaya-arch.py verificar", st["codigo"]),
        paso(4, "Firmar por la web", "En firma.gub.uy seleccione <b>Cédula de Identidad con chip en Navegador</b>, cargue el PDF y continúe el asistente.", "Elegir el archivo, aceptar la operación e introducir el PIN sólo cuando lo solicite el diálogo de firma oficial.", st),
        caja(
            "<b>Advertencia conocida:</b> el portal puede mostrar que la versión de SConnect no es compatible "
            "y aun así permitir continuar y firmar. No dé por hecho el éxito: descargue el resultado y "
            "verifique que la firma digital figure como válida.", NARANJA_CLARO, NARANJA, st,
        ),
        PageBreak(),
    ]

    historia += [
        Paragraph("5. Firmar con Okular", st["h1"]),
        Paragraph(
            "Okular sirve para firmar archivos PDF localmente. No firma DOCX, ODT, XLSX u otros formatos "
            "de oficina directamente: expórtelos primero a PDF desde LibreOffice u otra aplicación.", st["normal"],
        ),
        Paragraph("Configuración inicial", st["h2"]),
        lista([
            "Abra Okular y vaya a la configuración del motor PDF.",
            "Seleccione <b>NSS</b> como motor de firmas.",
            "Use como base de certificados <font name='DejaVuMono'>~/.pki/nssdb</font>.",
            "Aplique los cambios. Debería aparecer el certificado emitido a nombre del titular.",
        ], st),
        caja(
            "<b>Debe intervenir:</b> seleccionar el certificado correcto. Los campos Motivo, Localización "
            "y Fondo son opcionales; pueden dejarse vacíos. El fondo sólo cambia la apariencia visible, no "
            "la validez criptográfica.", NARANJA_CLARO, NARANJA, st,
        ),
        Spacer(1, 5 * mm),
        Paragraph("Firma del PDF", st["h2"]),
        lista([
            "Abra el PDF en Okular y elija la herramienta para añadir una firma digital.",
            "Dibuje el rectángulo donde se mostrará la firma, si desea una representación visible.",
            "Elija el certificado de la cédula e introduzca el PIN cuando aparezca el diálogo protegido.",
            "Guarde con otro nombre para conservar el original sin firmar.",
            "Vuelva a abrir el archivo firmado y revise el panel de firmas y la validez del certificado.",
        ], st),
        caja(
            "<b>Regla práctica:</b> una imagen, sello o firma manuscrita pegada sobre una página no equivale "
            "a una firma digital. Debe aparecer una firma criptográfica verificable en el visor PDF.",
            ROJO_CLARO, ROJO, st,
        ),
        Spacer(1, 7 * mm),
        Paragraph("6. Diagnóstico rápido", st["h1"]),
        Paragraph("Este comando no modifica el sistema:", st["normal"]),
        Paragraph("./cedula-uruguaya-arch.py diagnosticar", st["codigo"]),
        Paragraph(
            "Cada línea marcada con ✓ indica un componente encontrado. Una ✗ identifica dónde mirar: "
            "paquete, módulo PKCS#11, servicio PC/SC, NSS, host SConnect o manifiesto del navegador.", st["normal"],
        ),
        PageBreak(),
    ]

    historia += [
        Paragraph("7. Problemas frecuentes", st["h1"]),
        Table([
            [Paragraph("SÍNTOMA", st["centro"]), Paragraph("QUÉ DEBE HACER EL USUARIO", st["centro"])],
            [Paragraph("El script pide cerrar Brave o Chrome", st["normal"]), Paragraph("Cierre todas sus ventanas, espere unos segundos y vuelva a ejecutar el mismo comando.", st["normal"])],
            [Paragraph("La huella SHA-256 no coincide", st["normal"]), Paragraph("No continúe. Revise la página oficial: el archivo puede haber cambiado y el script necesita una actualización auditada.", st["normal"])],
            [Paragraph("No aparece el certificado", st["normal"]), Paragraph("Conecte lector y cédula, ejecute <font name='DejaVuMono'>verificar</font> y compruebe que Okular use NSS con <font name='DejaVuMono'>~/.pki/nssdb</font>.", st["normal"])],
            [Paragraph("SConnect dice que es incompatible", st["normal"]), Paragraph("Si el portal permite seguir, complete una prueba y verifique el PDF resultante. Si bloquea la operación, revise la versión oficial disponible.", st["normal"])],
            [Paragraph("El portal no firma", st["normal"]), Paragraph("Pruebe primero Brave; Chrome queda disponible como alternativa. Compruebe la extensión, reinicie el navegador y ejecute el diagnóstico.", st["normal"])],
            [Paragraph("No se puede seleccionar texto en Okular", st["normal"]), Paragraph("Cambie de la herramienta Mano a Selección de texto. Este manual fue generado con texto real seleccionable.", st["normal"])],
        ], colWidths=[54 * mm, 112 * mm], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), AZUL), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#BFC8D2")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8DEE5")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLARO]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ])),
        Spacer(1, 7 * mm),
        Paragraph("8. Desinstalación", st["h1"]),
        Paragraph(
            "La desinstalación exige confirmación explícita y crea un respaldo antes de retirar lo que "
            "instaló el automatizador:", st["normal"],
        ),
        Paragraph("./cedula-uruguaya-arch.py desinstalar --confirmar", st["codigo"]),
        Paragraph("Para solicitar también la retirada de Okular:", st["normal"]),
        Paragraph("./cedula-uruguaya-arch.py desinstalar --confirmar --quitar-okular", st["codigo"]),
        caja(
            "<b>Debe intervenir:</b> cerrar Brave y Chrome, leer la lista de pacman y confirmar. No quite "
            "Okular si lo utiliza para otros documentos.", NARANJA_CLARO, NARANJA, st,
        ),
        PageBreak(),
    ]

    historia += [
        Paragraph("Lista de control final", st["h1"]),
        Paragraph("Antes de considerar terminada la preparación, confirme:", st["normal"]),
        lista([
            "[ ] El comando <font name='DejaVuMono'>diagnosticar</font> no muestra fallos inesperados.",
            "[ ] La extensión SConnect está instalada en el navegador elegido.",
            "[ ] El lector y la cédula aparecen con el comando <font name='DejaVuMono'>verificar</font>.",
            "[ ] Se realizó una firma de prueba con un PDF no importante.",
            "[ ] El PDF firmado se descargó o guardó con otro nombre.",
            "[ ] Un visor muestra la firma criptográfica como válida.",
            "[ ] El original sin firmar sigue conservado.",
        ], st, VERDE),
        Spacer(1, 7 * mm),
        caja(
            "<b>Resumen:</b> el script instala y configura la infraestructura. El usuario conserva el "
            "control de los navegadores, el dispositivo físico, el documento, el certificado, el PIN, "
            "la ubicación visible de la firma y la comprobación del resultado.",
            CELESTE, AZUL, st,
        ),
        Spacer(1, 10 * mm),
        Paragraph("Comandos de referencia", st["h2"]),
        Paragraph(
            "# Instalación completa recomendada<br/>"
            "./cedula-uruguaya-arch.py instalar --con-okular<br/><br/>"
            "# Estado del sistema, sin cambios<br/>"
            "./cedula-uruguaya-arch.py diagnosticar<br/><br/>"
            "# Detección del token, sin pedir PIN<br/>"
            "./cedula-uruguaya-arch.py verificar<br/><br/>"
            "# Ayuda incorporada<br/>"
            "./cedula-uruguaya-arch.py --help", st["codigo"],
        ),
        Spacer(1, 8 * mm),
        Paragraph(
            "Este procedimiento comunitario fue probado en CachyOS y está diseñado para Arch Linux y derivados. Classic Client y SConnect son "
            "componentes privativos de sus respectivos proveedores; la compatibilidad puede cambiar con "
            "actualizaciones futuras.", st["pequeno"],
        ),
    ]

    doc.build(historia)
    print(SALIDA)


if __name__ == "__main__":
    generar()
