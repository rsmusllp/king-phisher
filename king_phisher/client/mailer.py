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

# disable this warning for the email.mime.* modules that have to be imported
# pylint: disable=unused-import

import codecs
import collections
import csv
import datetime
import email.encoders as encoders
import email.mime as mime
import email.mime.base
import email.mime.image
import email.mime.multipart
import email.mime.text
import email.utils
import logging
import mimetypes
import os
import smtplib
import socket
import threading
import time
import urllib.parse

from king_phisher import errors
from king_phisher import ics
from king_phisher import ipaddress
from king_phisher import its
from king_phisher import templates
from king_phisher import utilities
from king_phisher.client import gui_utilities
from king_phisher.client.dialogs import ssh_host_key
from king_phisher.constants import ConnectionErrorReason
from king_phisher.ssh_forward import SSHTCPForwarder

from gi.repository import GLib
import paramiko
import smoke_zephyr.utilities

__all__ = (
	'guess_smtp_server_address',
	'MailSenderThread',
	'render_message_template'
)

template_environment = templates.MessageTemplateEnvironment()

MessageAttachments = collections.namedtuple('MessageAttachments', ('files', 'images'))
"""
A named tuple for holding both image and file attachments for a message.

.. py:attribute:: files

	A tuple of :py:class:`~.mime.MIMEBase` instances representing the messsages
	attachments.

.. py:attribute:: images

	A tuple of :py:class:`~.mime.MIMEImage` instances representing the images in
	the message.
"""

MIME_TEXT_PLAIN = 'This message requires an HTML aware email agent to be properly viewed.\r\n\r\n'
"""The static string to place in MIME message as a text/plain part. This is shown by email clients that do not support HTML."""

def _iterate_targets_file(target_file, config=None):
	target_file_h = open(target_file, 'rU')
	csv_reader = csv.DictReader(target_file_h, ('first_name', 'last_name', 'email_address', 'department'))
	uid_charset = None if config is None else config['mailer.message_uid.charset']
	for line_no, raw_target in enumerate(csv_reader, 1):
		if None in raw_target:
			# remove the additional fields
			del raw_target[None]
		if its.py_v2:
			# this will intentionally cause a UnicodeDecodeError to be raised as is the behaviour in python 3.x
			# when csv.DictReader is initialized
			raw_target = dict((k, (v if v is None else v.decode('utf-8'))) for k, v in raw_target.items())
		if uid_charset is not None:
			raw_target['uid'] = utilities.make_message_uid(
				upper=uid_charset['upper'],
				lower=uid_charset['lower'],
				digits=uid_charset['digits']
			)
		target = MessageTarget(line=line_no, **raw_target)
		# the caller needs to catch and process the missing fields appropriately
		yield target
	target_file_h.close()

def count_targets_file(target_file):
	"""
	Count the number of valid targets that the specified file contains. This
	skips lines which are missing fields or where the email address is invalid.

	:param str target_file: The path the the target CSV file on disk.
	:return: The number of valid targets.
	:rtype: int
	"""
	count = 0
	for target in _iterate_targets_file(target_file):
		if target.missing_fields:
			continue
		if not utilities.is_valid_email_address(target.email_address):
			continue
		count += 1
	return count

def get_invite_start_from_config(config):
	"""
	Get the start time for an invite from the configuration. This takes into
	account whether the invite is for all day or starts at a specific time.

	:param dict config: The King Phisher client configuration.
	:return: The timestamp of when the invite is to start.
	:rtype: :py:class:`datetime.datetime`
	"""
	if config['mailer.calendar_invite_all_day']:
		start_time = datetime.datetime.combine(
			config['mailer.calendar_invite_date'],
			datetime.time(0, 0)
		)
	else:
		start_time = datetime.datetime.combine(
			config['mailer.calendar_invite_date'],
			datetime.time(
				int(config['mailer.calendar_invite_start_hour']),
				int(config['mailer.calendar_invite_start_minute'])
			)
		)
	return start_time

