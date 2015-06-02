# Install
The King Phisher Server is only supported on Linux. The King Phisher
Client is supported on both Windows and Linux. Windows executables are
available from the [releases page](https://github.com/securestate/king-phisher/releases).

An installation script is available to automate the process on supported versions
of Linux. Instructions on how it can be used are
[Linux Install Steps](#linux-install-steps) section.

## Overview
King Phisher uses a client server architecture. The ```KingPhisherServer```
application runs as a daemon on the phishing server. The ```KingPhisher```
client file is meant to connect to the daemon over SSH from a remote system. The
server must be running SSH and allow ports to be forwarded. The client after
connecting, communicates via RPC to the server through the encrypted SSH tunnel.

Additionally, the user logging in with the King Phisher Client will
require a valid local account on the King Phisher Server.

## Linux Install Steps

The following steps walk through installing King Phisher on Linux into a
self contained directory. Installing King Phisher into ```/opt/king-phisher```
is recommended.

King Phisher comes with an install script for a convenient installation process.
It will handle installing all of the operating system dependencies, the required
Python packages, and basic configuration. The automated install scripts supports
a limited set of Linux flavors. To request that one be added, please open a
support ticket.

After cloning the repository run the install.sh script that is in the tools
directory as such: ```sudo tools/install.sh```. This will download all the
required packages and set up a default server configuration. The automated
installation process may take up to 20 minutes to complete depending on
the speed at which packages are downloaded.

**WARNING:** If installing the server component of King Phisher, the automated
install script will use the template configuration file which specifies SQLite
as the database backend. It is highly recommended that PostgreSQL be used over
SQLite to support future database upgrades. For more information on selecting
and configuring a database backend, please see the
[wiki page](https://github.com/securestate/king-phisher/wiki/Database).

### Install Script Supported Flavors
| Linux Flavor | Client Support | Server Support |
|:-------------|:--------------:|:--------------:|
| BackBox      | yes            | yes            |
| CentOS       | no             | yes            |
| Debian       | yes            | yes            |
| Fedora       | yes            | yes            |
| Kali         | yes            | yes            |
| Ubuntu       | yes            | yes            |

### Install Script Environment Variables
Certain environment variables can be set to change the default behaviour of
the installation script.

| Variable Name               | Description                       | Default           |
|:----------------------------|:----------------------------------|:-----------------:|
| KING\_PHISHER\_DIR          | The base directory to install to  | /opt/king-phisher |
| KING\_PHISHER\_SKIP\_CLIENT | Skip installing client components | **NOT SET**       |
| KING\_PHISHER\_SKIP\_SERVER | Skip installing server components | **NOT SET**       |

Variables which are not set by default are flags which are toggled when defined.
For example to skip installing client components the following command could be
used: ```KING_PHISHER_SKIP_CLIENT=x tools/install.sh```

## Other Linux Versions
Install each of the required packages with
```pip install -r requirements.txt```. If any fail to install they are most
likely missing libraries that will need to be installed through the native
package manager.

## Required Packages
All required packages are listed in the provided ```requirements.txt``` file to
be easily installed with pip. Some packages may not install correctly due to
missing native libraries. The automated install script will handle the
installation of these libraries for the supported flavors of Linux.
