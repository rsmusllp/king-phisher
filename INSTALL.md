# Install
Before getting started install all of the required packages specified below

## Overview
King Phisher uses a client server architecture.  The KingPhisherServer file runs as a daemon on the phishing server.  The KingPhisher client is meant to connect to the daemon over SSH. The server must be running SSH and allow ports to be forwarded.

## Client Required Packages
[Paramiko](https://github.com/paramiko/paramiko)

[PyGObject](https://wiki.gnome.org/PyGObject)

## Server Required Packages
[Msgpack-Python](https://github.com/msgpack/msgpack-python)

[dnspython](http://www.dnspython.org/)

## Install Steps

### Client Ubuntu 13.04/13.10
1. Install required packages: ```sudo apt-get install python-gobject python-gobject-dev python-paramiko```
1. Download King-Phisher from GitHub: ```git clone https://github.com/securestate/king-phisher.git```
1. Start the client by running: ```./KingPhisher```

### Client Kali 1.03
1. Install required packages: ```sudo apt-get install python-gobject python-gobject-dev gir1.2-vte-2.90 gir1.2-webkit-3.0 python-paramiko```
1. Download King-Phisher from GitHub: ```git clone https://github.com/securestate/king-phisher.git```
1. Start the client by running ```./KingPhisher```

### Server Ubuntu 13.04/13.10
1. Install required packages: ```sudo apt-get install python-dnspython msgpack-python msgpack-python```
1. Download King-Phisher: ```git clone https://github.com/securestate/king-phisher.git```
1. Open server.conf.txt with a text editor and change the "web_root" field to the location where you want to serve your phishing website html files. Save the file as server.conf.
1. Start a screen session "screen -S KingPhisherServer"
1. Run ```./KingPhisherServer -L INFO --foreground server.conf``` pointing to your modified server.conf file
