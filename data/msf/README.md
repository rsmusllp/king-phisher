# SMS Plugin
The [SMS](./sms.rb) Metasploit plugin uses King Phisher's Rest API to send SMS messages when a new session is receive in Metasploit.
King Phisher's Rest API is accessible externally. This allows running the SMS plugin, within Metasploit, on a system other than the King Phisher server.
The system running Metasploit only needs to be able to make a HTTP GET request to the King Phisher server.

## King Phisher Configuration
Within King Phisher's 'server_config.yml' file, under 'rest_api' set the 'enabled' value to 'true'.
Change the 'token' value from 'null' to a secret string that will be used to access the King Phisher server's API remotely.
Running this one-liner in Linux will return a randomly generated 32 character string. At this point avoid using special characters.
`cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1`

Save the configuration file and restart the King Phisher server.

## Metasploit Usage
Add the [sms.rb](./sms.rb) file to your Metasploit 'plugins' directory.

If this is the first time using the SMS plugin, you will need to set four values which will be saved in '~/.msf4/sms.yml'.
On future use, these settings will be automatically loaded and do not need to be set again.

Additionally, you can see descriptions of the SMS plugin commands by running `help` in msfconsole.

Start Metasploit and load the SMS plugin.
`load sms`

Set the domain name of your King Phisher server.
`sms_set_server king-phisher.com`

Set the King Phisher server's API token.
`sms_set_token 0123456789abcdefABCDEF`

Set the cellphone number where you would like to receive SMS messages.
`sms_set_number 0123456789`

Set your cell phone carrier. Currently King Phisher supports AT&T, Boost, Sprint, T-Mobile, Verizon, Virgin Mobile.
`sms_set_carrier Boost`

Before saving, review your plugin settings.
`sms_show_params`

If everything looks good, save your settings.
`sms_save`

Start the SMS plugin monitoring for incoming settings.
`sms_start`

Stop the SMS plugin.
`sms_stop`
