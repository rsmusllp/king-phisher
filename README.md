![alt text](https://github.com/securestate/king-phisher/raw/master/data/king-phisher-logo.png "King Phisher")

# King Phisher [![Build Status](https://travis-ci.org/securestate/king-phisher.png)](https://travis-ci.org/securestate/king-phisher)
Python Phishing Campaign Toolkit

King Phisher facilitates running phishing-focused social engineering campaigns.

For instructions on how to install please see the INSTALL.md file. After
installing, for instructions on how to get started please see the
[wiki](https://github.com/securestate/king-phisher/wiki).

## License
King Phisher is released under the BSD 3-clause license, for more details see
the COPYING file.

## Credits
Special Thanks (QA / Beta Testing):

 - Jake Garlie - jagar

 - Ken Smith - p4tchw0rk

King-Phisher Development Team:

 - Brandan Geise - coldfusion ([@coldfusion39](https://twitter.com/coldfusion39))

 - Jeff McCutchan - jamcut ([@jamcut](https://twitter.com/jamcut))

 - Spencer McIntyre - zeroSteiner ([@zeroSteiner](https://twitter.com/zeroSteiner))

## Code Documentation
King Phisher uses Sphinx for internal code documentation. This
documentation can be generated from source with the command
```sphinx-build docs/source docs/build```. The latest documentation is
kindly hosted on [ReadTheDocs](https://readthedocs.org/) at
[king-phisher.readthedocs.org](https://king-phisher.readthedocs.org/en/latest/).

## Client Configuration
The client configuration file is encoded in JSON and most options are
configurable through the GUI interface.

The following options will be honored but are not configurable through
the GUI:

* server_remote_port (Default: 80)
* mailer.max_messages_per_connection (Default: 5)
* ssh_preferred_key (Default: N/A)

### Message Template Variables
The client message templates are formatted using the Jinja engine and
support a number of variables. These are included here as a reference.

Variable Name              | Variable Value
---------------------------|---------------
uid                        | Unique Tracking Identifier
first\_name                | The target's first name
last\_name                 | The target's last name
company\_name              | Company Name
email\_address             | The target's email address
tracking\_dot\_image\_tag  | The tracking image in a preformatted ```<img />``` tag
url.tracking\_dot          | URL of an image used for message tracking
url.webserver              | Phishing Server URL with the uid paramater
url.webserver_raw          | Phishing Server URL without any parameters

The uid is the most important, and must be present in links that the
messages contain.
