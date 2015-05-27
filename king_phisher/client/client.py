#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/client.py
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are
#  met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following disclaimer
#    in the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of the project nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import logging
import shlex

from king_phisher import find
from king_phisher import utilities
from king_phisher.client import dialogs
from king_phisher.client import export
from king_phisher.client import graphs
from king_phisher.client import gui_utilities
from king_phisher.client import tools
from king_phisher.client.tabs.campaign import CampaignViewTab
from king_phisher.client.tabs.mail import MailSenderTab

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Gtk

if isinstance(Gtk.ApplicationWindow, utilities.Mock):
	_Gtk_ApplicationWindow = type('Gtk.ApplicationWindow', (object,), {})
	_Gtk_ApplicationWindow.__module__ = ''
else:
	_Gtk_ApplicationWindow = Gtk.ApplicationWindow

class MainMenuBar(gui_utilities.GladeGObject):
	"""
	The main menu bar for the primary application window. This configures any
	optional menu items as well as handles all the menu item signals
	appropriately.
	"""
	top_gobject = 'menubar'
	def __init__(self, config, window, application):
		self.application = application
		assert isinstance(window, KingPhisherClient)
		super(MainMenuBar, self).__init__(config, window)
		self._add_accelerators()
		graphs_menu_item = self.gtk_builder_get('menuitem_tools_create_graph')
		if graphs.has_matplotlib:
			graphs_submenu = Gtk.Menu.new()
			for graph_name in graphs.get_graphs():
				graph = graphs.get_graph(graph_name)
				menu_item = Gtk.MenuItem.new_with_label(graph.name_human)
				menu_item.connect('activate', self.do_tools_show_campaign_graph, graph_name)
				graphs_submenu.append(menu_item)
			graphs_menu_item.set_submenu(graphs_submenu)
			graphs_menu_item.show_all()
		else:
			graphs_menu_item.set_sensitive(False)

	def _add_accelerators(self):
		accelerators = (
			('file_open', Gdk.KEY_o, Gdk.ModifierType.CONTROL_MASK),
			('file_quit', Gdk.KEY_q, Gdk.ModifierType.CONTROL_MASK),
			('tools_rpc_terminal', Gdk.KEY_F1, Gdk.ModifierType.CONTROL_MASK),
			('tools_sftp_client', Gdk.KEY_F2, Gdk.ModifierType.CONTROL_MASK)
		)
		for menu_name, key, modifier in accelerators:
			menu_item = self.gtk_builder_get('menuitem_' + menu_name)
			menu_item.add_accelerator('activate', self.parent.accel_group, key, modifier, Gtk.AccelFlags.VISIBLE)

	def do_edit_delete_campaign(self, _):
		self.parent.delete_campaign()

	def do_edit_rename_campaign(self, _):
		self.parent.rename_campaign()

	def do_edit_preferences(self, _):
		self.parent.edit_preferences()

	def do_edit_stop_service(self, _):
		self.parent.stop_remote_service()

	def do_export_campaign_xml(self, _):
		self.parent.export_campaign_xml()

	def do_export_message_data(self, _):
		self.parent.tabs['mailer'].export_message_data()

	def do_import_message_data(self, _):
		self.parent.tabs['mailer'].import_message_data()

	def do_show_campaign_selection(self, _):
		self.application.show_campaign_selection()

	def do_quit(self, _):
		self.parent.emit('exit-confirm')

	def do_tools_rpc_terminal(self, _):
		tools.KingPhisherClientRPCTerminal(self.config, self.parent, self.parent.get_property('application'))

	def do_tools_clone_page(self, _):
		dialogs.ClonePageDialog(self.config, self.parent).interact()

	def do_tools_sftp_client(self, _):
		self.parent.start_sftp_client()

	def do_tools_show_campaign_graph(self, _, graph_name):
		self.application.show_campaign_graph(graph_name)

	def do_help_about(self, _):
		dialogs.AboutDialog(self.config, self.parent).interact()

	def do_help_wiki(self, _):
		utilities.open_uri('https://github.com/securestate/king-phisher/wiki')

