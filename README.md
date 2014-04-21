# King Phisher [![Build Status](https://travis-ci.org/securestate/king-phisher.png)](https://travis-ci.org/securestate/king-phisher)
Python Phishing Campaign Toolkit

# Summary

## License

King Phisher is released under the BSD 3-clause license, for more details see
COPYING file.

# Credits
Special Thanks (QA / Beta Testing):

 - Jake Garlie - jagar

 - Ken Smith - p4tchw0rk

King-Phisher Development Team:

 - Brandan Geise - coldfusion

 - Jeff McCutchan - jamcut

 - Spencer McIntyre - zeroSteiner

## Client Configuration
The client configuration file is encoded in JSON and most options are configurable through the GUI interface.

The following options will be honored but are not configurable through the GUI:

* server_remote_port (Default: 80)
* mailer.max_messages_per_connection (Default: 5)
* ssh_preferred_key (Default: N/A)

### Message Template Variables
The client message template supports a number of variables each begining with $.

* $webserver\_url (Phishing Site URL example: &lt;a href="$webserver\_url?id=$uid"&gt;)
* $uid (Tracking User ID)
* $first\_name (First Name)
* $last\_name (Last Name)
* $company\_name (Company Name)
* $email\_address (Email Address)
* $tracking\_dot\_url (Tracking Dot URL)
* $tracking\_dot\_image\_tag (Tracking Dot Image Tag)

The $webserver\_url and $uid variables are the most important and must be present in messages which are sent.

## Server Configuration
The server configuration file is in the standard INI style.
