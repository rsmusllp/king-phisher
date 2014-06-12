#!/bin/bash
########################################################################
# This is the Linux installation script for the King Phisher Client and
# Server on Ubuntu and Kali Linux.
#
# Project Home Page: https://github.com/securestate/king-phisher/
# Author: Spencer McIntyre
#
# curl -s https://raw.githubusercontent.com/securestate/king-phisher/master/tools/install.sh | sudo bash
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

if [ "$(basename $FILE_NAME)" == "bash" ]; then
	echo "Downloading and installing the King Phisher server to $KING_PHISHER_DIR"
	if [ ! -d "$KING_PHISHER_DIR" ]; then
		git clone $GIT_CLONE_URL $KING_PHISHER_DIR > /dev/null 2>&1
		if [ $? -ne 0 ]; then
			echo "Failed to clone the Git Repo"
			exit $?
		fi
		echo "Successfully cloned the git repo"
	fi
elif [ "$(basename $FILE_NAME)" == "install.sh" ]; then
	KING_PHISHER_DIR="$(dirname $(dirname $FILE_NAME))"
fi
cd $KING_PHISHER_DIR

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

if [ "$LINUX_VERSION" == "Ubuntu" ]; then
	echo "Installing Ubuntu dependencies"
	apt-get install -y gir1.2-gtk-3.0 gir1.2-vte-2.90 \
		gir1.2-webkit-3.0 libfreetype6-dev python-cairo python-dev \
		libgtk-3-dev python-gi python-gi-cairo \
		python-gobject python-gobject-dev python-paramiko \
		python-pip python-tk tk-dev > /dev/null 2>&1
	echo "apt-get exited with status: $0"
fi

if [ "$LINUX_VERSION" == "Kali" ]; then
	echo "Installing Kali dependencies"
	apt-get install -y python-gobject python-gobject-dev python-pip \
		gir1.2-vte-2.90 gir1.2-webkit-3.0 > /dev/null 2>&1
fi

echo "Installing PyPi dependencies"
pip install -r requirements.txt > /dev/null

egrep "^${KING_PHISHER_GROUP}:" /etc/group > /dev/null 2>&1
if [ $? -ne 0 ]; then
	echo "Creating King Phisher Admin Group: '$KING_PHISHER_GROUP'"
	groupadd $KING_PHISHER_GROUP
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
