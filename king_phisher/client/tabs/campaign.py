import collections
import os
import urlparse

from king_phisher.client.mailer import format_message, MailSenderThread
from king_phisher.client import utilities

from gi.repository import Gtk

class CampaignViewVisitTab(utilities.UtilityGladeGObject):
	gobject_ids = [
		'button_refresh',
		'treeview_campaign'
	]
	top_gobject = 'box'
	def __init__(self, *args, **kwargs):
		self.label = Gtk.Label('Visits')
		super(self.__class__, self).__init__(*args, **kwargs)
		treeview = self.gobjects['treeview_campaign']
		treeview.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
		columns = {1:'Email', 2:'Visitor IP', 3:'Visitor Details', 4:'Visit Count', 5:'First Visit', 6:'Last Visit'}
		for column_id in range(1, len(columns) + 1):
			column_name = columns[column_id]
			column = Gtk.TreeViewColumn(column_name, Gtk.CellRendererText(), text = column_id)
			column.set_sort_column_id(column_id)
			treeview.append_column(column)

	def signal_button_clicked_export(self, button):
		dialog = utilities.UtilityFileChooser('Export Data', self.parent)
		file_name = self.config['campaign_name'] + '.csv'
		response = dialog.run_quick_save(file_name)
		dialog.destroy()
		if not response:
			return
		destination_file = response['target_filename']
		utilities.export_treeview_liststore_csv(self.gobjects['treeview_campaign'], destination_file)

	def signal_button_clicked_refresh(self, button):
		self.load_campaign_information()

	def load_campaign_information(self):
		treeview = self.gobjects['treeview_campaign']
		store = treeview.get_model()
		if store == None:
			store = Gtk.ListStore(str, str, str, str, str, str, str)
			treeview.set_model(store)
		else:
			store.clear()
		page = 0
		visits = True
		while visits:
			visits = self.parent.rpc('campaign/visits/view', self.config['campaign_id'], page)
			page += 1
			if not visits:
				break
			for visit in visits:
				msg_id = visit['message_id']
				msg_details = self.parent.rpc.cache_call('message/get', msg_id)
				visitor_email = msg_details['target_email']
				store.append([visit['id'], visitor_email, visit['visitor_ip'], visit['visitor_details'], str(visit['visit_count']), visit['first_visit'], visit['last_visit']])

class CampaignViewTab(object):
	def __init__(self, config, parent):
		self.config = config
		self.parent = parent
		self.box = Gtk.VBox()
		self.box.show()
		self.label = Gtk.Label('View Campaign')

		self.notebook = Gtk.Notebook()
		self.notebook.connect('switch-page', self._tab_changed)
		self.notebook.set_scrollable(True)
		self.box.pack_start(self.notebook, True, True, 0)

		self.tabs = {}
		current_page = self.notebook.get_current_page()
		self.last_page_id = current_page

		visit_tab = CampaignViewVisitTab(self.config, self.parent)
		self.tabs['visit'] = visit_tab
		self.notebook.append_page(visit_tab.box, visit_tab.label)

		for tab in self.tabs.values():
			tab.box.show()
		self.notebook.show()

	def _tab_changed(self, notebook, current_page, index):
		previous_page = notebook.get_nth_page(self.last_page_id)
		self.last_page_id = index
		visit_tab = self.tabs.get('visit')
