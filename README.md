![alt text](https://github.com/securestate/king-phisher/raw/master/data/king-phisher-logo.png "King Phisher")

# King Phisher
Phishing Campaign Toolkit

[![Documentation Status](https://readthedocs.org/projects/king-phisher/badge/?version=latest&style=flat-square)](http://king-phisher.readthedocs.org/en/latest)
[![Github Issues](http://img.shields.io/github/issues/securestate/king-phisher.svg?style=flat-square)](https://github.com/securestate/king-phisher/issues)

King Phisher is a tool for testing and promoting user awareness by simulating
real world phishing attacks. It features an easy to use, yet very flexible
architecture allowing full control over both emails and server content.
King Phisher can be used to run campaigns ranging from simple awareness
training to more complicated scenarios in which user aware content is served
for harvesting credentials.

King Phisher is only to be used for legal applications when the explicit
permission of the targeted organization has been obtained.

Get the latest stable version from the
[GitHub Releases Page](https://github.com/securestate/king-phisher/releases) or
use git to checkout the project from source.

For instructions on how to install, please see the
[INSTALL.md](https://github.com/securestate/king-phisher/blob/master/INSTALL.md)
file. After installing, for instructions on how to get started please see the
[wiki](https://github.com/securestate/king-phisher/wiki).

![alt text](https://raw.githubusercontent.com/securestate/king-phisher/screenshots/dashboard.png "Campaign Dashboard")

## License
King Phisher is released under the BSD 3-clause license, for more details see
the [LICENSE](https://github.com/securestate/king-phisher/blob/master/LICENSE) file.

## Credits
Special Thanks (QA / Beta Testing):

 - Jake Garlie - jagar
 - Ken Smith - p4tchw0rk
 - Brianna Whittaker

King Phisher Development Team:

 - Brandan Geise - coldfusion ([@coldfusion39](https://twitter.com/coldfusion39))
 - Jeff McCutchan - jamcut ([@jamcut](https://twitter.com/jamcut))
 - Spencer McIntyre - zeroSteiner ([@zeroSteiner](https://twitter.com/zeroSteiner))

## Template Files
Template files for both messages and server pages can be found in the separate
King Phisher [Templates repository](https://github.com/securestate/king-phisher-templates).
Any contributions regarding templates should also be submitted via a pull
request to the templates repository.

## Code Documentation
King Phisher uses Sphinx for internal code documentation. This
documentation can be generated from source with the command
```sphinx-build -b html docs/source docs/html```. The latest documentation is
kindly hosted on [ReadTheDocs](https://readthedocs.org/) at
[king-phisher.readthedocs.org](https://king-phisher.readthedocs.org/en/latest/).

## Client Configuration
The client configuration file is encoded in JSON and most options are
configurable through the GUI interface.

The following options will be honored but are not configurable through
the GUI:

* gui.refresh_frequency (Default: 5 minutes)
* mailer.max_messages_per_connection (Default: 5)
* rpc.serializer (Default: Automatically determined)
* ssh_preferred_key (Default: N/A)

### Message Template Variables
The client message templates are formatted using the Jinja2 templating engine
and support a number of variables. These are included here as a reference, check
the templates [wiki page](https://github.com/securestate/king-phisher/wiki/Templates)
for comprehensive documentation.

Variable Name              | Variable Value
---------------------------|---------------
client.company\_name       | The target's company name
client.email\_address      | The target's email address
client.first\_name         | The target's first name
client.last\_name          | The target's last name
client.message\_id         | The unique tracking identifier (this is the same as uid)
sender.email               | The email address in the "Source Email (MIME)" field
sender.friendly\_alias     | The value of the "Friendly Alias" field
sender.reply\_to           | The value of the "Reply To" field
url.tracking\_dot          | URL of an image used for message tracking
url.webserver              | Phishing server URL with the uid parameter
url.webserver\_raw         | Phishing server URL without any parameters
tracking\_dot\_image\_tag  | The tracking image in a preformatted ```<img />``` tag
uid                        | The unique tracking identifier (this is the same as client.message_id)

The uid is the most important, and must be present in links that the messages
contain.
