#!/bin/bash
# vim: tabstop=4 softtabstop=4 shiftwidth=4 noexpandtab
###############################################################################
# This is the Linux installation script for the King Phisher Client and
# Server on supported distributions.
#
# Project Home Page: https://github.com/securestate/king-phisher/
# Authors:
#   Erik Daguerre
#   Spencer McIntyre
#
# Quick run command:
#   wget -q https://github.com/securestate/king-phisher/raw/master/tools/install.sh && sudo bash ./install.sh
#
# Supported Linux Distributions:
#   Linux Flavor    | Client | Server |
#   ----------------|--------|--------|
#   BackBox         | yes    | yes    |
#   CentOS          | no     | yes    |
#   Debian          | yes    | yes    |
#   Fedora          | yes    | yes    |
#   Kali            | yes    | yes    |
#   Ubuntu          | yes    | yes    |
#
###############################################################################

E_USAGE=64
E_SOFTWARE=70
E_NOTROOT=87
FILE_NAME="$(dirname $(readlink -e $0) 2>/dev/null)/$(basename $0)"
GIT_CLONE_URL="https://github.com/securestate/king-phisher.git"
if [ -z "$KING_PHISHER_DIR" ]; then
	KING_PHISHER_DIR="/opt/king-phisher"
fi
KING_PHISHER_GROUP="king-phisher"
KING_PHISHER_USE_POSTGRESQL="no"
KING_PHISHER_WEB_ROOT="/var/www"
LINUX_VERSION=""
BACKUP=false

answer_all_no=false
answer_all_yes=false

function prompt_yes_or_no {
	# prompt the user to answer a yes or no question, defaulting to yes if no
	# response is entered
	local __prompt_text=$1
	local __result_var=$2
	if [ "$answer_all_no" == "true" ]; then
		$__result_var="no";
		return 0;
	elif [ "$answer_all_yes" == "true" ]; then
		eval $__result_var="yes";
		return 0;
	fi
	while true; do
		read -p "$__prompt_text [Y/n] " _response
		case $_response in
			"" ) eval $__result_var="yes"; break;;
			[Yy]* ) eval $__result_var="yes"; break;;
			[Nn]* ) eval $__result_var="no";  break;;
			* ) echo "Please answer yes or no.";;
		esac
	done
	return 0;
}

function show_help {
	echo "Usage: $(basename $0) [-h] [-n/-y]"
	echo ""
	echo "King Phisher Install Script"
	echo ""
	echo "optional arguments"
	echo "  -h, --help            show this help message and exit"
	echo "  -n, --no              answer no to all questions"
	echo "  -y, --yes             answer yes to all questions"
	echo "  --skip-client         skip installing client components"
	echo "  --skip-server         skip installing server components"
	return 0;
}

while :; do
	case $1 in
		-h|-\?|--help)
			show_help
			exit
			;;
		-n|--no)
			if [ "$answer_all_yes" == "true" ]; then
				echo "Can not use -n and -y together"
				exit $E_USAGE
			fi
			answer_all_no=true
			;;
		-y|--yes)
			if [ "$answer_all_no" == "true" ]; then
				echo "Can not use -n and -y together"
				exit $E_USAGE
			fi
			answer_all_yes=true
			;;
		--skip-client)
			KING_PHISHER_SKIP_CLIENT="x"
			;;
		--skip-server)
			KING_PHISHER_SKIP_SERVER="x"
			;;
		--)
			shift
			break
			;;
		-?*)
			printf "Unknown option: %s\n" "$1" >&2
			exit $E_USAGE
			;;
		*)
			break
	esac
	shift
done

if [ "$(id -u)" != "0" ]; then
	echo "This must be run as root"
	exit $E_NOTROOT
fi

if [[ ! $LINUX_VERSION ]] && grep -E "BackBox Linux 4\.[5-9]" /etc/issue &> /dev/null; then
	LINUX_VERSION="BackBox"
fi

if [[ ! $LINUX_VERSION ]] && grep -E "CentOS Linux release 7(\.[0-9]{1,4}){2}" /etc/redhat-release &> /dev/null; then
	LINUX_VERSION="CentOS"
	KING_PHISHER_SKIP_CLIENT="x"
