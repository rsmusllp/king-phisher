# Install
Before getting started, install all of the required packages specified below.

## Overview
King-Phisher uses a client server architecture.  The ```KingPhisherServer``` file runs as a daemon on the phishing server.  The ```KingPhisher``` client file is meant to connect to the daemon over SSH. The server must be running SSH and allow ports to be forwarded. The client, after connecting communicates via RPC to the server through the encrypted SSH tunnel.

Additionally, the user logging in with the King-Phisher client will require a valid local account on the KingPhisherServer.

## Client Required Packages
[Paramiko](https://github.com/paramiko/paramiko)

[PyGObject](https://wiki.gnome.org/PyGObject)

## Client Optional Packages
[Matplotlib](http://matplotlib.org/)

[Msgpack-Python](https://github.com/msgpack/msgpack-python)

## Server Required Packages
[dnspython](http://www.dnspython.org/)

[Msgpack-Python](https://github.com/msgpack/msgpack-python)

[PyYAML](http://pyyaml.org/)

## Install Steps
1. Download King-Phisher from GitHub: ```git clone https://github.com/securestate/king-phisher.git```
1. Change directory into king-phisher: ```cd king-phisher```
1. Install Python dependencies with PIP ```sudo pip install -r requirements.txt```
1. Skip to the next section depending on if you're install the client or server.

### Client on Ubuntu 13.04 / 13.10 / 14.04
1. Install required system packages: ```sudo apt-get install python-gobject python-gobject-dev```
1. Install the King-Phisher Client: ```sudo python tools/setup_client.py build && sudo python tools/setup_client.py install```

### Client on Kali 1.04
1. Install required packages: ```sudo apt-get install python-gobject python-gobject-dev gir1.2-vte-2.90 gir1.2-webkit-3.0```
1. Install the King-Phisher Client: ```sudo python tools/setup_client.py build && sudo python tools/setup_client.py install```

### Server on Ubuntu 13.04 / 13.10 / 14.04
1. Install the King-Phisher Server: ```sudo python tools/setup_server.py build && sudo python tools/setup_server.py install```
1. Install the King-Phisher Service file: ```sudo cp data/server/service_files/king-phisher.conf /etc/init/```
1. Open data/server/king_phisher/server_config.yml with a text editor and change the "web_root" field to the location where you want to serve your phishing website html files. Save the file as ```/etc/king-phisher.yml```.
1. Run ```sudo start king-phisher```
