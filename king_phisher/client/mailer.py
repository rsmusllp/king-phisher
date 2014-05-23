#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/mailer.py
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

import csv
import logging
import mimetypes
import os
import random
import smtplib
import string
import threading
import time
import urlparse
from email import Encoders
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

from king_phisher import templates
from king_phisher import utilities
from king_phisher.client import gui_utilities
from king_phisher.ssh_forward import SSHTCPForwarder

from gi.repository import GLib

make_uid = lambda: ''.join(random.choice(string.ascii_letters + string.digits) for x in range(16))

template_environment = templates.KingPhisherTemplateEnvironment()

def format_message(template, config, first_name=None, last_name=None, uid=None, target_email=None):
	first_name = ('Alice' if not isinstance(first_name, (str, unicode)) else first_name)
	last_name = ('Liddle' if not isinstance(last_name, (str, unicode)) else last_name)
	target_email = ('aliddle@wonderland.com' if not isinstance(target_email, (str, unicode)) else target_email)
	uid = (uid or config['server_config'].get('server.secret_id') or make_uid())

	template = template_environment.from_string(template)
	template_vars = {}
	template_vars['uid'] = uid
	template_vars['first_name'] = first_name
	template_vars['last_name'] = last_name
	template_vars['email_address'] = target_email
	template_vars['company_name'] = config.get('mailer.company_name', '')

	webserver_url = config.get('mailer.webserver_url', '')
	webserver_url = urlparse.urlparse(webserver_url)
	tracking_image = config['server_config']['server.tracking_image']
	template_vars['webserver'] = webserver_url.netloc
	tracking_url = urlparse.urlunparse((webserver_url.scheme, webserver_url.netloc, tracking_image, '', 'id=' + uid, ''))
	webserver_url = urlparse.urlunparse((webserver_url.scheme, webserver_url.netloc, webserver_url.path, '', '', ''))
	template_vars['tracking_dot_image_tag'] = "<img src=\"{0}\" style=\"display:none\" />".format(tracking_url)

	template_vars_url = {}
	template_vars_url['rickroll'] = 'http://www.youtube.com/watch?v=oHg5SJYRHA0'
	template_vars_url['webserver'] = webserver_url + '?id=' + uid
	template_vars_url['webserver_raw'] = webserver_url
	template_vars_url['tracking_dot'] = tracking_url
	template_vars['url'] = template_vars_url
	template_vars.update(template_environment.standard_variables)
	return template.render(template_vars)