fi

if [[ ! $LINUX_VERSION ]] && grep -E "Fedora release 2[4-9]" /etc/redhat-release &> /dev/null; then
	LINUX_VERSION="Fedora"
fi

if [[ ! $LINUX_VERSION ]] && grep -E "Debian GNU\/Linux [8-9] " /etc/issue &> /dev/null; then
	LINUX_VERSION="Debian"
fi

if [[ ! $LINUX_VERSION ]] && grep 'Kali Linux Rolling' /etc/debian_version &> /dev/null; then
	LINUX_VERSION="Kali"
fi

if [[ ! $LINUX_VERSION ]] && grep -E "Ubuntu 1[456]\.(04|10)" /etc/issue &> /dev/null; then
	LINUX_VERSION="Ubuntu"
fi

if [[ ! $LINUX_VERSION ]] && grep -E "Ubuntu Xenial Xerus" /etc/issue &> /dev/null; then
	LINUX_VERSION="Ubuntu"
fi

if [ -z "$LINUX_VERSION" ]; then
	echo "Failed to detect the version of Linux"
	echo "This installer only supports the following Linux distributions:"
	echo "  - BackBox"
	echo "  - CentOS"
	echo "  - Debian"
	echo "  - Fedora"
	echo "  - Kali"
	echo "  - Ubuntu"
	echo ""
	echo "If the current version of Linux is one of these flavors but it is"
	echo "not recognized, please open a support ticket and include the version."
	exit 1
fi
echo "Linux version detected as $LINUX_VERSION"

if [ ! -z "$KING_PHISHER_SKIP_CLIENT" ]; then
	echo "Skipping installing King Phisher Client components"
fi
if [ ! -z "$KING_PHISHER_SKIP_SERVER" ]; then
	echo "Skipping installing King Phisher Server components"
else
	prompt_yes_or_no "Install and use PostgreSQL? (Highly recommended and required for upgrading)" KING_PHISHER_USE_POSTGRESQL
	if [ $KING_PHISHER_USE_POSTGRESQL == "yes" ]; then
		echo "Will install and configure PostgreSQL for the server"
	fi
fi

# update apt-get package information and only continue if successful
if [ "$(command -v apt-get)" ]; then
	echo "Attempting to update apt-get cache package information"
	if ! apt-get update; then
		echo "Command 'apt-get update' failed, please correct the issues and try again"
		exit
	fi
fi

# install git if necessary
if [ ! "$(command -v git)" ]; then
	if [ "$LINUX_VERSION" == "CentOS" ]; then
		yum install -y -q git
	elif [ "$LINUX_VERSION" == "Fedora" ]; then
		dnf install -y -q git
	else
		apt-get install -y -qq git
	fi
fi

if git status &> /dev/null; then
	KING_PHISHER_DIR="$(git rev-parse --show-toplevel)"
	echo "Git repo found at $KING_PHISHER_DIR"
elif [ -d "$(dirname $(dirname $FILE_NAME))/king_phisher" ]; then
	KING_PHISHER_DIR="$(dirname $(dirname $FILE_NAME))"
	echo "Project directory found at $KING_PHISHER_DIR"
else
	echo "Downloading and installing the King Phisher server to $KING_PHISHER_DIR"
	if [ ! -d "$KING_PHISHER_DIR" ]; then
		if ! git clone $GIT_CLONE_URL $KING_PHISHER_DIR &> /dev/null; then
			echo "Failed to clone the Git repo"
			exit $E_SOFTWARE
		fi
		echo "Successfully cloned the git repo"
	fi
fi
cd $KING_PHISHER_DIR
if [ -n "$KING_PHISHER_DEV" ] && [ -d ".git" ]; then
	git fetch origin
	git checkout -b dev origin/dev
	echo "Switched to the dev branch"
fi

