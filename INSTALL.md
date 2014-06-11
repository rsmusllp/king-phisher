# Install
The King Phisher server is only supported on Linux.  The King Phishser client is supported on both Windows and Linux. Windows executables are available from the [releases page](https://github.com/securestate/king-phisher/releases).

Before getting started, install all of the required packages specified below.

## Overview
King-Phisher uses a client server architecture.  The ```KingPhisherServer``` file runs as a daemon on the phishing server.  The ```KingPhisher``` client file is meant to connect to the daemon over SSH. The server must be running SSH and allow ports to be forwarded. The client, after connecting communicates via RPC to the server through the encrypted SSH tunnel.

Additionally, the user logging in with the King-Phisher client will require a valid local account on the KingPhisherServer.

## Client Required Packages
* [Jinja2](http://jinja.pocoo.org/)
* [Paramiko](https://github.com/paramiko/paramiko)
* [PyGObject](https://wiki.gnome.org/PyGObject)

## Client Optional Packages
* [Matplotlib](http://matplotlib.org/)
* [Msgpack-Python](https://github.com/msgpack/msgpack-python)

## Server Required Packages
* [dnspython](http://www.dnspython.org/)
* [Jinja2](http://jinja.pocoo.org/)
* [Msgpack-Python](https://github.com/msgpack/msgpack-python)
* [PyYAML](http://pyyaml.org/)

## Linux Install Steps
The following steps walk through installing King-Phisher on Linux into a
self contained directory. Installing King-Phisher into ```/opt/king-phisher```
is recommended.

### Download from Git
1. Download King-Phisher from GitHub: ```git clone https://github.com/securestate/king-phisher.git```
1. Change directory into king-phisher: ```cd king-phisher```
1. Skip to the next section depending on if you're install the client or the server.

### Client on Ubuntu 13.04 / 13.10 / 14.04
1. Install required packages: ```sudo apt-get install -qq gir1.2-gtk-3.0 gir1.2-vte-2.90 gir1.2-webkit-3.0 python-cairo python-gi python-gi-cairo python-gobject python-gobject-2 python-gobject-dev python-paramiko```
1. Install Python dependencies with PIP ```sudo pip install -r requirements.txt```
1. Run the King-Phisher Client: ```./KingPhisher```

### Client on Kali
1. Install required packages: ```sudo apt-get install python-gobject python-gobject-dev python-pip gir1.2-vte-2.90 gir1.2-webkit-3.0```
1. Install Python dependencies with PIP ```sudo pip install -r requirements.txt```
1. Run the King-Phisher Client: ```./KingPhisher```

### Server on Ubuntu 13.04 / 13.10 / 14.04
1. Install required packages: ```sudo apt-get install -qq gir1.2-gtk-3.0 gir1.2-vte-2.90 gir1.2-webkit-3.0 python-cairo python-gi python-gi-cairo python-gobject python-gobject-2 python-gobject-dev python-paramiko```
1. Install Python dependencies with PIP ```sudo pip install -r requirements.txt```
1. Copy the default server configuration file: ```cp data/server/king_phisher/server_config.yml .```
1. Open server_config.yml with a text editor and change any settings. The remaining steps assume all the defaults are used.
1. Create the database directory: ```sudo mkdir /var/king-phisher; chown nobody /var/king-phisher```
 * SQLite requires write permissions to the directory containing the database file.
1. Run the King-Phisher Server: ```sudo ./KingPhisherServer server_config.yml```
 * Check the KingPhisherServer help menu for command line options.
