import collections
import os
import urlparse

from king_phisher.client.login import KingPhisherClientSSHLoginDialog
from king_phisher.client.mailer import format_message, MailSenderThread
from king_phisher.utilities import gtk_sync, show_dialog_error, show_dialog_warning, show_dialog_yes_no, which_glade, UtilityFileChooser, UtilityGladeGObject

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import WebKit

class MailSenderSendMessagesTab(UtilityGladeGObject):
	gobject_ids = [
		'button_mail_sender_start',
		'button_mail_sender_stop',
		'textview_mail_sender_progress',
		'togglebutton_mail_sender_pause',
		'progressbar_mail_sender',
		'scrolledwindow_mail_sender_progress'
	]
	top_gobject = 'box'
	def __init__(self, *args, **kwargs):
		self.label = Gtk.Label('Send Messages')
		super(MailSenderSendMessagesTab, self).__init__(*args, **kwargs)
		self.textview = self.gobjects['textview_mail_sender_progress']
		self.textbuffer = self.textview.get_buffer()
		self.textbuffer_iter = self.textbuffer.get_start_iter()
		self.progressbar = self.gobjects['progressbar_mail_sender']
		self.sender_thread = None

	def signal_button_clicked_sender_start(self, button):
		required_settings = [
			'mailer.webserver_url',
			'mailer.company_name',
			'mailer.source_email',
			'mailer.subject',
			'mailer.html_file',
			'mailer.target_file'
		]
		for setting in required_settings:
			if not self.config.get(setting):
				show_dialog_warning('Missing Required Option', self.parent, 'Return to the Config tab and set all required options')
				return
		if not self.config.get('smtp_server'):
			show_dialog_warning('Missing SMTP Server Setting', self.parent, 'Please configure the SMTP server')
			return
		if self.sender_thread:
			return
		self.gobjects['button_mail_sender_start'].set_sensitive(False)
		self.gobjects['button_mail_sender_stop'].set_sensitive(True)
		self.progressbar.set_fraction(0)
		self.sender_thread = MailSenderThread(self.config, self.config['mailer.target_file'], self.text_insert, lambda p: self.progressbar.set_fraction(p), self.sender_cleanup)

		# Connect to the SMTP server
		if self.config['smtp_ssh_enable']:
			while True:
				self.text_insert('Connecting To SSH... ')
				login_dialog = KingPhisherClientSSHLoginDialog(self.config, self.parent)
				login_dialog.objects_load_from_config()
				response = login_dialog.interact()
				if response == Gtk.ResponseType.CANCEL:
					self.sender_start_failure(text = 'Canceled.\n')
					return
				if self.sender_thread.server_ssh_connect():
					self.text_insert('Done.\n')
					break
				self.sender_start_failure('Failed to connect to SSH', 'Failed.\n')
		self.text_insert('Connecting To SMTP Server... ')
		if not self.sender_thread.server_smtp_connect():
			self.sender_start_failure('Failed to connect to SMTP', 'Failed.\n')
			return
		self.text_insert('Done.\n')
		self.sender_thread.start()
		self.gobjects['togglebutton_mail_sender_pause'].set_sensitive(True)

	def signal_button_clicked_sender_stop(self, button):
		if not self.sender_thread:
			return
		if not show_dialog_yes_no('Are you sure you want to stop?', self.parent):
			return
		self.sender_thread.stop()
		self.gobjects['button_mail_sender_stop'].set_sensitive(False)
		self.gobjects['button_mail_sender_start'].set_sensitive(True)
		self.gobjects['togglebutton_mail_sender_pause'].set_property('active', False)
		self.gobjects['togglebutton_mail_sender_pause'].set_sensitive(False)

	def signal_button_toggled_sender_pause(self, button):
		if not self.sender_thread:
			return
		if button.get_property('active'):
			self.sender_thread.pause()
		else:
			self.sender_thread.unpause()

	def signal_textview_size_allocate_autoscroll(self, textview, allocation):
		scrolled_window = self.gobjects['scrolledwindow_mail_sender_progress']
		adjustment = scrolled_window.get_vadjustment()
		adjustment.set_value(adjustment.get_upper() - adjustment.get_page_size())

	def text_insert(self, message):
		self.textbuffer.insert(self.textbuffer_iter, message)
		gtk_sync()

	def sender_start_failure(self, message = None, text = None):
		if text:
			self.text_insert(text)
		self.gobjects['button_mail_sender_stop'].set_sensitive(False)
		self.gobjects['button_mail_sender_start'].set_sensitive(True)
		if message:
			show_dialog_error(message, self.parent)

	def sender_cleanup(self):
		self.progressbar.set_fraction(1)
		self.sender_thread = None
		self.gobjects['button_mail_sender_stop'].set_sensitive(False)
		self.gobjects['togglebutton_mail_sender_pause'].set_property('active', False)
		self.gobjects['togglebutton_mail_sender_pause'].set_sensitive(False)
		self.gobjects['button_mail_sender_start'].set_sensitive(True)

class MailSenderPreviewTab(object):
	def __init__(self, config, parent):
		self.label = Gtk.Label('Preview')
		self.config = config
		self.parent = parent

		self.box = Gtk.VBox()
		self.box.show()
		self.webview = WebKit.WebView()
		self.webview.show()
		self.box.pack_start(self.webview, True, True, 0)

