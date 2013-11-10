import csv
import os
import random
import smtplib
import string
import threading
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

from king_phisher.ssh_forward import SSHTCPForwarder
from king_phisher.utilities import server_parse

make_uid = lambda: os.urandom(16).encode('hex')

def format_message(template, config, uid = None):
	uid = (uid or make_uid())
	template = string.Template(template)
	template_vars = {}
	template_vars['uid'] = uid
	template_vars['first_name'] = 'Alice'
	template_vars['last_name'] = 'Liddle'
	template_vars['companyname'] = config.get('mailer.company_name', '')
	template_vars['webserver'] = config.get('mailer.webserver', '')
	return template.substitute(**template_vars)

class MailSenderThread(threading.Thread):
	def __init__(self, config, target_file, notify_status, notify_progress, notify_stopped):
		super(MailSenderThread, self).__init__()
		self.config = config
		self.target_file = target_file
		self.notify_status = notify_status
		self.notify_progress = notify_progress
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
		local_port = random.randint(2000,6000)
		try:
			self.ssh_forwarder = SSHTCPForwarder(server, username, password, local_port, remote_server)
			self.ssh_forwarder.start()
		except:
			return False
		self.smtp_server = (self.smtp_server[0], local_port)
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
			emails_done += 1
			self.notify_progress(float(emails_done) / float(emails_total))
			uid = make_uid()
			self.notify_status("Sending Email {0} of {1} To {2} With UID: {3}\n".format(emails_done, emails_total, target['email_address'], uid))
			msg = self.create_email(target['first_name'], target['last_name'], target['email_address'], uid)
			self.send_email(target['email_address'], msg)
		target_file_h.close()
		self.notify_status("Finished Sending Emails, Successfully Sent {0} Emails\n".format(emails_done))
		if self.ssh_forwarder:
			self.ssh_forwarder.stop()
			self.ssh_forwarder = None
			self.notify_status('Disconnected From SSH Server\n')
		if self.smtp_connection:
			self.smtp_connection.quit()
			self.smtp_connection = None
			self.notify_status('Disconnected From SMTP Server\n')
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
		msg_body = MIMEText(format_message(msg_template, self.config), "html")
		msg_alt.attach(msg_body)
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
