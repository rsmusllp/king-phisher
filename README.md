# King Phisher [![Build Status](https://travis-ci.org/securestate/king-phisher.png)](https://travis-ci.org/securestate/king-phisher)
Python Phishing Campaign Toolkit

King Phisher facilitates running phishing-focused social engineering campaigns.

For instructions on how to install please see the INSTALL.md file. After installing, for instructions on how to get started please see the [wiki](https://github.com/securestate/king-phisher/wiki).

## License

King Phisher is released under the BSD 3-clause license, for more details see
COPYING file.

## Credits
Special Thanks (QA / Beta Testing):

 - Jake Garlie - jagar

 - Ken Smith - p4tchw0rk

King-Phisher Development Team:

 - Brandan Geise - coldfusion

 - Jeff McCutchan - jamcut

 - Spencer McIntyre - [zeroSteiner](https://github.com/zeroSteiner) ([@zeroSteiner](https://twitter.com/zeroSteiner))

## Client Configuration
The client configuration file is encoded in JSON and most options are configurable through the GUI interface.

The following options will be honored but are not configurable through the GUI:

* server_remote_port (Default: 80)
* mailer.max_messages_per_connection (Default: 5)
* ssh_preferred_key (Default: N/A)

### Message Template Variables
The client message template supports a number of variables each begining with $. These are included here as a reference.

Variable Name              | Variable Value
---------------------------|---------------
$webserver\_url            | Phishing Server URL
$uid                       | Unique Tracking Identifier
$first\_name               | The target's first name
$last\_name                | The target's last name
$company\_name             | Company Name
$email\_address            | The target's email address
$tracking\_dot\_url        | URL of an image used for message tracking
$tracking\_dot\_image\_tag | The tracking image in a preformatted ```<img />``` tag

The $webserver\_url and $uid variables are the most important and must be present in messages which are sent.
