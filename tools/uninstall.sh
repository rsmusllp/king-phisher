#!/bin/bash
# vim: tabstop=4 softtabstop=4 shiftwidth=4 noexpandtab
###############################################################################
# This is the Linux uninstall script for the King Phisher Client and
# Server on supported distributions.
#
# Project Home Page: https://github.com/securestate/king-phisher/
# Authors:
#   Erik Daguerre
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
	echo "King Phisher uninstall Script"
	echo ""
	echo "optional arguments"
	echo "  -h, --help            show this help message and exit"
	echo "  -n, --no              answer no to all questions"
	echo "  -y, --yes             answer yes to all questions"
	echo "  --delete-database     delete the King Phisher database"
	echo "  --delete-directory    delete the King Phisher directory"
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

if [ $answer_all_yes == "true" ]; then
	KING_PHISHER_DELETE_DATABASE="x"
	KING_PHISHER_DELETE_DIRECTORY="x"
fi

if [ ! -z $KING_PHISHER_DELETE_DATABASE ]; then
	echo "WARNING: King Phisher Database will be deleted. All campaign data will be Lost"
	prompt_yes_or_no "Are you sure you want to continue" DATABASE_LAST_CHANCE
	if [ $DATABASE_LAST_CHANCE == "yes" ]; then
		su postgres -c "psql -c \"DROP DATABASE king_phisher;\"" &> /dev/null
		su postgres -c "psql -c \"DROP USER king_phisher;\"" &> /dev/null
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
	echo "WARNING: $KING_PHISHER_DIR directory will be removed"
	prompt_yes_or_no "Are you sure you want to continue" DIR_LAST_CHANCE
	if [ $DIR_LAST_CHANCE == "yes" ]; then
		rm -rf $KING_PHISHER_DIR
		echo "The King Phisher directory has been removed"
	fi
fi

if [ -f /lib/systemd/system/king-phisher.service ]; then
	systemctl stop king-phisher
	rm /lib/systemd/system/king-phisher.service
	if [ -f /etc/systemd/system/multi-user.target.wants/king-phisher.service ]; then
		rm /etc/systemd/system/multi-user.target.wants/king-phisher.service
	fi
	systemctl daemon-reload
	echo "Removed King Phisher systemd service files"
fi

if [ -f /etc/init/king-phisher.conf ]; then
	service king-phisher stop
	rm /etc/init/king-phisher.conf
	echo "Removed King Phisher initd service files"
fi

if [ -f "/usr/local/share/applications/king-phisher.desktop" ]; then
	rm /usr/local/share/applications/king-phisher.desktop
	echo "Removed king-phisher.desktop file"
elif [ -f "/usr/share/applications/king-phisher.desktop" ]; then
	rm /usr/share/applications/king-phisher.desktop
	echo "Removed king-phisher.desktop file"
fi
if [ -f /usr/share/icons/hicolor/scalable/apps/king-phisher-icon.svg ]; then
	rm /usr/share/icons/hicolor/scalable/apps/king-phisher-icon.svg
	echo "Removed the King Phisher icon"
fi

if [ -f "/usr/share/icons/hicolor/index.theme" -a "$(command -v gtk-update-icon-cache)" ]; then
	echo "Updating the GTK icon cache"
	gtk-update-icon-cache --force /usr/share/icons/hicolor
fi
