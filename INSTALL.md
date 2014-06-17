# Install
The King Phisher server is only supported on Linux. The King Phishser
client is supported on both Windows and Linux. Windows executables are
available from the
[releases page](https://github.com/securestate/king-phisher/releases).

Before getting started, install all of the required packages specified below.

## Overview
King-Phisher uses a client server architecture. The
```KingPhisherServer``` file runs as a daemon on the phishing server.
The ```KingPhisher``` client file is meant to connect to the daemon over
SSH. The server must be running SSH and allow ports to be forwarded. The
 client, after connecting communicates via RPC to the server through the
  encrypted SSH tunnel.

Additionally, the user logging in with the King-Phisher client will
require a valid local account on the KingPhisherServer.

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

### Client and Server on Ubuntu 14.04 / Kali 1.0
After cloning the directory run the install.sh script that is in the tools
directory as such: ```sudo tools/install.sh```. This will download all the
required packages and set up a default server configuration.

### Other Linux Versions
Install each of the required packages with
```pip install -r requirements.txt```. If any fail to install they are most
likely missing libraries that will need to be installed through the native
package manager.
