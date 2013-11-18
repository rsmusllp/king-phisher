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
#  * Neither the name of the  nor the names of its
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
import urlparse
from email import Encoders
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

from king_phisher.ssh_forward import SSHTCPForwarder
from king_phisher.client.utilities import server_parse

make_uid = lambda: ''.join(random.choice(string.ascii_letters + string.digits) for x in range(16))

def format_message(template, config, first_name= None, last_name = None, uid = None):
	first_name = (first_name or 'Alice')
	last_name = (last_name or 'Liddle')
	uid = (uid or make_uid())
	template = string.Template(template)
	template_vars = {}
	template_vars['uid'] = uid
	template_vars['first_name'] = first_name
	template_vars['last_name'] = last_name
	template_vars['companyname'] = config.get('mailer.company_name', '')
	template_vars['rickroll_url'] = 'http://www.youtube.com/watch?v=oHg5SJYRHA0'
	webserver_url = config.get('mailer.webserver_url', '')
	webserver_url = urlparse.urlparse(webserver_url)
	webserver_url = urlparse.urlunparse((webserver_url.scheme, webserver_url.netloc, webserver_url.path, '', '', ''))
	template_vars['webserver_url'] = webserver_url
	return template.substitute(**template_vars)

class MailSenderThread(threading.Thread):
	def __init__(self, config, target_file, notify_status, notify_sent, notify_stopped):
		super(MailSenderThread, self).__init__()
		self.logger = logging.getLogger(self.__class__.__name__)
		self.config = config
		self.target_file = target_file
		self.notify_status = notify_status
		self.notify_sent = notify_sent
		self.notify_stopped = notify_stopped
		self.ssh_forwarder = None
		self.smtp_connection = None
		self.smtp_server = server_parse(self.config['smtp_server'], 25)
		self.running = threading.Event()
		self.paused = threading.Event()
		self.should_exit = threading.Event()

	def server_ssh_connect(self):
		server = server_parse(self.config['ssh_server'], 22)
		username = self.config['ssh_username']
		password = self.config['ssh_password']
		remote_server = server_parse(self.config['smtp_server'], 25)
		local_port = random.randint(2000, 6000)
		try:
			self.ssh_forwarder = SSHTCPForwarder(server, username, password, local_port, remote_server)
			self.ssh_forwarder.start()
		except:
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
		self.running.set()
		self.should_exit.clear()
		self.paused.clear()

		target_file_h = open(self.target_file, 'r')
		csv_reader = csv.DictReader(target_file_h, ['first_name', 'last_name', 'email_address'])
		for target in csv_reader:
			if self.should_exit.is_set():
				self.notify_status('Sending Emails Cancelled\n')
				break
			if self.paused.is_set():
				self.notify_status('Paused Sending Emails, Waiting To Resume\n')
				self.running.wait()
				self.paused.clear()
				if self.should_exit.is_set():
					self.notify_status('Sending Emails Cancelled\n')
					break
				self.notify_status('Resuming Sending Emails\n')
			uid = make_uid()
			emails_done += 1
			self.notify_status("Sending Email {0} of {1} To {2} With UID: {3}\n".format(emails_done, emails_total, target['email_address'], uid))
			msg = self.create_email(target['first_name'], target['last_name'], target['email_address'], uid)
			self.send_email(target['email_address'], msg)
			self.notify_sent(uid, target['email_address'], emails_done, emails_total)
		target_file_h.close()
		self.notify_status("Finished Sending Emails, Successfully Sent {0} Emails\n".format(emails_done))
		if self.smtp_connection:
			self.smtp_connection.quit()
			self.smtp_connection = None
			self.notify_status('Disconnected From SMTP Server\n')
		if self.ssh_forwarder:
			self.ssh_forwarder.stop()
			self.ssh_forwarder = None
			self.notify_status('Disconnected From SSH Server\n')
		self.notify_stopped()
		return

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
		msg.preamble = 'This is a multi-part message in MIME format.'
		msg_alt = MIMEMultipart('alternative')
		msg.attach(msg_alt)
		msg_template = open(self.config['mailer.html_file'], 'r').read()
		formatted_msg = format_message(msg_template, self.config, first_name = first_name, last_name = last_name, uid = uid)
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
