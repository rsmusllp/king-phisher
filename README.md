King Phisher
==
Python Phishing Campaign Toolkit

License
--
King Phisher is released under the BSD 3-clause license, for more details see
COPYING file.

Required Packages (Client)
--
[Paramiko](https://github.com/paramiko/paramiko)

[PyGObject](https://wiki.gnome.org/PyGObject)

Required Packages (Server)
--
[AdvancedHTTPServer](https://gist.github.com/zeroSteiner/4502576)

[PAM](http://atlee.ca/software/pam/)

Client Configuration
--

The client configuration file is encoded in JSON and most options are configurable through the GUI interface.

The following options will be honored but are not configurable through the GUI:

* server_remote_port (Default: 80)
* mailer.max_messages_per_connection (Default: 5)

Server Configuration
--
The server configuration file is in the standard INI style.