class MailSenderEditTab(UtilityGladeGObject):
	gobject_ids = [
			'button_save_html_file',
			'textview_html_file'
	]
	top_gobject = 'box'
	def __init__(self, *args, **kwargs):
		self.label = Gtk.Label('Edit')
		super(MailSenderEditTab, self).__init__(*args, **kwargs)
		self.textview = self.gobjects['textview_html_file']
		self.textbuffer = self.textview.get_buffer()
		self.button_save_html_file = self.gobjects['button_save_html_file']

	def signal_button_save(self, button):
		html_file = self.config.get('mailer.html_file')
		if not html_file:
			return
		text = self.textbuffer.get_text(self.textbuffer.get_start_iter(), self.textbuffer.get_end_iter(), False)
		if not show_dialog_yes_no("Save HTML File?", self.parent):
			return
		html_file_h = open(html_file, 'w')
		html_file_h.write(text)
		html_file_h.close()

class MailSenderConfigTab(UtilityGladeGObject):
	gobject_ids = [
			'entry_webserver_url',
			'entry_company_name',
			'entry_source_email',
			'entry_source_email_alias',
			'entry_subject',
			'entry_reply_to_email',
			'entry_html_file',
			'entry_target_file'
	]
	config_prefix = 'mailer.'
	top_gobject = 'box'
	def __init__(self, *args, **kwargs):
		self.label = Gtk.Label('Config')
		super(MailSenderConfigTab, self).__init__(*args, **kwargs)

	def signal_entry_activate_open_file(self, entry):
		dialog = UtilityFileChooser('Choose File')
		if entry == self.gobjects.get('entry_html_file'):
			dialog.quick_add_filter('HTML Files', '*.html')
		elif entry == self.gobjects.get('entry_target_file'):
			dialog.quick_add_filter('CSV Files', '*.csv')
		dialog.quick_add_filter('All Files', '*')
		response = dialog.run_quick_open()
		dialog.destroy()
		if not response:
			return False
		entry.set_text(response['target_filename'])
		return True

class MailSenderTab(Gtk.VBox):
	def __init__(self, config, parent, *args, **kwargs):
		self.config = config
		self.parent = parent
		super(MailSenderTab, self).__init__(*args, **kwargs)
		self.label = Gtk.Label('Send Messages')

		self.notebook = Gtk.Notebook()
		self.notebook.connect('switch-page', self._tab_changed)
		self.notebook.set_scrollable(True)
		self.pack_start(self.notebook, True, True, 0)

		self.tabs = {}
		current_page = self.notebook.get_current_page()
		self.last_page_id = current_page

		config_tab = MailSenderConfigTab(self.config, self.parent)
		self.tabs['config'] = config_tab
		self.notebook.append_page(config_tab.box, config_tab.label)

		edit_tab = MailSenderEditTab(self.config, self.parent)
		self.tabs['edit'] = edit_tab
		self.notebook.append_page(edit_tab.box, edit_tab.label)

		preview_tab = MailSenderPreviewTab(self.config, self.parent)
		self.tabs['preview'] = preview_tab
		self.notebook.append_page(preview_tab.box, preview_tab.label)

		send_messages_tab = MailSenderSendMessagesTab(self.config, self.parent)
		self.tabs['send_messages'] = send_messages_tab
		self.notebook.append_page(send_messages_tab.box, send_messages_tab.label)

		for tab in self.tabs.values():
			tab.box.show()
		self.notebook.show()

	def _tab_changed(self, notebook, current_page, index):
		previous_page = notebook.get_nth_page(self.last_page_id)
		self.last_page_id = index
		config_tab = self.tabs.get('config')
		edit_tab = self.tabs.get('edit')
		preview_tab = self.tabs.get('preview')
		progress_tab = self.tabs.get('progress')

		if config_tab and previous_page == config_tab.box:
			config_tab.objects_save_to_config()
		elif edit_tab and previous_page == edit_tab.box:
			for i in xrange(1):
				html_file = self.config.get('mailer.html_file')
				if not html_file:
					break
				text = edit_tab.textbuffer.get_text(edit_tab.textbuffer.get_start_iter(), edit_tab.textbuffer.get_end_iter(), False)
				if not text:
					break
				old_text = open(html_file, 'r').read()
				if old_text == text:
					break
				if not show_dialog_yes_no("Save HTML File?", self.parent):
					break
				html_file_h = open(html_file, 'w')
				html_file_h.write(text)
				html_file_h.close()

		if edit_tab and current_page == edit_tab.box:
			html_file = self.config.get('mailer.html_file')
			if not html_file:
				edit_tab.button_save_html_file.set_sensitive(False)
				edit_tab.textview.set_property('editable', False)
				return
			edit_tab.button_save_html_file.set_sensitive(True)
			edit_tab.textview.set_property('editable', True)
			edit_tab.textbuffer.set_text(open(html_file, 'r').read())
		elif preview_tab and current_page == preview_tab.box:
			html_file = self.config.get('mailer.html_file')
			if not html_file:
				return
			html_file_uri = urlparse.urlparse(html_file, 'file').geturl()
			html_data = open(html_file, 'r').read()
			html_data = format_message(html_data, self.config)
			preview_tab.webview.load_html_string(html_data, html_file_uri)