@smoke_zephyr.utilities.Cache('3m')
def guess_smtp_server_address(host, forward_host=None):
	"""
	Guess the IP address of the SMTP server that will be connected to given the
	SMTP host information and an optional SSH forwarding host. If a hostname is
	in use it will be resolved to an IP address, either IPv4 or IPv6 and in that
	order. If a hostname resolves to multiple IP addresses, None will be
	returned. This function is intended to guess the SMTP servers IP address
	given the client configuration so it can be used for SPF record checks.

	:param str host: The SMTP server that is being connected to.
	:param str forward_host: An optional host that is being used to tunnel the connection.
	:return: The IP address of the SMTP server.
	:rtype: None, :py:class:`ipaddress.IPv4Address`, :py:class:`ipaddress.IPv6Address`
	"""
	host = host.rsplit(':', 1)[0]
	if ipaddress.is_valid(host):
		ip = ipaddress.ip_address(host)
		if not ip.is_loopback:
			return ip
	else:
		info = None
		for family in (socket.AF_INET, socket.AF_INET6):
			try:
				info = socket.getaddrinfo(host, 1, family)
			except socket.gaierror:
				continue
			info = set(list([r[4][0] for r in info]))
			if len(info) != 1:
				return
			break
		if info:
			ip = ipaddress.ip_address(info.pop())
			if not ip.is_loopback:
				return ip
	if forward_host:
		return guess_smtp_server_address(forward_host)
	return

def render_message_template(template, config, target=None, analyze=False):
	"""
	Take a message from a template and format it to be sent by replacing
	variables and processing other template directives. If the *target*
	parameter is not set, a placeholder will be created and the message will be
	formatted to be previewed.

	:param str template: The message template.
	:param dict config: The King Phisher client configuration.
	:param target: The messages intended target information.
	:type target: :py:class:`.MessageTarget`
	:param bool analyze: Set the template environment to analyze mode.
	:return: The formatted message.
	:rtype: str
	"""
	if target is None:
		target = MessageTargetPlaceholder(uid=config['server_config'].get('server.secret_id'))
		template_environment.set_mode(template_environment.MODE_PREVIEW)

	if analyze:
		template_environment.set_mode(template_environment.MODE_ANALYZE)

	template = template_environment.from_string(template)
	template_vars = {}
	template_vars['campaign'] = dict(
		id=str(config['campaign_id']),
		name=config['campaign_name']
	)
	template_vars['client'] = dict(
		first_name=target.first_name,
		last_name=target.last_name,
		email_address=target.email_address,
		department=target.department,
		company_name=config.get('mailer.company_name'),
		message_id=target.uid
	)

	template_vars['sender'] = dict(
		email=config.get('mailer.source_email'),
		friendly_alias=config.get('mailer.source_email_alias'),
		reply_to=config.get('mailer.reply_to_email')
	)
	template_vars['uid'] = target.uid

	message_type = config.get('mailer.message_type', 'email')
	template_vars['message_type'] = message_type
	if message_type == 'calendar_invite':
		template_vars['calendar_invite'] = dict(
			all_day=config.get('mailer.calendar_invite_all_day'),
			location=config.get('mailer.calendar_invite_location'),
			start=get_invite_start_from_config(config),
			summary=config.get('mailer.calendar_invite_summary')
		)

	template_vars['message'] = dict(
		attachment=config.get('mailer.attachment_file'),
		importance=config.get('mailer.importance'),
		recipient=dict(
			field=config.get('mailer.target_field', 'to'),
			to=(target.email_address if config.get('mailer.target_field') == 'to' else config.get('mailer.recipient_email_to', '')),
			cc=(target.email_address if config.get('mailer.target_field') == 'cc' else config.get('mailer.recipient_email_cc', '')),
			bcc=(target.email_address if config.get('mailer.target_field') == 'bcc' else '')
		),
		sensitivity=config.get('mailer.sensitivity'),
		subject=config.get('mailer.subject'),
		template=config.get('mailer.html_file'),
		type=message_type
	)

	webserver_url = config.get('mailer.webserver_url', '')
	webserver_url = urllib.parse.urlparse(webserver_url)
	tracking_image = config['server_config']['server.tracking_image']
	template_vars['webserver'] = webserver_url.netloc
	tracking_url = urllib.parse.urlunparse((webserver_url.scheme, webserver_url.netloc, tracking_image, '', 'id=' + target.uid, ''))
	webserver_url = urllib.parse.urlunparse((webserver_url.scheme, webserver_url.netloc, webserver_url.path, '', '', ''))
	template_vars['tracking_dot_image_tag'] = "<img src=\"{0}\" style=\"display:none\" />".format(tracking_url)

	template_vars_url = {}
	template_vars_url['rickroll'] = 'http://www.youtube.com/watch?v=oHg5SJYRHA0'
	template_vars_url['webserver'] = webserver_url + '?id=' + target.uid
	template_vars_url['webserver_raw'] = webserver_url
	template_vars_url['tracking_dot'] = tracking_url
	template_vars['url'] = template_vars_url
	template_vars.update(template_environment.standard_variables)
	return template.render(template_vars)

