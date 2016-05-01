import distutils.version

import king_phisher.version as version
import king_phisher.client.plugins as plugins
import king_phisher.client.gui_utilities as gui_utilities

import requests

StrictVersion = distutils.version.StrictVersion

def release_to_version(release):
	return StrictVersion(release['tag_name'][1:])

def get_latest_release():
	releases = requests.get('https://api.github.com/repos/securestate/king-phisher/releases').json()
	releases = [release for release in releases if not release['draft']]
	releases = sorted(
		releases,
		key=release_to_version,
		reverse=True
	)
	return releases[0]

class Plugin(plugins.ClientPlugin):
	authors = ['Spencer McIntyre']
	title = 'Check For Updates'
	description = """
	Automatically check for updates to the King Phisher project by inspecting
	the latest GitHub releases. If a new version has been released, the user
	will be notified with a dialog box after logging into the server.
	"""
	homepage = 'https://github.com/securestate/king-phisher'
	req_min_version = '1.0'
	def initialize(self):
		self.signal_connect('server-connected', self.signal_server_connected)
		return True

	def signal_server_connected(self, _):
		release = get_latest_release()
		self.logger.info('found latest release: ' + release['tag_name'])
		client_version = StrictVersion(version.distutils_version)
		release_version = release_to_version(release)
		server_version = self.application.rpc('version')['version_info']
		server_version = StrictVersion("{major}.{minor}.{micro}".format(**server_version))
		out_of_date = None

		if release_version > client_version:
			out_of_date = 'Client'
		elif release_version > server_version:
			out_of_date = 'Server'
		if out_of_date is None:
			return

		gui_utilities.show_dialog_info(
			'New Version Available',
			self.application.main_window,
			"The King Phisher {part} is out of date,\n"
			"<a href=\"{release[html_url]}\">{release[tag_name]}</a> is now available.".format(part=out_of_date, release=release),
			secondary_use_markup=True
		)