class KingPhisherClient(_Gtk_ApplicationWindow):
	"""
	This is the top level King Phisher client object. It contains the
	custom GObject signals, and keeps all the GUI references. This is also the
	parent window for most GTK objects.

	:GObject Signals: :ref:`gobject-signals-window-label`
	"""
	__gsignals__ = {
		'exit': (GObject.SIGNAL_RUN_LAST, None, ()),
		'exit-confirm': (GObject.SIGNAL_RUN_LAST, None, ())
	}
	def __init__(self, config, application):
		"""
		:param dict config: The main King Phisher client configuration.
		:param application: The application instance to which this window belongs.
		:type application: :py:class:`.KingPhisherClientApplication`
		"""
		assert isinstance(application, Gtk.Application)
		super(KingPhisherClient, self).__init__(application=application)
		self.application = application
		self.logger = logging.getLogger('KingPhisher.Client.MainWindow')
		self.config = config
		"""The main King Phisher client configuration."""
		self.set_property('title', 'King Phisher')
		vbox = Gtk.Box()
		vbox.set_property('orientation', Gtk.Orientation.VERTICAL)
		vbox.show()
		self.add(vbox)
		default_icon_file = find.find_data_file('king-phisher-icon.svg')
		if default_icon_file:
			icon_pixbuf = GdkPixbuf.Pixbuf.new_from_file(default_icon_file)
			self.set_default_icon(icon_pixbuf)
		self.accel_group = Gtk.AccelGroup()
		self.add_accel_group(self.accel_group)
		self.menubar = MainMenuBar(self.config, self, application)
		vbox.pack_start(self.menubar.menubar, False, False, 0)

		# create notebook and tabs
		self.notebook = Gtk.Notebook()
		"""The primary :py:class:`Gtk.Notebook` that holds the top level taps of the client GUI."""
		self.notebook.connect('switch-page', self.signal_notebook_switch_page)
		self.notebook.set_scrollable(True)
		vbox.pack_start(self.notebook, True, True, 0)

		self.tabs = {}
		current_page = self.notebook.get_current_page()
		self.last_page_id = current_page

		mailer_tab = MailSenderTab(self.config, self, self.application)
		self.tabs['mailer'] = mailer_tab
		self.notebook.insert_page(mailer_tab.box, mailer_tab.label, current_page + 1)
		self.notebook.set_current_page(current_page + 1)

		campaign_tab = CampaignViewTab(self.config, self, self.application)
		campaign_tab.box.show()
		self.tabs['campaign'] = campaign_tab
		self.notebook.insert_page(campaign_tab.box, campaign_tab.label, current_page + 2)

		self.set_size_request(800, 600)
		self.connect('delete-event', self.signal_delete_event)
		self.notebook.show()
		self.show()
		self.rpc = None # needs to be initialized last
		"""The :py:class:`.KingPhisherRPCClient` instance."""

		login_dialog = dialogs.LoginDialog(self.config, self)
		login_dialog.dialog.connect('response', self.signal_login_dialog_response, login_dialog)
		login_dialog.dialog.show()

	def signal_notebook_switch_page(self, notebook, current_page, index):
		#previous_page = notebook.get_nth_page(self.last_page_id)
		self.last_page_id = index
		mailer_tab = self.tabs.get('mailer')
		campaign_tab = self.tabs.get('campaign')

		notebook = None
		if mailer_tab and current_page == mailer_tab.box:
			notebook = mailer_tab.notebook
		elif campaign_tab and current_page == campaign_tab.box:
			notebook = campaign_tab.notebook

		if notebook:
			index = notebook.get_current_page()
			notebook.emit('switch-page', notebook.get_nth_page(index), index)

	def signal_delete_event(self, x, y):
		self.emit('exit-confirm')
		return True

	def do_exit(self):
		self.hide()
		gui_utilities.gtk_widget_destroy_children(self)
		gui_utilities.gtk_sync()
		self.application.server_disconnect()
		self.destroy()
		return

	def do_exit_confirm(self):
		self.emit('exit')

	def client_quit(self):
		"""
		Unconditionally quit the client and perform any necessary clean up
		operations. The exit-confirm signal will not be sent so there will not
		be any opportunities for the client to cancel the operation.
		"""
		self.emit('exit')

	def signal_login_dialog_response(self, dialog, response, glade_dialog):
		if response == Gtk.ResponseType.CANCEL or response == Gtk.ResponseType.DELETE_EVENT:
			dialog.destroy()
			self.emit('exit')
			return True
		glade_dialog.objects_save_to_config()
		self.application.server_connect()
		self.rpc = self.application.rpc
		dialog.destroy()

	def rename_campaign(self):
		campaign = self.rpc.remote_table_row('campaigns', self.config['campaign_id'])
		prompt = dialogs.TextEntryDialog.build_prompt(self.config, self, 'Rename Campaign', 'Enter the new campaign name:', campaign.name)
		response = prompt.interact()
		if response == None or response == campaign.name:
			return
		self.rpc('campaigns/set', self.config['campaign_id'], ('name',), (response,))
		gui_utilities.show_dialog_info('Campaign Name Updated', self, 'The campaign name was successfully changed')

	def delete_campaign(self):
		"""
		Delete the campaign on the server. A confirmation dialog will be
		displayed before the operation is performed. If the campaign is
		deleted and a new campaign is not selected with
		:py:meth:`.show_campaign_selection`, the client will quit.
		"""
		if not gui_utilities.show_dialog_yes_no('Delete This Campaign?', self, 'This action is irreversible, all campaign data will be lost.'):
			return
		self.rpc('campaign/delete', self.config['campaign_id'])
		if not self.application.show_campaign_selection():
			gui_utilities.show_dialog_error('Now Exiting', self, 'A campaign must be selected.')
			self.client_quit()

	def edit_preferences(self):
		"""
		Display a
		:py:class:`.dialogs.configuration.ConfigurationDialog`
		instance and saves the configuration to disk if cancel is not selected.
		"""
		dialog = dialogs.ConfigurationDialog(self.config, self)
		if dialog.interact() != Gtk.ResponseType.CANCEL:
			app = self.get_property('application')
			app.save_config()

	def export_campaign_xml(self):
		"""Export the current campaign to an XML data file."""
		dialog = gui_utilities.FileChooser('Export Campaign XML Data', self)
		file_name = self.config['campaign_name'] + '.xml'
		response = dialog.run_quick_save(file_name)
		dialog.destroy()
		if not response:
			return
		destination_file = response['target_path']
		export.campaign_to_xml(self.rpc, self.config['campaign_id'], destination_file)

	def start_sftp_client(self):
		"""
		Start the client's preferred sftp client application.
		"""
		if not self.config['sftp_client']:
			gui_utilities.show_dialog_error('Invalid SFTP Configuration', self, 'An SFTP client is not configured')
			return False
		command = str(self.config['sftp_client'])
		sftp_bin = shlex.split(command)[0]
		if not utilities.which(sftp_bin):
			self.logger.error('could not locate the sftp binary: ' + sftp_bin)
			gui_utilities.show_dialog_error('Invalid SFTP Configuration', self, "Could not find the SFTP binary '{0}'".format(sftp_bin))
			return False
		try:
			command = command.format(
				server=self.config['server'],
				username=self.config['server_username'],
				web_root=self.config['server_config']['server.web_root']
			)
		except KeyError as error:
			self.logger.error("key error while parsing the sftp command for token: {0}".format(error.args[0]))
			gui_utilities.show_dialog_error('Invalid SFTP Configuration', self, "Invalid token '{0}' in the SFTP command.".format(error.args[0]))
			return False
		self.logger.debug("starting sftp client command: {0}".format(command))
		utilities.start_process(command, wait=False)
		return

	def stop_remote_service(self):
		"""
		Stop the remote King Phisher server. This will request that the
		server stop processing new requests and exit. This will display
		a confirmation dialog before performing the operation. If the
		remote service is stopped, the client will quit.
		"""
		if not gui_utilities.show_dialog_yes_no('Stop The Remote King Phisher Service?', self, 'This will stop the remote King Phisher service and\nnew incoming requests will not be processed.'):
			return
		self.rpc('shutdown')
		self.logger.info('the remote king phisher service has been stopped')
		gui_utilities.show_dialog_error('Now Exiting', self, 'The remote service has been stopped.')
		self.client_quit()
		return
