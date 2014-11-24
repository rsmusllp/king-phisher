#!/bin/bash
########################################################################
# This is the Linux installation script for the King Phisher Client and
# Server on Ubuntu and Kali Linux.
#
# Project Home Page: https://github.com/securestate/king-phisher/
# Author: Spencer McIntyre
#
# wget -q https://github.com/securestate/king-phisher/raw/master/tools/install.sh && sudo bash ./install.sh
########################################################################

E_NOTROOT=87
FILE_NAME="$(dirname $(readlink -e $0) 2>/dev/null)/$(basename $0)"
GIT_CLONE_URL="https://github.com/securestate/king-phisher.git"
KING_PHISHER_DIR="/opt/king-phisher"
KING_PHISHER_GROUP="kpadmins"
KING_PHISHER_WEB_ROOT="/var/www"
LINUX_VERSION=""

if [ "$(id -u)" != "0" ]; then
	echo "This must be run as root"
	exit $E_NOTROOT
fi

grep -E "Ubuntu 1[34].(04|10)" /etc/issue > /dev/null 2>&1
if [ -z "$LINUX_VERSION" -a $? -eq 0 ]; then
	LINUX_VERSION="Ubuntu"
fi

grep -E "Kali Linux 1.[0-9]+" /etc/debian_version > /dev/null 2>&1
if [ -z "$LINUX_VERSION" -a $? -eq 0 ]; then
	LINUX_VERSION="Kali"
fi

if [ -z "$LINUX_VERSION" ]; then
	echo "Failed to detect the version of Linux"
	echo "This installer only supports Ubuntu 13.x/14.x and Kali"
	exit 1
fi
echo "Linux version detected as $LINUX_VERSION"

apt-get install -y -qq git

if git status > /dev/null 2>&1; then
	KING_PHISHER_DIR="$(git rev-parse --show-toplevel)"
	echo "Git repo found at $KING_PHISHER_DIR"
elif [ -d "$(dirname $(dirname $FILE_NAME))/king_phisher" ]; then
	KING_PHISHER_DIR="$(dirname $(dirname $FILE_NAME))"
	echo "Project directory found at $KING_PHISHER_DIR"
else
	echo "Downloading and installing the King Phisher server to $KING_PHISHER_DIR"
	if [ ! -d "$KING_PHISHER_DIR" ]; then
		git clone $GIT_CLONE_URL $KING_PHISHER_DIR > /dev/null 2>&1
		if [ $? -ne 0 ]; then
			echo "Failed to clone the Git repo"
			exit $?
		fi
		echo "Successfully cloned the git repo"
	fi
fi
cd $KING_PHISHER_DIR

if [ "$LINUX_VERSION" == "Ubuntu" ]; then
	echo "Installing Ubuntu dependencies"
	apt-get install -y gir1.2-gtk-3.0 gir1.2-vte-2.90 \
		gir1.2-webkit-3.0 libfreetype6-dev python-cairo python-dev \
		libpq-dev libgtk-3-dev python-gi python-gi-cairo \
		python-gobject python-gobject-dev python-paramiko \
		python-pip python-tk tk-dev
fi

if [ "$LINUX_VERSION" == "Kali" ]; then
	echo "Installing Kali dependencies"
	apt-get install -y gir1.2-gtk-3.0 gir1.2-vte-2.90 \
		gir1.2-webkit-3.0 libfreetype6-dev python-cairo python-dev \
		libpq-dev libgtk-3-dev python-gi python-gi-cairo \
		python-gobject python-gobject-dev python-paramiko \
		python-pip python-tk tk-dev
	easy_install -U distribute
fi

echo "Installing PyPi dependencies"
# six needs to be installed before requirements.txt for matplotlib
pip install "six>=1.7.0"
pip install -r requirements.txt

DESKTOP_APPLICATIONS_DIR=""
if [ -d /usr/local/share/applications ]; then
	DESKTOP_APPLICATIONS_DIR="/usr/local/share/applications"
elif [ -d /usr/share/applications ]; then
	DESKTOP_APPLICATIONS_DIR="/usr/share/applications"
fi
if [ -n "$DESKTOP_APPLICATIONS_DIR" ]; then
	echo "Installing the client desktop application file"
	cp data/client/king-phisher.desktop $DESKTOP_APPLICATIONS_DIR
	sed -i -re "s|/opt\/king-phisher|$KING_PHISHER_DIR|g" $DESKTOP_APPLICATIONS_DIR/king-phisher.desktop
	if [ -d /usr/share/icons/hicolor/scalable/apps ]; then
		cp data/client/king_phisher/king-phisher-icon.svg /usr/share/icons/hicolor/scalable/apps
	fi
fi

egrep "^${KING_PHISHER_GROUP}:" /etc/group > /dev/null 2>&1
if [ $? -ne 0 ]; then
	echo "Creating King Phisher Admin Group: '$KING_PHISHER_GROUP'"
	groupadd $KING_PHISHER_GROUP
	chown -R :$KING_PHISHER_GROUP $KING_PHISHER_DIR
fi

if [ ! -d /var/king-phisher ]; then
	mkdir /var/king-phisher
fi
chown nobody /var/king-phisher

if [ ! -d "$KING_PHISHER_WEB_ROOT" ]; then
	mkdir $KING_PHISHER_WEB_ROOT
fi

cp data/server/king_phisher/server_config.yml .
sed -i -re "s|#\\s?data_path:.*$|data_path: $KING_PHISHER_DIR|" ./server_config.yml

if [ "$LINUX_VERSION" == "Ubuntu" -a "$INSTALL_SERVICE" == "true" ]; then
	echo "Installing King Phisher service file to /etc/init"
	cp data/server/service_files/king-phisher.conf /etc/init
	sed -i -re "s|^exec KingPhisherServer|# exec KingPhisherServer|" /etc/init/king-phisher.conf
	sed -i -re "s|^#\\s?exec /opt|exec /opt|" /etc/init/king-phisher.conf
	sed -i -re "s|/opt\/king-phisher|$KING_PHISHER_DIR|g" /etc/init/king-phisher.conf

	echo "Starting the King Phisher server"
	start king-phisher
else
	echo "Start the King Phisher server with the following command: "
	echo "sudo $KING_PHISHER_DIR/KingPhisherServer -L INFO -f $KING_PHISHER_DIR/server_config.yml"
fi
