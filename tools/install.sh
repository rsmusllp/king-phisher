#!/bin/bash
########################################################################
# This is the Linux installation script for the King Phisher Client and
# Server on Ubuntu and Kali Linux.
#
# Project Home Page: https://github.com/securestate/king-phisher/
# Author: Spencer McIntyre
#
# Quick run command:
#
#
# Supported Linux versions:
# Linux Flavor    | Client | Server |
# ----------------|--------|--------|
# CentOS          | no     | yes    |
# Kali            | yes    | yes    |
# Ubuntu          | yes    | yes    |
########################################################################

E_NOTROOT=87
FILE_NAME="$(dirname $(readlink -e $0) 2>/dev/null)/$(basename $0)"
GIT_CLONE_URL="https://github.com/securestate/king-phisher.git"
if [ -z "$KING_PHISHER_DIR" ]; then
	KING_PHISHER_DIR="/opt/king-phisher"
fi
KING_PHISHER_GROUP="kpadmins"
KING_PHISHER_WEB_ROOT="/var/www"
LINUX_VERSION=""

if [ "$(id -u)" != "0" ]; then
	echo "This must be run as root"
	exit $E_NOTROOT
fi

grep -E "CentOS Linux release 7(\.[0-9]{1,4}){2}" /etc/redhat-release > /dev/null 2>&1
if [ -z "$LINUX_VERSION" -a $? -eq 0 ]; then
	LINUX_VERSION="CentOS"
	KING_PHISHER_SKIP_CLIENT="x"
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

if [ ! -z "$KING_PHISHER_SKIP_CLIENT" ]; then
	echo "Skipping installing King Phisher Client components"
fi
if [ ! -z "$KING_PHISHER_SKIP_SERVER" ]; then
	echo "Skipping installing King Phisher Server components"
fi

# install git
if [ "$LINUX_VERSION" == "CentOS" ]; then
	yum install -y -q git
else
	apt-get install -y -qq git
fi

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

echo "Installing $LINUX_VERSION dependencies"
if [ "$LINUX_VERSION" == "CentOS" ]; then
	yum install -y epel-release
	yum install -y freetype-devel gcc gcc-c++ libpng-devel make \
		postgresql-devel python-devel python-pip
	if [ -z "$KING_PHISHER_SKIP_SERVER" ]; then
		yum install -y postgresql-devel
	fi
elif [ "$LINUX_VERSION" == "Kali" ]; then
	apt-get install -y libfreetype6-dev python-dev python-pip
	if [ -z "$KING_PHISHER_SKIP_CLIENT" ]; then
		apt-get install -y gir1.2-gtk-3.0 gir1.2-vte-2.90 \
			gir1.2-webkit-3.0 python-cairo \
			libgtk-3-dev python-gi python-gi-cairo \
			python-gobject python-gobject-dev python-paramiko \
			python-tk tk-dev
	fi
	if [ -z "$KING_PHISHER_SKIP_SERVER" ]; then
		apt-get install -y libpq-dev
	fi
	easy_install -U distribute
elif [ "$LINUX_VERSION" == "Ubuntu" ]; then
	apt-get install -y libfreetype6-dev python-dev python-pip
	if [ -z "$KING_PHISHER_SKIP_CLIENT" ]; then
		apt-get install -y gir1.2-gtk-3.0 gir1.2-vte-2.90 \
			gir1.2-webkit-3.0 python-cairo \
			libgtk-3-dev python-gi python-gi-cairo \
			python-gobject python-gobject-dev python-paramiko \
			python-tk tk-dev
	fi
	if [ -z "$KING_PHISHER_SKIP_SERVER" ]; then
		apt-get install -y libpq-dev
	fi
fi

echo "Installing Python package dependencies from pypi"
# six needs to be installed before requirements.txt for matplotlib
pip install "six>=1.7.0"
pip install -r requirements.txt

if [ -z "$KING_PHISHER_SKIP_CLIENT" ]; then
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
fi

if [ -z "$KING_PHISHER_SKIP_SERVER" ]; then
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

	if [ "$LINUX_VERSION" == "CentOS" ]; then
		echo "Installing the King Phisher service file in /lib/systemd/system/"
		cp data/server/service_files/king-phisher.service /lib/systemd/system
		sed -i -re "s|^ExecStart=KingPhisherServer|# ExecStart=KingPhisherServer|" /lib/systemd/system/king-phisher.service
		sed -i -re "s|^#\\s?ExecStart=/opt|ExecStart=/opt|" /lib/systemd/system/king-phisher.service
		sed -i -re "s|/opt\/king-phisher|$KING_PHISHER_DIR|g" /lib/systemd/system/king-phisher.service

		echo "Starting the King Phisher service"
		systemctl daemon-reload
		systemctl enable king-phisher.service
		systemctl start king-phisher.service
	elif [ "$LINUX_VERSION" == "Ubuntu" ]; then
		echo "Installing the King Phisher service file in /etc/init/"
		cp data/server/service_files/king-phisher.conf /etc/init
		sed -i -re "s|^exec KingPhisherServer|# exec KingPhisherServer|" /etc/init/king-phisher.conf
		sed -i -re "s|^#\\s?exec /opt|exec /opt|" /etc/init/king-phisher.conf
		sed -i -re "s|/opt\/king-phisher|$KING_PHISHER_DIR|g" /etc/init/king-phisher.conf

		echo "Starting the King Phisher service"
		start king-phisher
	else
		echo "Start the King Phisher server with the following command: "
		echo "sudo $KING_PHISHER_DIR/KingPhisherServer -L INFO -f $KING_PHISHER_DIR/server_config.yml"
	fi
fi
