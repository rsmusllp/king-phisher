# King Phisher
Python Phishing Campaign Toolkit

# Summary

## License

King Phisher is released under the BSD 3-clause license, for more details see
COPYING file.

# Credits
Special Thanks (QA / Beta Testing):

 - Jake Garlie - jagar

 - Brandan Geise - coldfusion

 - Ken Smith - p4tchw0rk

King-Phisher Development Team:

 - Jeff McCutchan - jamcut

 - Spencer McIntyre - zeroSteiner

## Client Required Packages
[AdvancedHTTPServer](https://gist.github.com/zeroSteiner/4502576)

[Paramiko](https://github.com/paramiko/paramiko)

[PyGObject](https://wiki.gnome.org/PyGObject)

## Server Required Packages
[AdvancedHTTPServer](https://gist.github.com/zeroSteiner/4502576)

[PAM](http://atlee.ca/software/pam/)

## Client Configuration
The client configuration file is encoded in JSON and most options are configurable through the GUI interface.

The following options will be honored but are not configurable through the GUI:

* server_remote_port (Default: 80)
* mailer.max_messages_per_connection (Default: 5)

## Server Configuration
The server configuration file is in the standard INI style.
