Change Log
==========

This document contains notes on the major changes for each version of King
Phisher.

Version 1.x.x
-------------

Version 1.8.0
^^^^^^^^^^^^^

*In Progress*

* Install script now supports Red Hat Server 7

Version 1.7.0
^^^^^^^^^^^^^

Released :release:`1.7.0` on April 4th, 2017

* Better error messages for malformed server configuration files
* Support for sending to targets via To / CC / BCC fields
* New features for client and server plugins
* Add comparison of "trained" statistics to the campaign comparison
* Support for including and importing Jinja templates from relative paths
* Support for including custom HTTP headers in server responses
* New feature to import Campaigns from XML files
* Support for emails address with longer top level domain names

Version 1.6.0
^^^^^^^^^^^^^

Released :release:`1.6.0` on January 31st, 2017

* Support negotiating STARTTLS with SMTP servers that support it
* Support for real time event publishing to the client
* Support for a new GraphQL API for more efficient data queries
* More flexibility in configuring server logging
* Add persistent storage for server plugin data
* Add a Jinja function to check if a password is complex
* Add client ``message-data-export`` and ``message-data-import`` signals
* King Phisher now starts with Python3 by default
* ``tools/install.sh`` now creates a backup  of server_config.yml when present

* Minor bug fixes

   * Minor CSS fixes
   * Special characters now display in the UI correctly

Version 1.5.2
^^^^^^^^^^^^^

Released :release:`1.5.2` on December 23rd, 2016

* Minor bug fixes

   * Use Default SMS sender to fix SMS subscription with T-Mobile
   * Upgrade AdvancedHTTPServer to v2.0.6 to fix select polling
   * Corrected issue when attachment file is inaccessible
   * Fixed issue when message file directory is gone
   * Fixed server side encoding error with basic auth
   * Fixed TypeError handling while rendering templates
   * Fixed a unicode bug when processing targets csv
   * Fixed install.sh script for CentOS7 and python3
   * Fixed show exception dialog with Glib idle_add
   * Fixed a logic bug causing premature SMTP reconnects
   * Fixed Webkit-1 load_string Null error

Version 1.5.1
^^^^^^^^^^^^^

Released :release:`1.5.1` on October 3rd, 2016

* Automated installation script improvements

   * Backup an existing server configuration file
   * Log warnings when the PostgreSQL user exists

* Improve the Metasploit plugin for session notifications via SMS
* Support exporting credentials for use with Metasploit's ``USERPASS_FILE`` option

Version 1.5.0
^^^^^^^^^^^^^

Released :release:`1.5.0` on September 22nd, 2016

* Added an SPF button to the client for on demand SPF record checking
* Fixed missing packages in the Windows build for timezone data
* Transitioned to the dnspython package for Python 2.x and 3.x

Version 1.4.0
^^^^^^^^^^^^^

Released :release:`1.4.0` on August 5th, 2016

* Added additional Jinja variables for server pages
* Upgraded to AdvancedHTTPServer version 2

   * Added support for binding to multiple interfaces
   * Added support for multiple SSL hostnames via SNI

* Support for plugins in the server application
* Added server signals for event subscriptions in plugins
* Updated the style for GTK 3.20
* Start to warn users about the impending Python 2.7 deprecation
* Change to installing for Python 3
* Added an uninstallation script

Version 1.3.0
^^^^^^^^^^^^^

Released :release:`1.3.0` on May 17th, 2016

* Added automatic setup of PostgreSQL database for the server
* Server bug fixes when running on non-standard HTTP ports
* Added completion to the messaged editor
* Support for plugins in the client application
* Added a client plugin to automatically check for updates
* Added a client plugin to generate anonmous statistics
* Added debug logging of parameters for key RPC methods
* Lots of Python 3.x compatiblity fixes

Version 1.2.0
^^^^^^^^^^^^^

Released :release:`1.2.0` on March 18th, 2016

* SSH host key validation
* Install script command line flags
* Support for authenticating to SMTP servers
* Style and compatibility changes for Kali

Version 1.1.0
^^^^^^^^^^^^^

Released :release:`1.1.0` on December 30th, 2015

* Added an option to send a message to a single target
* Support for sending calendar invite messages
* Added PostgreSQL setup to the installer
* Support for exporting to Excel
* Added a Jupyter notebook for interactive data analysis
* Added additional campaign filtering options
* Support for removal of metadata from Microsoft Office 2007+ documents

Version 1.0.0
^^^^^^^^^^^^^

Released :release:`1.0.0` on October 15th, 2015

* Moved templates to a dedicated separate repository
* Added a custom theme for the client
* Added support for two factor authentication with TOTP
* Support for specifying an img style attribute for inline images in messages

Version 0.x.x
-------------

Version 0.3.0
^^^^^^^^^^^^^

Released :release:`0.3.0` on August 21st, 2015

* Added a new campaign creation assistant
* Support for expiring campaigns at a specified time
* Track more details when messages are opened such as the IP address and User Agent
* Support for tagging campaign types
* Support for organizing campaigns by companies
* Support for storing email recipients department name
* Support for collecting credentials via Basic Auth

Version 0.2.1
^^^^^^^^^^^^^

Released :release:`0.2.1` on July 14th, 2015

* Added syntax highlighting to the message edit tab
* Technical documentation improvements, including documenting the REST API
* Support reloading message templates when they change from an external editor
* Support for pulling the client IP from a cookie set by an upstream proxy
* Support for embedding training videos from YouTube
* Added a Metasploit plugin for using the REST API to send SMS messages
* Support for exporting visit information to GeoJSON

Version 0.2.0
^^^^^^^^^^^^^

Released :release:`0.2.0` on April 28th, 2015

* Added additional graphs including maps when basemap is available
* Added geolocation support
* Made dashboard layout configurable
* Support for cloning web pages
* Support for installing on Fedora
* Support for running the server with Docker

Version 0.1.7
^^^^^^^^^^^^^

Released :release:`0.1.7` on February 19th, 2015

* Added make_csrf_page function
* Added server support for SSL
* Support verifying the server configuration file
* Added a desktop file and icon for the client GUI
* Added support for operating on multiple rows in the client's campaign tables
* Support starting an external SFTP application from the client
* Tweaked miscellaneous features to scale for larger campaigns (35k+ messages)
* Updated AdvancedHTTPServer to version 0.4.2 which supports Python 3
* Added integration for checking Sender Policy Framework (SPF) records

Version 0.1.6
^^^^^^^^^^^^^

Released :release:`0.1.6` on November 3rd, 2014

* Migrated to SQLAlchemy backend (SQLite will no longer be supported for database upgrades)
* Added additional documentation to the wiki
* Enhanced error handling and UI documentation for a better user experience
* Support for quickly adding common dates and times in the message editor

Version 0.1.5
^^^^^^^^^^^^^

Released :release:`0.1.5` on September 29th, 2014

* Added support for inline images in emails
* Import and export support for message configurations
* Highlight the current campaign in the selection dialog

Version 0.1.4
^^^^^^^^^^^^^

Released :release:`0.1.4` on September 4th, 2014

* Full API documentation
* Install script for Kali & Ubuntu
* Lots of bug fixes

Version 0.1.3
^^^^^^^^^^^^^

Released :release:`0.1.3` on June 4th, 2014

* Jinja2 templates for both the client and server
* API version checking to warn when the client and server versions are incompatible
