# Install
Before getting started install all of the required packages specified below

## Overview
King Phisher uses a client server architecture.  The KingPhisherServer file runs as a daemon on the phishing server.  The KingPhisher client is meant to connect to the daemon over SSH. The server must be running SSH and allow ports to be forwarded.

## Client Required Packages
[AdvancedHTTPServer](https://gist.github.com/zeroSteiner/4502576)

[Paramiko](https://github.com/paramiko/paramiko)

[PyGObject](https://wiki.gnome.org/PyGObject)

## Server Required Packages
[AdvancedHTTPServer](https://gist.github.com/zeroSteiner/4502576)

[PAM](http://atlee.ca/software/pam/)

[Msgpack-Python](https://github.com/msgpack/msgpack-python)

[dnspython](http://www.dnspython.org/)

## Kali Specific Notes

1. Copy the AdvancedHTTPServer.py and pam.py dependencies into the KingPhisher directory

1. Install additional client dependencies with the command: ```sudo apt-get install gir1.2-vte-2.90 gir1.2-webkit-3.0```

1. KingPhisher will not authenticate properly for root users, therefore, you need to set up a non-root user before it can be used.

1. Edit the config file to use /tmp/kingphisher.db folder for the database
