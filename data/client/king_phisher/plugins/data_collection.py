import argparse
import copy
import datetime
import hashlib
import sys

from king_phisher import color
from king_phisher import its
from king_phisher import json_ex
from king_phisher import version
import king_phisher.client.plugins as plugins
import king_phisher.client.gui_utilities as gui_utilities
import king_phisher.client.widget.extras as extras

from smoke_zephyr.utilities import unique

__version__ = '1.0'

def generate_hash(data, algorithm='sha256'):
	if its.py_v3 and isinstance(data, str):
		data = data.encode('utf-8')
	return algorithm + ':' + hashlib.new(algorithm, data).hexdigest()

def generate_signature(data):
	data = copy.deepcopy(data)
	data['hash'] = None
	return generate_hash(json_ex.dumps(data))

def verify_signature(data):
	if not data.get('hash'):
		return False
	return data['hash'] == generate_signature(data)

class Plugin(plugins.ClientPlugin):
	authors = ['Spencer McIntyre', 'Erik Daguerre']
	title = 'Anonymous Data Collection'
	description = """
	By default this plugin will be disabled, You must opt-in to this feature, to
	have your campaign data anonymize, furthermore you will need to email the data in
	for analyze.

	By enabling this plugin, you are allowing this plugin to anonymize your campaign
	data and prompt you to review the anonymous data collected and email it in for processing.
	"""
	homepage = 'http://github.com/securestate/king-phisher-plugins'
	options = [
		plugins.ClientOptionInteger('cycle_days', 'Number of days between reminders to submit data.', default=90,
									display_name='Cycle in Days'),
	]

	def initialize(self):
		version = __version__
		self.signal_connect('server-connected', self.server_connected)

		return True

	def server_connected(self, _):
		config = self.config
		if self.config.get('last_date'):
			if datetime.datetime.utcnow() - config['last_date'] < datetime.timedelta(days=config['cycle_days']):
				return
		dialog_txt = "It has been {} days since your last phishing data submission.\nWould you like to anonymize data for submission?".format(config['cycle_days'])
		if not gui_utilities.show_dialog_yes_no('Phishing Data Collection', self.application.get_active_window(), dialog_txt):
			return

		get_stats = StatsGenerator(self.application.rpc)
		stats = get_stats.generate_stats()

		dialog = extras.FileChooserDialog('Save Anonymized Data', self.application.get_active_window())
		file_name = 'anonmized_phishing_data.txt'
		response = dialog.run_quick_save(file_name)
		dialog.destroy()
		if not response['target_path']:
			return
		file = open(response['target_path'], 'w')
		file.write(stats)
		gui_utilities.show_dialog_info('Please review and email:\n {} \nto KingPhisher@securestate.com'.format(response['target_path']),
										self.application.get_active_window())
		config['last_date'] = datetime.datetime.utcnow()

class StatsGenerator(object):
	def __init__(self, rpc):
		self.rpc = rpc
		self.encoding = 'utf-8'

	def generate_stats(self):
		stats = {
			'campaigns': [],
			'generated': datetime.datetime.utcnow(),
			'version': {
				'king_phisher': version.distutils_version,
				'stats': __version__
			}
		}
		rpc = self.rpc
		for campaign in rpc.remote_table('campaigns'):
			stats['campaigns'].append(self._campaign_stats(campaign))
		stats['hash'] = generate_signature(stats)
		return json_ex.dumps(stats)

	def _campaign_stats(self, campaign):
		rpc = self.rpc
		messages = list(rpc.remote_table('messages', query_filter={'campaign_id': campaign.id}))
		visits = list(rpc.remote_table('visits', query_filter={'campaign_id': campaign.id}))
		credentials = list(rpc.remote_table('credentials', query_filter={'campaign_id': campaign.id}))
		stats = {
			'created': campaign.created,
			'expiration': campaign.expiration,
			'reject_after_credentials': campaign.reject_after_credentials,
			'id': campaign.id,
			'name': generate_hash(campaign.name),
			'messages': {
				'total': len(messages),
				'unique': {
					'by_target': len(unique(messages, key=lambda message: message.target_email)),
				}
			},
			'visits': {
				'total': len(visits),
				'unique': {
					'by_message': len(unique(visits, key=lambda visit: visit.message_id)),
				}
			},
			'credentials': {
				'total': len(credentials),
				'unique': {
					'by_message': len(unique(credentials, key=lambda credential: credential.message_id)),
					'by_visit': len(unique(credentials, key=lambda credential: credential.visit_id))
				}
			}
		}
		return stats

def main():
	parser = argparse.ArgumentParser(description='Stat File Verification', conflict_handler='resolve')
	parser.add_argument('-v', '--version', action='version', version='%(prog)s Version: ' + __version__)
	parser.add_argument('data_file', type=argparse.FileType('r'), help='the stats file to verify')
	arguments = parser.parse_args()

	try:
		data = json_ex.load(arguments.data_file)
	except:
		color.print_error('failed to load the data')
		return 1
	else:
		color.print_status('loaded the statistics data')
	finally:
		arguments.data_file.close()

	if not verify_signature(data):
		color.print_error('the signature is invalid')
		return 1

	color.print_good('the signature is valid')
	return 0

if __name__ == '__main__':
	sys.exit(main())