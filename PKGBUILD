pkgname=libclassicclient-uruguay
pkgver=7.5.0_b01.02
pkgrel=2
pkgdesc="Thales Classic Client 7.5 para la cedula de identidad uruguaya"
arch=('x86_64')
url="https://www.gub.uy/"
license=('LicenseRef-Thales-Proprietary')
depends=('glibc' 'gcc-libs' 'pcsclite' 'qt5-base' 'gtk2')
optdepends=('ccid: controlador CCID para lectores USB de tarjetas inteligentes')
source=('libclassicclient.deb')
sha256sums=('b6fd0150fcea2b952b0d82027324cf3250dea6f42eaac430d6d08ea22eb840ed')
options=('!strip')

package() {
  bsdtar -xf data.tar.gz -C "$pkgdir"
  find "$pkgdir" -type d -exec chmod 755 {} +
}
