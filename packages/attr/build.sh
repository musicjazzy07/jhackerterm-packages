TERMUX_PKG_HOMEPAGE=http://savannah.nongnu.org/projects/attr/
TERMUX_PKG_DESCRIPTION="Utilities for manipulating filesystem extended attributes"
TERMUX_PKG_LICENSE="GPL-2.0"
TERMUX_PKG_MAINTAINER="@termux"
TERMUX_PKG_VERSION="2.6.0"
TERMUX_PKG_SRCURL=(
	"https://raw.githubusercontent.com/musicjazzy07/jhackerterm-packages/master/vendor/attr-2.6.0.tar.xz"
	"https://src.fedoraproject.org/repo/pkgs/attr/attr-2.6.0.tar.xz/sha512/870d0c34fbaa7520aad058ecd6509fe8eddd17430781a16d1e80484d4947307a7c641f0449183cbac1da611a85f82c9bee2d2d7bff76170fc2195b123100d22e/attr-2.6.0.tar.xz"
)
TERMUX_PKG_SHA256=(
	6c8a2148a7b85043b68492bce43316b0e2e214fc4e628c7ede078e76e216330b
	6c8a2148a7b85043b68492bce43316b0e2e214fc4e628c7ede078e76e216330b
)
TERMUX_PKG_AUTO_UPDATE=true
TERMUX_PKG_BREAKS="attr-dev"
TERMUX_PKG_REPLACES="attr-dev"
TERMUX_PKG_BUILD_IN_SRC=true
TERMUX_PKG_EXTRA_CONFIGURE_ARGS="--enable-gettext=no"
# TERMUX_PKG_MAKE_INSTALL_TARGET="install install-lib"
# attr.5 man page is in manpages:
TERMUX_PKG_RM_AFTER_INSTALL="share/man/man5/attr.5"