if [ "$LINUX_VERSION" == "Kali" ]; then
	if ! grep 'Kali Linux Rolling' /etc/debian_version &> /dev/null; then
		echo "Checking Kali 2 apt sources"
		if ! grep -E "deb http://http\.kali\.org/kali sana main non-free contrib" /etc/apt/sources.list &> /dev/null; then
			echo "Standard Kali 2 apt sources are missing, now adding them"
			echo "See http://docs.kali.org/general-use/kali-linux-sources-list-repositories for more details"
			echo "deb http://http.kali.org/kali sana main non-free contrib" >> /etc/apt/sources.list
			apt-get update
		fi
	fi
fi

echo "Installing $LINUX_VERSION dependencies"
if [ "$LINUX_VERSION" == "CentOS" ]; then
	if [ ! "$(command -v python3)" ]; then
		# manually install python3.5 on CentOS 7 and symlink it to python3
		echo "Installing Python3.5 for CentOS 7"
		yum install -y https://centos7.iuscommunity.org/ius-release.rpm
		yum install -y python35u python35u-devel python35u-pip
		echo "Symlinking $(which python3.5) -> /usr/bin/python3"
		ln -s $(which python3.5) /usr/bin/python3
	fi
	yum install -y epel-release
	yum install -y freetype-devel gcc gcc-c++ libpng-devel make \
		openssl-devel postgresql-devel
	if [ "$KING_PHISHER_USE_POSTGRESQL" == "yes" ]; then
		yum install -y postgresql-server
		# manually init the database
		postgresql-setup initdb
	fi
elif [ "$LINUX_VERSION" == "Fedora" ]; then
	dnf install -y freetype-devel gcc gcc-c++ gtk3-devel \
		libpng-devel postgresql-devel python3-devel python3-pip \
		libffi-devel openssl-devel
	if [ -z "$KING_PHISHER_SKIP_CLIENT" ]; then
		dnf install -y geos geos-devel gtksourceview3 vte3
	fi
	if [ "$KING_PHISHER_USE_POSTGRESQL" == "yes" ]; then
		dnf install -y postgresql-server
	fi
	# Fedora 23 is missing an rpm lib required, check to see if it has been installed.
	if [ ! -d "$/usr/lib/rpm/redhat/redhat-hardened-cc1" ]; then
		dnf install -y rpm-build
	fi
elif [ "$LINUX_VERSION" == "BackBox" ] || \
	 [ "$LINUX_VERSION" == "Debian"  ] || \
	 [ "$LINUX_VERSION" == "Kali"    ] || \
	 [ "$LINUX_VERSION" == "Ubuntu"  ]; then
	apt-get install -y libfreetype6-dev python3-dev python3-pip pkg-config
	if [ -z "$KING_PHISHER_SKIP_CLIENT" ]; then
		if ! apt-get install -y gir1.2-gtk-3.0 gir1.2-gtksource-3.0 \
			gir1.2-webkit-3.0 python3-cairo libgeos++-dev \
			libgtk-3-dev libpq-dev python3-gi python3-gi-cairo libpq-dev; then
				echo -e "\nFailed to install dependencies with apt-get\n"
				exit
		fi

		if [ "$LINUX_VERSION" == "Ubuntu" ]; then
			apt-get install -y adwaita-icon-theme-full
		fi

		if apt-cache search gir1.2-vte-2.91 &> /dev/null; then
			if ! apt-get -y install gir1.2-vte-2.91; then
				echo "Failed to install gir1.2-vte-2.91"
			fi
		else
			if ! apt-get -y install gir1.2-vte-2.90; then
				echo "Failed to install gir1.2-vte-2.90"
			fi
		fi

		if apt-get install -y gir1.2-webkit2-3.0 &> /dev/null; then
			echo "Successfully installed gir1.2-webkit2-3.0 with apt-get"
		else
			echo "Failed to install gir1.2-webkit2-3.0 with apt-get"
		fi
	fi

	if [ "$KING_PHISHER_USE_POSTGRESQL" == "yes" ]; then
		apt-get install -y postgresql postgresql-server-dev-all &> /dev/null
	fi
	if [ "$LINUX_VERSION" == "Kali" ]; then
		easy_install -U distribute
		apt-get install -y postgresql-server-dev-all &> /dev/null
	fi
fi

