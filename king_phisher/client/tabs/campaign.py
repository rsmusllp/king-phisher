import collections
import os
import urlparse

from king_phisher.client.mailer import format_message, MailSenderThread
from king_phisher.client.utilities import UtilityGladeGObject

from gi.repository import Gtk

class CampaignViewTab(UtilityGladeGObject):
	gobject_ids = [
		'button_refresh',
		'treeview_campaign'
	]
	top_gobject = 'box'
	def __init__(self, *args, **kwargs):
		self.label = Gtk.Label('Campaign')
		super(self.__class__, self).__init__(*args, **kwargs)
		treeview = self.gobjects['treeview_campaign']
		column = Gtk.TreeViewColumn('Email', Gtk.CellRendererText(), text = 1)
		treeview.append_column(column)
		column = Gtk.TreeViewColumn('Visitor IP', Gtk.CellRendererText(), text = 2)
		treeview.append_column(column)
		column = Gtk.TreeViewColumn('Visitor Details', Gtk.CellRendererText(), text = 3)
		treeview.append_column(column)
		column = Gtk.TreeViewColumn('First Visit', Gtk.CellRendererText(), text = 4)
		treeview.append_column(column)
		column = Gtk.TreeViewColumn('Last Visit', Gtk.CellRendererText(), text = 5)
		treeview.append_column(column)
		treeview.get_selection().set_mode(Gtk.SelectionMode.SINGLE)

	def signal_button_clicked(self, button):
		self.load_campaign_information()

	def load_campaign_information(self):
		treeview = self.gobjects['treeview_campaign']
		store = treeview.get_model()
		if store == None:
			store = Gtk.ListStore(str, str, str, str, str, str)
			treeview.set_model(store)
		else:
			store.clear()
		message_cache = {}
		page = 0
		visits = True
		while visits:
			visits = self.parent.rpc('campaign/visits/view', self.config['campaign_id'], page)
			page += 1
			if not visits:
				break
			for visit in visits:
				msg_id = visit['message_id']
				if not msg_id in message_cache:
					message_cache[msg_id] = self.parent.rpc('message/get', msg_id)
				visitor_email = message_cache[msg_id]['target_email']
				store.append([visit['id'], visitor_email, visit['visitor_ip'], visit['visitor_details'], visit['first_visit'], visit['last_visit']])