class MailSenderThread(threading.Thread):
	def __init__(self, config, target_file, tab, rpc):
		super(MailSenderThread, self).__init__()
		self.logger = logging.getLogger('KingPhisher.Client.' + self.__class__.__name__)
		self.config = config
		self.target_file = target_file
		self.tab = tab
		self.rpc = rpc
		self.ssh_forwarder = None
		self.smtp_connection = None
		self.smtp_server = utilities.server_parse(self.config['smtp_server'], 25)
		self.running = threading.Event()
		self.paused = threading.Event()
		self.should_exit = threading.Event()
		self.max_messages_per_minute = float(self.config.get('smtp_max_send_rate', 0.0))

	def server_ssh_connect(self):
		server = utilities.server_parse(self.config['ssh_server'], 22)
		username = self.config['ssh_username']
		password = self.config['ssh_password']
		remote_server = utilities.server_parse(self.config['smtp_server'], 25)
		local_port = random.randint(2000, 6000)
		try:
			self.ssh_forwarder = SSHTCPForwarder(server, username, password, local_port, remote_server, preferred_private_key=self.config.get('ssh_preferred_key'))
			self.ssh_forwarder.start()
			time.sleep(0.5)
		except:
			self.logger.warning('failed to connect to remote ssh server')
			return False
		self.smtp_server = ('localhost', local_port)
		return True

	def server_smtp_connect(self):
		if self.config.get('smtp_ssl_enable', False):
			SMTP_CLASS = smtplib.SMTP_SSL
		else:
			SMTP_CLASS = smtplib.SMTP
		try:
			self.smtp_connection = SMTP_CLASS(*self.smtp_server)
		except:
			return False
		return True

	def server_smtp_disconnect(self):
		if self.smtp_connection:
			try:
				self.smtp_connection.quit()
			except smtplib.SMTPServerDisconnected:
				pass
			self.smtp_connection = None
			GLib.idle_add(self.tab.notify_status, 'Disconnected From SMTP Server\n')

	def server_smtp_reconnect(self):
		if self.smtp_connection:
			try:
				self.smtp_connection.quit()
			except smtplib.SMTPServerDisconnected:
				pass
			self.smtp_connection = None
		while not self.server_smtp_connect():
			GLib.idle_add(self.tab.notify_status, 'Failed To Reconnect To The SMTP Server\n')
			if not self.process_pause(True):
				return False
		return True

	def count_emails(self, target_file):
		targets = 0
		target_file_h = open(target_file, 'r')
		csv_reader = csv.DictReader(target_file_h, ['first_name', 'last_name', 'email_address'])
		for target in csv_reader:
			targets += 1
		target_file_h.close()
		return targets

	def run(self):
		emails_done = 0
		emails_total = self.count_emails(self.target_file)
		max_messages_per_connection = self.config.get('mailer.max_messages_per_connection', 5)
		self.running.set()
		self.should_exit.clear()
		self.paused.clear()

		target_file_h = open(self.target_file, 'r')
		csv_reader = csv.DictReader(target_file_h, ['first_name', 'last_name', 'email_address'])
		for target in csv_reader:
			iteration_time = time.time()
			if emails_done > 0 and (emails_done % max_messages_per_connection):
				self.server_smtp_reconnect()
			if self.should_exit.is_set():
				GLib.idle_add(self.tab.notify_status, 'Sending Emails Cancelled\n')
				break
			if not self.process_pause():
				break
			uid = make_uid()
			emails_done += 1
			GLib.idle_add(self.tab.notify_status, "Sending Email {0} of {1} To {2} With UID: {3}\n".format(emails_done, emails_total, target['email_address'], uid))
			msg = self.create_email(target['first_name'], target['last_name'], target['email_address'], uid)
			if not self.try_send_email(target['email_address'], msg):
				break
			GLib.idle_add(lambda x: self.tab.notify_sent(*x), (emails_done, emails_total))
			campaign_id = self.config['campaign_id']
			company_name = self.config.get('mailer.company_name', '')
			self.rpc('campaign/message/new', campaign_id, uid, target['email_address'], company_name, target['first_name'], target['last_name'])
			if self.max_messages_per_minute:
				iteration_time = (time.time() - iteration_time)
				sleep_time = (60.0 / float(self.max_messages_per_minute)) - iteration_time
				if sleep_time > 0:
					time.sleep(sleep_time)
		target_file_h.close()
		GLib.idle_add(self.tab.notify_status, "Finished Sending Emails, Successfully Sent {0} Emails\n".format(emails_done))
		self.server_smtp_disconnect()
		if self.ssh_forwarder:
			self.ssh_forwarder.stop()
			self.ssh_forwarder = None
			GLib.idle_add(self.tab.notify_status, 'Disconnected From SSH Server\n')
		GLib.idle_add(self.tab.notify_stopped)
		return

	def process_pause(self, set_pause=False):
		if set_pause:
			gui_utilities.glib_idle_add_wait(lambda: self.tab.pause_button.set_property('active', True))
		if self.paused.is_set():
			GLib.idle_add(self.tab.notify_status, 'Paused Sending Emails, Waiting To Resume\n')
			self.running.wait()
			self.paused.clear()
			if self.should_exit.is_set():
				GLib.idle_add(self.tab.notify_status, 'Sending Emails Cancelled\n')
				return False
			GLib.idle_add(self.tab.notify_status, 'Resuming Sending Emails\n')
			self.max_messages_per_minute = float(self.config.get('smtp_max_send_rate', 0.0))
		return True

	def create_email(self, first_name, last_name, target_email, uid):
		msg = MIMEMultipart()
		msg['Subject'] = self.config['mailer.subject']
		if self.config.get('mailer.reply_to_email'):
			msg.add_header('reply-to', self.config['mailer.reply_to_email'])
		if self.config.get('mailer.source_email_alias'):
			msg['From'] = "\"{0}\" <{1}>".format(self.config['mailer.source_email_alias'], self.config['mailer.source_email'])
		else:
			msg['From'] = self.config['mailer.source_email']
		msg['To'] = target_email
		importance = self.config.get('mailer.importance', 'Normal')
		if importance != 'Normal':
			msg['Importance'] = importance
		sensitivity = self.config.get('mailer.sensitivity', 'Normal')
		if sensitivity != 'Normal':
			msg['Sensitivity'] = sensitivity
		msg.preamble = 'This is a multi-part message in MIME format.'
		msg_alt = MIMEMultipart('alternative')
		msg.attach(msg_alt)
		msg_template = open(self.config['mailer.html_file'], 'r').read()
		formatted_msg = format_message(msg_template, self.config, first_name=first_name, last_name=last_name, uid=uid, target_email=target_email)
		msg_body = MIMEText(formatted_msg, "html")
		msg_alt.attach(msg_body)
		if self.config.get('mailer.attachment_file'):
			attachment = self.config['mailer.attachment_file']
			attachfile = MIMEBase(*mimetypes.guess_type(attachment))
			attachfile.set_payload(open(attachment, 'rb').read())
			Encoders.encode_base64(attachfile)
			attachfile.add_header('Content-Disposition', "attachment; filename=\"{0}\"".format(os.path.basename(attachment)))
			msg.attach(attachfile)
		return msg

	def try_send_email(self, *args, **kwargs):
		message_sent = False
		while not message_sent:
			for i in xrange(0, 3):
				try:
					self.send_email(*args, **kwargs)
					message_sent = True
					break
				except:
					GLib.idle_add(self.tab.notify_status, 'Failed To Send Message\n')
					time.sleep(1)
			if not message_sent:
				self.server_smtp_disconnect()
				if not self.process_pause(True):
					return False
				self.server_smtp_reconnect()
		return True

	def send_email(self, target_email, msg):
		source_email = self.config['mailer.source_email']
		self.smtp_connection.sendmail(source_email, target_email, msg.as_string())

	def pause(self):
		self.running.clear()
		self.paused.set()

	def unpause(self):
		self.running.set()

	def stop(self):
		self.should_exit.set()
		self.unpause()
		if self.is_alive():
			self.join()