def rfc2282_timestamp(dt=None, utc=False):
	"""
	Convert a :py:class:`datetime.datetime` instance into an :rfc:`2282`
	compliant timestamp suitable for use in MIME-encoded messages.

	:param dt: A time to use for the timestamp otherwise the current time is used.
	:type dt: :py:class:`datetime.datetime`
	:param utc: Whether to return the timestamp as a UTC offset or from the local timezone.
	:return: The timestamp.
	:rtype: str
	"""
	dt = dt or datetime.datetime.utcnow()
	# email.utils.formatdate wants the time to be in the local timezone
	dt = utilities.datetime_utc_to_local(dt)
	return email.utils.formatdate(time.mktime(dt.timetuple()), not utc)

class MessageTarget(object):
	"""
	A simple class for holding information regarding a messages intended
	recipient.
	"""
	required_fields = ('first_name', 'last_name', 'email_address')
	__slots__ = 'department', 'email_address', 'first_name', 'last_name', 'line', 'uid'
	def __init__(self, first_name, last_name, email_address, uid=None, department=None, line=None):
		self.first_name = first_name
		"""The target recipient's first name."""
		self.last_name = last_name
		"""The target recipient's last name."""
		self.email_address = utilities.nonempty_string(email_address)
		"""The target recipient's email address."""
		self.uid = uid
		"""The unique identifier that is going to be used for this target."""
		if self.uid is None:
			self.uid = utilities.make_message_uid()
		self.department = utilities.nonempty_string(department)
		"""The target recipient's department name."""
		self.line = line
		"""The line number in the file from which this target was loaded."""

	def __repr__(self):
		return "<{0} first_name={1!r} last_name={2!r} email_address={3!r} >".format(self.__class__.__name__, self.first_name, self.last_name, self.email_address)

	@property
	def missing_fields(self):
		return tuple(field for field in self.required_fields if getattr(self, field) is None)

class MessageTargetPlaceholder(MessageTarget):
	"""
	A default :py:class:`~.MessageTarget` for use as a placeholder value while
	rendering, performing tests, etc.
	"""
	def __init__(self, uid=None):
		super(MessageTargetPlaceholder, self).__init__('Alice', 'Liddle', 'aliddle@wonderland.com', uid=uid, department='Visitors')

class TopMIMEMultipart(mime.multipart.MIMEMultipart):
	"""
	A :py:class:`.mime.multipart.MIMEMultipart` subclass for representing the
	top / outer most part of a MIME multipart message. This adds additional
	default headers to the message.
	"""
	def __init__(self, mime_type, config, target):
		"""
		:param str mime_type: The type of this part such as related or alternative.
		:param dict config: The King Phisher client configuration.
		:param target: The target information for the messages intended recipient.
		:type target: :py:class:`.MessageTarget`
		"""
		mime.multipart.MIMEMultipart.__init__(self, mime_type, charset='utf-8')
		self['Subject'] = render_message_template(config['mailer.subject'], config, target)
		if config.get('mailer.reply_to_email'):
			self.add_header('reply-to', config['mailer.reply_to_email'])
		if config.get('mailer.source_email_alias'):
			self['From'] = "\"{0}\" <{1}>".format(config['mailer.source_email_alias'], config['mailer.source_email'])
		else:
			self['From'] = config['mailer.source_email']
		self['Date'] = rfc2282_timestamp()
		self.preamble = 'This is a multi-part message in MIME format.'

class MIMEText(mime.text.MIMEText):
	def __init__(self, text, subtype, charset='utf-8'):
		super(MIMEText, self).__init__(text, subtype, charset)

	@property
	def payload_string(self):
		return self.get_payload_string()

	@payload_string.setter
	def payload_string(self, text):
		self.set_payload_string(text)

	def get_payload_string(self):
		payload = self.get_payload(decode=True)
		if payload:
			charset = self.get_charset()
			payload = payload.decode(charset.input_charset)
		return payload

	def set_payload_string(self, payload, charset=None):
		if 'Content-Transfer-Encoding' in self:
			del self['Content-Transfer-Encoding']
		return self.set_payload(payload, charset=charset or self.get_charset())