echo "Installing Python package dependencies from PyPi"
# six needs to be installed before requirements.txt for matplotlib
PIP_VERSION=$(pip --version)
python3 -m pip install --upgrade pip
# set pip back to python2 if python2 was default
if echo $PIP_VERSION | grep "python 2.7"; then
	python -m pip install -U pip -I &> /dev/null
fi
python3 -m pip install --upgrade setuptools
python3 -m pip install --upgrade six
if ! python3 -m pip install -r requirements.txt; then
	echo "Failed to install python requirements with pip"
	exit $E_SOFTWARE
fi

if [ -z "$KING_PHISHER_SKIP_CLIENT" ]; then
	DESKTOP_APPLICATIONS_DIR=""
	if [ -d "/usr/local/share/applications" ]; then
		DESKTOP_APPLICATIONS_DIR="/usr/local/share/applications"
	elif [ -d "/usr/share/applications" ]; then
		DESKTOP_APPLICATIONS_DIR="/usr/share/applications"
	fi
	if [ -n "$DESKTOP_APPLICATIONS_DIR" ]; then
		echo "Installing the client desktop application file"
		cp data/client/king-phisher.desktop $DESKTOP_APPLICATIONS_DIR
		sed -i -re "s|/opt\/king-phisher|$KING_PHISHER_DIR|g" $DESKTOP_APPLICATIONS_DIR/king-phisher.desktop
		if [ -d "/usr/share/icons/hicolor/scalable/apps" ]; then
			cp data/client/king_phisher/king-phisher-icon.svg /usr/share/icons/hicolor/scalable/apps
		fi
		if [ -f "/usr/share/icons/hicolor/index.theme" -a "$(command -v gtk-update-icon-cache)" ]; then
			echo "Updating the GTK icon cache"
			gtk-update-icon-cache --force /usr/share/icons/hicolor
		fi
	fi
	# try to install basemap directly from it's sourceforge tarball
	if python3 -m pip install http://downloads.sourceforge.net/project/matplotlib/matplotlib-toolkits/basemap-1.0.7/basemap-1.0.7.tar.gz &> /dev/null ; then
		echo "Successfully installed basemap with pip"
	else
		echo "Failed to install basemap with PIP, this is not a required dependency for King Phisher"
		echo "See https://github.com/securestate/king-phisher/wiki/Graphs#installing-basemap-with-pip for more information."
	fi
fi

