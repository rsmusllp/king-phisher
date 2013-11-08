import collections
import os
import string
import urlparse

from king_phisher.utilities import which_glade, UtilityFileChooser, UtilityGladeGObject

from gi.repository import Gtk
from gi.repository import WebKit

def format_message(template, config):
	template = string.Template(template)
	template_vars = {}
	template_vars['first_name'] = 'Alice'
	template_vars['last_name'] = 'Liddle'
	template_vars['companyname'] = config.get('mailer.company_name', '')
	template_vars['webserver'] = config.get('mailer.webserver', '')
	return template.substitute(**template_vars)

class MailSenderPreviewTab(object):
	def __init__(self, config, parent):
		self.label = Gtk.Label('Preview')
		self.config = config
		self.parent = parent

		self.box = Gtk.VBox()
		self.webview = WebKit.WebView()
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
		if not show_dialog_yes_no(self.parent, "Save HTML File?"):
			return
		html_file_h = open(html_file, 'w')
		html_file_h.write(text)
		html_file_h.close()

class MailSenderConfigTab(UtilityGladeGObject):
	gobject_ids = [
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

		for tab in self.tabs.values():
			tab.box.show_all()
		self.notebook.show()

	def _tab_changed(self, notebook, current_page, index):
		previous_page = notebook.get_nth_page(self.last_page_id)
		self.last_page_id = index
		config_tab = self.tabs.get('config')
		edit_tab = self.tabs.get('edit')
		preview_tab = self.tabs.get('preview')

		if edit_tab and previous_page == edit_tab.box:
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
			config_tab.objects_save_to_config()
			html_file_uri = urlparse.urlparse(html_file, 'file').geturl()
			html_data = open(html_file, 'r').read()
			html_data = format_message(html_data, self.config)
			preview_tab.webview.load_html_string(html_data, html_file_uri)
		elif self.tabs.get('edit') and current_page == self.tabs.get('edit').box:
			edit_tab = self.tabs['edit']

