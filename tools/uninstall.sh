#!/bin/bash
# vim: tabstop=4 softtabstop=4 shiftwidth=4 noexpandtab
###############################################################################
# This is the Linux uninstall script for the King Phisher Client and
# Server on supported distributions.
#
# Project Home Page: https://github.com/securestate/king-phisher/
# Authors:
#   Erik Daguerre
#   Hunter DeMeyer
#
###############################################################################

E_USAGE=64
E_SOFTWARE=70
E_NOTROOT=87
FILE_NAME="$(dirname $(readlink -e $0) 2>/dev/null)/$(basename $0)"

answer_all_no=false
answer_all_yes=false

function prompt_yes_or_no {
	# prompt the user to answer a yes or no question, defaulting to yes if no
	# response is entered
	local __prompt_text=$1
	local __default_answer=$2
	local __result_var=$3
	if [ "$answer_all_no" == "true" ]; then
		$__result_var="no";
		return 0;
	elif [ "$answer_all_yes" == "true" ]; then
		eval $__result_var="yes";
		return 0;
	fi
	if [ "$__default_answer" == "yes" ]; then
		__prompt_text="$__prompt_text [Y/n] "
	elif [ "$__default_answer" == "no" ]; then
		__prompt_text="$__prompt_text [y/N] "
	else
		echo "PROGRAMMING ERROR (arg #2 must be yes or no)"
		exit $E_SOFTWARE
	fi
	while true; do
		read -p "$__prompt_text" _response
		case $_response in
			"" ) eval $__result_var="$__default_answer"; break;;
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
	echo "King Phisher uninstall Script"
	echo ""
	echo "optional arguments"
	echo "  -h, --help              show this help message and exit"
	echo "  -n, --no                answer no to all questions"
	echo "  -y, --yes               answer yes to all questions"
	echo "  --delete-database       delete the King Phisher database"
	echo "  --delete-directory      delete the King Phisher directory"
	echo "  --delete-config [USER]  delete the King Phisher configuration, optionally for USER" 
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
		--delete-database)
			KING_PHISHER_DELETE_DATABASE="x"
			;;
		--delete-directory)
			KING_PHISHER_DELETE_DIRECTORY="x"
			;;
		--delete-config)
			KING_PHISHER_DELETE_CONFIG="x"
			user="$(logname)"
			if [ ! -z $2 ]; then
				if [ ! "$(echo $2 | cut -c1)" == "-" ]; then
					if [ ! "$(id -u $2)" == "" ]; then
						user="$2"
					else
						exit $E_USAGE
					fi
				fi
			fi
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

if [ ! -z $KING_PHISHER_DELETE_DATABASE ]; then
	echo "WARNING: The King Phisher database will be deleted. All campaign data will be lost."
	prompt_yes_or_no "Are you sure you want to continue?" "no" KING_PHISHER_DELETE_CONFIRM
	if [ $KING_PHISHER_DELETE_CONFIRM == "yes" ]; then
		su postgres -c "psql -c \"DROP DATABASE king_phisher;\"" &> /dev/null
		su postgres -c "psql -c \"DROP USER king_phisher;\"" &> /dev/null

		PG_CONFIG_LOCATION=$(su postgres -c "psql -t -P format=unaligned -c 'show hba_file';")
		echo "PostgreSQL configuration file found at $PG_CONFIG_LOCATION"
		sed -i '/king_phisher/d' $PG_CONFIG_LOCATION
		echo "The King Phisher database has been removed"
	fi
fi

if [ ! -z $KING_PHISHER_DELETE_DIRECTORY ]; then
	if git status &> /dev/null; then
		KING_PHISHER_DIR="$(git rev-parse --show-toplevel)"
		echo "Git repo found at $KING_PHISHER_DIR"
	elif [ -d "$(dirname $(dirname $FILE_NAME))/king_phisher" ]; then
		KING_PHISHER_DIR="$(dirname $(dirname $FILE_NAME))"
		echo "Project directory found at $KING_PHISHER_DIR"
	fi
	echo "WARNING: The $KING_PHISHER_DIR directory will be removed"
	prompt_yes_or_no "Are you sure you want to continue?" "no" KING_PHISHER_DELETE_CONFIRM
	if [ $KING_PHISHER_DELETE_CONFIRM == "yes" ]; then
		rm -rf $KING_PHISHER_DIR
		echo "The King Phisher directory has been removed"
	fi
fi

if [ ! -z $KING_PHISHER_DELETE_CONFIG ]; then
	echo "Warning: The configuration for $user will be removed"
	prompt_yes_or_no "Are you sure you want to continue?" "no" KING_PHISHER_DELETE_CONFIRM
	if [ "$KING_PHISHER_DELETE_CONFIRM" == "yes" ]; then
		rm -rf "/home/$user/.config/king-phisher"
		echo "The King Phisher configuration for $user has been removed"
	fi
fi

if [ -f /lib/systemd/system/king-phisher.service ]; then
	if ! systemctl is-active king-phisher; then
		systemctl stop king-phisher
	fi
	if ! systemctl is-enabled king-phisher; then
		systemctl disable king-phisher
	fi
	rm /lib/systemd/system/king-phisher.service
	if [ -f /etc/systemd/system/multi-user.target.wants/king-phisher.service ]; then
		rm /etc/systemd/system/multi-user.target.wants/king-phisher.service
	fi
	systemctl daemon-reload
elif [ -f /etc/init/king-phisher.conf ]; then
	service king-phisher stop
	rm /etc/init/king-phisher.conf
fi
echo "Removed the King Phisher service files"

if [ -f "/usr/local/share/applications/king-phisher.desktop" ]; then
	rm /usr/local/share/applications/king-phisher.desktop
	echo "Removed the king-phisher.desktop file"
elif [ -f "/usr/share/applications/king-phisher.desktop" ]; then
	rm /usr/share/applications/king-phisher.desktop
	echo "Removed the king-phisher.desktop file"
fi
if [ -f /usr/share/icons/hicolor/scalable/apps/king-phisher-icon.svg ]; then
	rm /usr/share/icons/hicolor/scalable/apps/king-phisher-icon.svg
	echo "Removed the client King Phisher icon file"
fi

if [ -f "/usr/share/icons/hicolor/index.theme" -a "$(command -v gtk-update-icon-cache)" ]; then
	echo "Updating the GTK icon cache"
	gtk-update-icon-cache --force /usr/share/icons/hicolor
fi