class MailSenderThread(threading.Thread):
	"""
	The King Phisher threaded email message sender. This object manages
	the sending of emails for campaigns and supports pausing the sending of
	messages which can later be resumed by unpausing. This object reports
	its information to the GUI through an optional
	:py:class:`.MailSenderSendTab` instance, these two objects
	are very interdependent.
	"""
	def __init__(self, application, target_file, rpc, tab=None):
		"""
		:param application: The GTK application that the thread is associated with.
		:type application: :py:class:`.KingPhisherClientApplication`
		:param str target_file: The CSV formatted file to read message targets from.
		:param tab: The GUI tab to report information to.
		:type tab: :py:class:`.MailSenderSendTab`
		:param rpc: The client's connected RPC instance.
		:type rpc: :py:class:`.KingPhisherRPCClient`
		"""
		super(MailSenderThread, self).__init__()
		self.daemon = True
		self.logger = logging.getLogger('KingPhisher.Client.' + self.__class__.__name__)
		self.application = application
		self.config = self.application.config
		self.target_file = target_file
		"""The name of the target file in CSV format."""
		self.tab = tab
		"""The optional :py:class:`.MailSenderSendTab` instance for reporting status messages to the GUI."""
		self.rpc = rpc
		self._ssh_forwarder = None
		self.smtp_connection = None
		"""The :py:class:`smtplib.SMTP` connection instance."""
		self.smtp_server = smoke_zephyr.utilities.parse_server(self.config['smtp_server'], 25)
		self.running = threading.Event()
		"""A :py:class:`threading.Event` object indicating if emails are being sent."""
		self.paused = threading.Event()
		"""A :py:class:`threading.Event` object indicating if the email sending operation is or should be paused."""
		self.should_stop = threading.Event()
		self.max_messages_per_minute = float(self.config.get('smtp_max_send_rate', 0.0))
		self.mail_options = []

	def tab_notify_sent(self, emails_done, emails_total):
		"""
		Notify the tab that messages have been sent.

		:param int emails_done: The number of emails that have been sent.
		:param int emails_total: The total number of emails that are going to be sent.
		"""
		if isinstance(self.tab, gui_utilities.GladeGObject):
			GLib.idle_add(lambda x: self.tab.notify_sent(*x), (emails_done, emails_total))

	def tab_notify_status(self, message):
		"""
		Handle a status message regarding the message sending operation.

		:param str message: The notification message.
		"""
		self.logger.info(message.lower())
		if isinstance(self.tab, gui_utilities.GladeGObject):
			GLib.idle_add(self.tab.notify_status, message + '\n')

	def tab_notify_stopped(self):
		"""
		Notify the tab that the message sending operation has stopped.
		"""
		if isinstance(self.tab, gui_utilities.GladeGObject):
			GLib.idle_add(self.tab.notify_stopped)

	def server_ssh_connect(self):
		"""
		Connect to the remote SMTP server over SSH and configure port forwarding
		with :py:class:`.SSHTCPForwarder` for tunneling SMTP traffic.

		:return: The connection status as one of the :py:class:`.ConnectionErrorReason` constants.
		"""
		server = smoke_zephyr.utilities.parse_server(self.config['ssh_server'], 22)
		username = self.config['ssh_username']
		password = self.config['ssh_password']
		remote_server = smoke_zephyr.utilities.parse_server(self.config['smtp_server'], 25)
		try:
			self._ssh_forwarder = SSHTCPForwarder(
				server,
				username,
				password,
				remote_server,
				private_key=self.config.get('ssh_preferred_key'),
				missing_host_key_policy=ssh_host_key.MissingHostKeyPolicy(self.application)
			)
			self._ssh_forwarder.start()
		except errors.KingPhisherAbortError as error:
			self.logger.info("ssh connection aborted ({0})".format(error.message))
		except paramiko.AuthenticationException:
			self.logger.warning('failed to authenticate to the remote ssh server')
			return ConnectionErrorReason.ERROR_AUTHENTICATION_FAILED
		except paramiko.SSHException as error:
			self.logger.warning("failed with: {0!r}".format(error))
		except socket.timeout:
			self.logger.warning('the connection to the ssh server timed out')
		except Exception:
			self.logger.warning('failed to connect to the remote ssh server', exc_info=True)
		else:
			self.smtp_server = self._ssh_forwarder.local_server
			return ConnectionErrorReason.SUCCESS
		return ConnectionErrorReason.ERROR_UNKNOWN

	def server_smtp_connect(self):
		"""
		Connect and optionally authenticate to the configured SMTP server.

		:return: The connection status as one of the :py:class:`.ConnectionErrorReason` constants.
		"""
		if self.config.get('smtp_ssl_enable', False):
			SmtpClass = smtplib.SMTP_SSL
		else:
			SmtpClass = smtplib.SMTP
		self.logger.debug('opening a new connection to the SMTP server')
		try:
			self.smtp_connection = SmtpClass(*self.smtp_server, timeout=15)
			self.smtp_connection.ehlo()
		except smtplib.SMTPException:
			self.logger.warning('received an SMTPException while connecting to the SMTP server', exc_info=True)
			return ConnectionErrorReason.ERROR_UNKNOWN
		except socket.error:
			self.logger.warning('received a socket.error while connecting to the SMTP server')
			return ConnectionErrorReason.ERROR_CONNECTION

		if not self.config.get('smtp_ssl_enable', False) and 'starttls' in self.smtp_connection.esmtp_features:
			self.logger.debug('target SMTP server supports the STARTTLS extension')
			try:
				self.smtp_connection.starttls()
				self.smtp_connection.ehlo()
			except smtplib.SMTPException:
				self.logger.warning('received an SMTPException while negotiating STARTTLS with the SMTP server', exc_info=True)
				return ConnectionErrorReason.ERROR_UNKNOWN

		username = self.config.get('smtp_username', '')
		if username:
			password = self.config.get('smtp_password', '')
			try:
				self.smtp_connection.login(username, password)
			except smtplib.SMTPException as error:
				self.logger.warning('received an {0} while authenticating to the SMTP server'.format(error.__class__.__name__))
				self.smtp_connection.quit()
				return ConnectionErrorReason.ERROR_AUTHENTICATION_FAILED

		if self.smtp_connection.has_extn('SMTPUTF8'):
			self.logger.debug('target SMTP server supports the SMTPUTF8 extension')
			self.mail_options.append('SMTPUTF8')
		return ConnectionErrorReason.SUCCESS

	def server_smtp_disconnect(self):
		"""Clean up and close the connection to the remote SMTP server."""
		if self.smtp_connection:
			self.logger.debug('closing the connection to the SMTP server')
			try:
				self.smtp_connection.quit()
			except smtplib.SMTPServerDisconnected:
				pass
			self.smtp_connection = None
			self.tab_notify_status('Disconnected from the SMTP server')

	def server_smtp_reconnect(self):
		"""
		Disconnect from the remote SMTP server and then attempt to open
		a new connection to it.

		:return: The reconnection status.
		:rtype: bool
		"""
		if self.smtp_connection:
			try:
				self.smtp_connection.quit()
			except smtplib.SMTPServerDisconnected:
				pass
			self.smtp_connection = None
		while self.server_smtp_connect() != ConnectionErrorReason.SUCCESS:
			self.tab_notify_status('Failed to reconnect to the SMTP server')
			if not self.process_pause(True):
				return False
		return True

	def count_targets(self):
		"""
		Count the number of targets that will be sent messages.

		:return: The number of targets that will be sent messages.
		:rtype: int
		"""
		return sum(1 for _ in self.iterate_targets(counting=True))

	def iterate_targets(self, counting=False):
		"""
		Iterate over each of the targets as defined within the configuration.
		If *counting* is ``False``, messages will not be displayed to the end
		user through the notification tab.

		:param bool counting: Whether or not to iterate strictly for counting purposes.
		:return: Each message target.
		:rtype: :py:class:`~.MessageTarget`
		"""
		mailer_tab = self.application.main_tabs['mailer']
		target_type = self.config['mailer.target_type']
		if target_type == 'single':
			target_name = self.config['mailer.target_name'].split(' ')
			while len(target_name) < 2:
				target_name.append('')
			uid_charset = self.config['mailer.message_uid.charset']
			target = MessageTarget(
				first_name=target_name[0].strip(),
				last_name=target_name[1].strip(),
				email_address=self.config['mailer.target_email_address'].strip(),
				uid=utilities.make_message_uid(
					upper=uid_charset['upper'],
					lower=uid_charset['lower'],
					digits=uid_charset['digits']
				)
			)
			if not counting:
				mailer_tab.emit('target-create', target)
			yield target
		elif target_type == 'file':
			for target in _iterate_targets_file(self.target_file, config=self.config):
				missing_fields = target.missing_fields
				if missing_fields:
					if counting:
						msg = "Target CSV line {0} skipped due to missing field{1}".format(target.line, ('' if len(missing_fields) == 1 else 's'))
						msg += ':' + ', '.join(field.replace('_', ' ') for field in missing_fields)
						self.tab_notify_status(msg)
					continue
				if not utilities.is_valid_email_address(target.email_address):
					self.logger.warning("skipping line {0} in target csv file due to invalid email address: {1}".format(target.line, target.email_address))
					continue
				if not counting:
					mailer_tab.emit('target-create', target)
				yield target
		else:
			self.logger.error("the configured target type '{0}' is unsupported".format(target_type))

	def run(self):
		"""The entry point of the thread."""
		self.logger.debug("mailer routine running in tid: 0x{0:x}".format(threading.current_thread().ident))
		self.running.set()
		self.should_stop.clear()
		self.paused.clear()

		try:
			self._prepare_env()
			emails_done = self._send_messages()
		except UnicodeDecodeError as error:
			self.logger.error("a unicode error occurred, {0} at position: {1}-{2}".format(error.reason, error.start, error.end))
			self.tab_notify_status("A unicode error occurred, {0} at position: {1}-{2}".format(error.reason, error.start, error.end))
		except Exception:
			self.logger.error('an error occurred while sending messages', exc_info=True)
			self.tab_notify_status('An error occurred while sending messages.')
		else:
			self.tab_notify_status("Finished sending, successfully sent {0:,} messages".format(emails_done))

		self.server_smtp_disconnect()
		if self._ssh_forwarder:
			self._ssh_forwarder.stop()
			self._ssh_forwarder = None
			self.tab_notify_status('Disconnected from the SSH server')
		self.tab_notify_stopped()
		return

	def process_pause(self, set_pause=False):
		"""
		Pause sending emails if a pause request has been set.

		:param bool set_pause: Whether to request a pause before processing it.
		:return: Whether or not the sending operation was cancelled during the pause.
		:rtype: bool
		"""
		if set_pause:
			if isinstance(self.tab, gui_utilities.GladeGObject):
				gui_utilities.glib_idle_add_wait(lambda: self.tab.pause_button.set_property('active', True))
			else:
				self.pause()
		if self.paused.is_set():
			self.tab_notify_status('Paused sending emails, waiting to resume')
			self.running.wait()
			self.paused.clear()
			if self.should_stop.is_set():
				self.tab_notify_status('Sending emails cancelled')
				return False
			self.tab_notify_status('Resuming sending emails')
			self.max_messages_per_minute = float(self.config.get('smtp_max_send_rate', 0.0))
		return True

	def create_message(self, target=None):
		if target is None:
			target = MessageTargetPlaceholder(uid=self.config['server_config'].get('server.secret_id'))
		attachments = self.get_mime_attachments()
		message = getattr(self, 'create_message_' + self.config['mailer.message_type'])(target, attachments)
		# set the Message-ID header, per RFC-2822 using the target UID and the sender domain
		mime_msg_id = '<' + target.uid
		if '@' in self.config['mailer.source_email']:
			mime_msg_id += '@' + self.config['mailer.source_email'].split('@', 1)[1]
		mime_msg_id += '>'
		message['Message-ID'] = mime_msg_id
		mailer_tab = self.application.main_tabs['mailer']
		mailer_tab.emit('message-create', target, message)
		return message

	def create_message_calendar_invite(self, target, attachments):
		"""
		Create a MIME calendar invite to be sent from a set of parameters.

		:param target: The information for the messages intended recipient.
		:type target: :py:class:`.MessageTarget`
		:param str uid: The message's unique identifier.
		:param attachments: The attachments to add to the created message.
		:type attachments: :py:class:`Attachments`
		:return: The new MIME message.
		:rtype: :py:class:`email.mime.multipart.MIMEMultipart`
		"""
		top_msg = TopMIMEMultipart('mixed', self.config, target)
		top_msg['To'] = target.email_address

		related_msg = mime.multipart.MIMEMultipart('related')
		top_msg.attach(related_msg)

		alt_msg = mime.multipart.MIMEMultipart('alternative')
		related_msg.attach(alt_msg)

		part = mime.base.MIMEBase('text', 'plain', charset='utf-8')
		part.set_payload(MIME_TEXT_PLAIN)
		encoders.encode_base64(part)
		alt_msg.attach(part)

		with codecs.open(self.config['mailer.html_file'], 'r', encoding='utf-8') as file_h:
			msg_template = file_h.read()
		formatted_msg = render_message_template(msg_template, self.config, target=target)
		part = MIMEText(formatted_msg, 'html')
		alt_msg.attach(part)

		start_time = get_invite_start_from_config(self.config)
		if self.config['mailer.calendar_invite_all_day']:
			duration = ics.DurationAllDay()
		else:
			duration = int(self.config['mailer.calendar_invite_duration']) * 60
		ical = ics.Calendar(
			self.config['mailer.source_email'],
			start_time,
			self.config.get('mailer.calendar_invite_summary'),
			duration=duration,
			location=self.config.get('mailer.calendar_invite_location')
		)
		ical.add_attendee(target.email_address, rsvp=self.config.get('mailer.calendar_request_rsvp', False))

		part = mime.base.MIMEBase('text', 'calendar', charset='utf-8', method='REQUEST')
		part.set_payload(ical.to_ical(encoding='utf-8'))
		encoders.encode_base64(part)
		alt_msg.attach(part)

		for attach in attachments.images:
			related_msg.attach(attach)

		for attach in attachments.files:
			top_msg.attach(attach)
		return top_msg

	def create_message_email(self, target, attachments):
		"""
		Create a MIME email to be sent from a set of parameters.

		:param target: The information for the messages intended recipient.
		:type target: :py:class:`.MessageTarget`
		:param str uid: The message's unique identifier.
		:param attachments: The attachments to add to the created message.
		:type attachments: :py:class:`MessageAttachments`
		:return: The new MIME message.
		:rtype: :py:class:`email.mime.multipart.MIMEMultipart`
		"""
		msg = TopMIMEMultipart('related', self.config, target)
		target_field = self.config.get('mailer.target_field', 'to').lower()
		for header in ('To', 'CC', 'BCC'):
			if header.lower() == target_field:
				msg[header] = '<' + target.email_address + '>'
				continue
			value = self.config.get('mailer.recipient_email_' + header.lower())
			if value:
				msg[header] = '<' + value + '>'

		importance = self.config.get('mailer.importance', 'Normal')
		if importance != 'Normal':
			msg['Importance'] = importance
		sensitivity = self.config.get('mailer.sensitivity', 'Normal')
		if sensitivity != 'Normal':
			msg['Sensitivity'] = sensitivity

		msg_alt = mime.multipart.MIMEMultipart('alternative')
		msg.attach(msg_alt)
		with codecs.open(self.config['mailer.html_file'], 'r', encoding='utf-8') as file_h:
			msg_template = file_h.read()
		formatted_msg = render_message_template(msg_template, self.config, target=target)
		# RFC-1341 page 35 states friendliest part must be attached first
		msg_body = MIMEText(MIME_TEXT_PLAIN, 'plain')
		msg_alt.attach(msg_body)
		msg_body = MIMEText(formatted_msg, 'html')
		msg_alt.attach(msg_body)
		msg_alt.set_default_type('html')

		# process attachments
		for attach in attachments.files:
			msg.attach(attach)
		for attach in attachments.images:
			msg.attach(attach)
		return msg

	def get_mime_attachments(self):
		"""
		Return a :py:class:`.MessageAttachments` object containing both the images and
		raw files to be included in sent messages.

		:return: A namedtuple of both files and images in their MIME containers.
		:rtype: :py:class:`.MessageAttachments`
		"""
		files = []
		# allow the attachment_file.post_processing to be attached instead of
		# attachment_file so attachment_file can be used as an input for
		# arbitrary operations to modify without over writing the original
		attachment_file = self.config.get('mailer.attachment_file.post_processing')
		delete_attachment_file = False
		if attachment_file is not None:
			if not isinstance(attachment_file, str):
				raise TypeError('config option mailer.attachment_file.post_processing is not a readable file')
			if not os.path.isfile(attachment_file) and os.access(attachment_file, os.R_OK):
				raise ValueError('config option mailer.attachment_file.post_processing is not a readable file')
			self.config['mailer.attachment_file.post_processing'] = None
			delete_attachment_file = True
		else:
			attachment_file = self.config.get('mailer.attachment_file')
		if attachment_file:
			attachfile = mime.base.MIMEBase(*mimetypes.guess_type(attachment_file))
			attachfile.set_payload(open(attachment_file, 'rb').read())
			encoders.encode_base64(attachfile)
			attachfile.add_header('Content-Disposition', "attachment; filename=\"{0}\"".format(os.path.basename(attachment_file)))
			files.append(attachfile)
			if delete_attachment_file and os.access(attachment_file, os.W_OK):
				os.remove(attachment_file)

		images = []
		for attachment_file, attachment_name in template_environment.attachment_images.items():
			attachfile = mime.image.MIMEImage(open(attachment_file, 'rb').read())
			attachfile.add_header('Content-ID', "<{0}>".format(attachment_name))
			attachfile.add_header('Content-Disposition', "inline; filename=\"{0}\"".format(attachment_name))
			images.append(attachfile)
		return MessageAttachments(tuple(files), tuple(images))

	def _prepare_env(self):
		with codecs.open(self.config['mailer.html_file'], 'r', encoding='utf-8') as file_h:
			msg_template = file_h.read()
		render_message_template(msg_template, self.config, analyze=True)
		template_environment.set_mode(template_environment.MODE_SEND)

	def _send_messages(self):
		emails_done = 0
		mailer_tab = self.application.main_tabs['mailer']
		max_messages_per_connection = self.config.get('mailer.max_messages_per_connection', 5)

		emails_total = "{0:,}".format(self.count_targets())
		sending_line = "Sending email {{0: >{0},}} of {1} with UID: {{1}} to {{2}}".format(len(emails_total), emails_total)
		emails_total = int(emails_total.replace(',', ''))

		for target in self.iterate_targets():
			iteration_time = time.time()
			if self.should_stop.is_set():
				self.tab_notify_status('Sending emails cancelled')
				break
			if not self.process_pause():
				break
			if emails_done > 0 and max_messages_per_connection > 0 and (emails_done % max_messages_per_connection == 0):
				self.server_smtp_reconnect()

			emails_done += 1
			if not all(mailer_tab.emit('target-send', target)):
				self.logger.info("target-send signal subscriber vetoed target: {0!r}".format(target))
				continue
			self.tab_notify_status(sending_line.format(emails_done, target.uid, target.email_address))

			message = self.create_message(target=target)
			if not all(mailer_tab.emit('message-send', target, message)):
				self.logger.info("message-send signal subscriber vetoed message to target: {0!r}".format(target))
				continue
			self.rpc(
				'campaign/message/new/deferred',
				self.config['campaign_id'],
				target.uid,
				target.email_address,
				target.first_name,
				target.last_name,
				target.department
			)
			if not self._try_send_message(target.email_address, message):
				self.rpc('db/table/delete', 'messages', target.uid)
				break
			self.rpc('db/table/set', 'messages', target.uid, ('sent',), (datetime.datetime.utcnow(),))

			self.tab_notify_sent(emails_done, emails_total)
			self.application.emit('message-sent', target.uid, target.email_address)

			if self.max_messages_per_minute:
				iteration_time = (time.time() - iteration_time)
				self._sleep((60.0 / float(self.max_messages_per_minute)) - iteration_time)
		return emails_done

	def _sleep(self, duration):
		while duration > 0:
			sleep_chunk = min(duration, 0.5)
			time.sleep(sleep_chunk)
			if self.should_stop.is_set():
				break
			duration -= sleep_chunk
		return self.should_stop.is_set()

	def _try_send_message(self, *args, **kwargs):
		message_sent = False
		while not message_sent and not self.should_stop.is_set():
			for i in range(0, 3):
				try:
					self.send_message(*args, **kwargs)
					message_sent = True
					break
				except smtplib.SMTPServerDisconnected:
					self.logger.warning('failed to send message, the server has been disconnected')
					self.tab_notify_status('Failed to send message, the server has been disconnected')
					self.tab_notify_status('Sleeping for 5 seconds before attempting to reconnect')
					if self._sleep(5):
						break
					self.smtp_connection = None
					self.server_smtp_reconnect()
				except smtplib.SMTPException as error:
					self.tab_notify_status("Failed to send message (exception: {0})".format(error.__class__.__name__))
					self.logger.warning("failed to send message (exception: smtplib.{0})".format(error.__class__.__name__))
					self._sleep((i + 1) ** 2)
			if not message_sent:
				self.server_smtp_disconnect()
				if not self.process_pause(True):
					return False
				self.server_smtp_reconnect()
		return True

	def send_message(self, target_email, msg):
		"""
		Send an email using the connected SMTP server.

		:param str target_email: The email address to send the message to.
		:param msg: The formatted message to be sent.
		:type msg: :py:class:`.mime.multipart.MIMEMultipart`
		"""
		source_email = self.config['mailer.source_email_smtp']
		self.smtp_connection.sendmail(source_email, target_email, msg.as_string(), self.mail_options)

	def pause(self):
		"""
		Sets the :py:attr:`~.MailSenderThread.running` and
		:py:attr:`~.MailSenderThread.paused` flags correctly to indicate
		that the object is paused.
		"""
		self.running.clear()
		self.paused.set()

	def unpause(self):
		"""
		Sets the :py:attr:`~.MailSenderThread.running` and
		:py:attr:`~.MailSenderThread.paused` flags correctly to indicate
		that the object is no longer paused.
		"""
		self.running.set()

	def stop(self):
		"""
		Requests that the email sending operation stop. It can not be
		resumed from the same position. This function blocks until the
		stop request has been processed and the thread exits.
		"""
		self.should_stop.set()
		self.unpause()
		if self.is_alive():
			self.join()

	def missing_files(self):
		"""
		Return a list of all missing or unreadable files which are referenced by
		the message template.

		:return: The list of unusable files.
		:rtype: list
		"""
		missing = []
		attachment = self.config.get('mailer.attachment_file')
		if attachment and not os.access(attachment, os.R_OK):
			missing.append(attachment)
		msg_template = self.config['mailer.html_file']
		if not os.access(msg_template, os.R_OK):
			missing.append(msg_template)
			return missing
		self._prepare_env()
		for attachment in template_environment.attachment_images.keys():
			if not os.access(attachment, os.R_OK):
				missing.append(attachment)
		return missing