if [ -z "$KING_PHISHER_SKIP_SERVER" ]; then
	if ! egrep "^${KING_PHISHER_GROUP}:" /etc/group &> /dev/null; then
		echo "Creating King Phisher admin group: '$KING_PHISHER_GROUP'"
		groupadd $KING_PHISHER_GROUP
		chown -R :$KING_PHISHER_GROUP $KING_PHISHER_DIR
	fi
	if [ ! -d "/var/king-phisher" ]; then
		mkdir /var/king-phisher
	fi
	chown nobody /var/king-phisher
	if [ ! -d "$KING_PHISHER_WEB_ROOT" ]; then
		mkdir $KING_PHISHER_WEB_ROOT
	fi

	if [ -e server_config.yml ]; then
		echo "Found previous server configuration, backing up to server_config.yml.bck{numbered}"
		cp --backup=numbered server_config.yml ./server_config.yml.bck
		BACKUP=true
	fi

	cp data/server/king_phisher/server_config.yml .
	sed -i -re "s|#\\s?data_path:.*$|data_path: $KING_PHISHER_DIR|" ./server_config.yml

	if [ "$KING_PHISHER_USE_POSTGRESQL" == "yes" ]; then
		if [ -f "/etc/init.d/postgresql" ]; then
			service postgresql start
			if ! service postgresql status &> /dev/null; then
				postgresql-setup --initdb &> /dev/null
				if ! service postgresql start &> /dev/null; then
					echo "ERROR: Could not start postgresql"
					exit
				fi
			fi
		fi
		if [ -f "/usr/lib/systemd/system/postgresql.service" ]; then
			systemctl start postgresql &> /dev/null
			if ! systemctl is-active &> /dev/null; then
				postgresql-setup --initdb &> /dev/null
				if ! systemctl start postgresql &> /dev/null; then
					echo "ERROR: Could not start postgresql"
					exit
				fi
			fi
		fi
		echo "Configuring the PostgreSQL server"
		PG_CONFIG_LOCATION=$(su postgres -c "psql -t -P format=unaligned -c 'show hba_file';")
		echo "PostgreSQL configuration file found at $PG_CONFIG_LOCATION"
		if ! grep -E "king_phisher" $PG_CONFIG_LOCATION &> /dev/null; then
			# put the king_phisher first in the line for localhost connects with md5
			sed -i '/# IPv4 local connections:/a\host    king_phisher    king_phisher    127.0.0.1/32            md5' $PG_CONFIG_LOCATION
			sed -i '/# IPv6 local connections:/a\host    king_phisher    king_phisher    ::1/128                 md5' $PG_CONFIG_LOCATION
		fi
		sed -i -re "s|database: sqlite://|#database: sqlite://|" ./server_config.yml
		# generate a random 32 character long password for postgresql
		PG_KP_PASSWORD=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' |  head -c 40)
		sed -i -re "s|#\\s?database: postgresql://.*$|database: postgresql://king_phisher:$PG_KP_PASSWORD@localhost/king_phisher|" ./server_config.yml
		if [[ -z "$(su postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='king_phisher'\"")" ]]; then
			su postgres -c "psql -c \"CREATE USER king_phisher WITH PASSWORD '$PG_KP_PASSWORD';\"" &> /dev/null
			echo "Created the PostgreSQL user 'king_phisher' with a random password"
		else
			echo "WARNING: The PostgreSQL king_phisher user already exists! The password will need"
			echo "WARNING: to be manually updated to match the one automatically generated by this"
			echo "WARNING: installation script by using the ALTER ROLE PostgreSQL command."
			echo "WARNING: or restore a backup server_config.yml.bck with the correct password."
		fi
		# restart postgresql to have hda_file updates take affect
		if [ -f "/etc/init.d/postgresql" ]; then
			/etc/init.d/postgresql restart &> /dev/null
		fi
		if [ -f "/usr/lib/systemd/system/postgresql.service" ]; then
			systemctl restart postgresql
		fi
	fi

	if [ -d "/lib/systemd/system" -a "$(command -v systemctl)" ]; then
		echo "Installing the King Phisher systemd service file in /lib/systemd/system/"
		cp data/server/service_files/king-phisher.service /lib/systemd/system
		sed -i -re "s|/opt\/king-phisher|$KING_PHISHER_DIR|g" /lib/systemd/system/king-phisher.service

		echo "Starting the King Phisher service"
		systemctl daemon-reload
		systemctl enable king-phisher.service
		systemctl start king-phisher.service
	elif [ "$LINUX_VERSION" == "Ubuntu" ]; then
		echo "Installing the King Phisher upstart service file in /etc/init/"
		cp data/server/service_files/king-phisher.conf /etc/init
		sed -i -re "s|/opt\/king-phisher|$KING_PHISHER_DIR|g" /etc/init/king-phisher.conf

		echo "Starting the King Phisher service"
		start king-phisher
	else
		echo "-----------------------------------------------------------------------------------------------"
		echo "Start the King Phisher server with the following command prior to starting the client:"
		echo "sudo $KING_PHISHER_DIR/KingPhisherServer -L INFO -f $KING_PHISHER_DIR/server_config.yml"
	fi
fi
if [ "$BACKUP" == "true" ]; then
	echo "-----------------------------------------------------------------------------------------------"
	echo "WARNING: If this is not a fresh install of King Phisher, you will need to restore your server_config.yml"
	echo "WARNING: the server_config.yml gets backup in numbered backups. Please cp the version you wish to restore"
	echo "EXAMPLE: cp server_config.yml.bck ./server_config.yml"
fi

if [ -z "$KING_PHISHER_SKIP_CLIENT" ]; then
	echo "-----------------------------------------------------------------------------------------------"
	echo "You can start the King Phisher client with the following command:"
	echo "$KING_PHISHER_DIR/KingPhisher"
fi
