#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/sms.py
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

import argparse
import random
import re
import smtplib
import sys

import dns.resolver
import smoke_zephyr.utilities

if sys.version_info[0] < 3:
	from email.MIMEText import MIMEText
else:
	from email.mime.text import MIMEText

__version__ = '1.0'
__all__ = ('lookup_carrier_gateway', 'send_sms')

CARRIERS = {
	'AT&T':          'txt.att.net',
	'Boost':         'myboostmobile.com',
	'Sprint':        'messaging.sprintpcs.com',
	'T-Mobile':      'tmomail.net',
	'Verizon':       'vtext.com',
	'Virgin Mobile': 'vmobl.com',
}
"""A dictionary for mapping carrier names to SMS via email gateways."""

DEFAULT_FROM_ADDRESS = 'sms@king-phisher.com'
"""The default email address to use in the from field."""

@smoke_zephyr.utilities.Cache('6h')
def get_smtp_servers(domain):
	"""
	Get the SMTP servers for the specified domain by querying their MX records.

	:param str domain: The domain to look up the MX records for.
	:return: The smtp servers for the specified domain.
	:rtype: list
	"""
	mx_records = dns.resolver.query(domain, 'MX')
	return [str(r.exchange).rstrip('.') for r in mx_records]

def normalize_name(name):
	return name.lower().replace('&', '').replace('-', '')

def lookup_carrier_gateway(carrier):
	"""
	Lookup the SMS gateway for the specified carrier. Normalization on the
	carrier name does take place and if an invalid or unknown value is
	specified, None will be returned.

	:param str carrier: The name of the carrier to lookup.
	:return: The SMS gateway for the specified carrier.
	:rtype: str
	"""
	carrier = normalize_name(carrier)
	carrier_address = [c for c in CARRIERS.keys() if normalize_name(c) == carrier]
	if len(carrier_address) != 1:
		return None
	return CARRIERS[carrier_address[0]]

def send_sms(message_text, phone_number, carrier, from_address=None):
	"""
	Send an SMS message by emailing the carriers SMS gateway. This method
	requires no money however some networks are blocked by the carriers
	due to being flagged for spam which can cause issues.

	:param str message_text: The message to send.
	:param str phone_number: The phone number to send the SMS to.
	:param str carrier: The cellular carrier that the phone number belongs to.
	:param str from_address: The optional address to display in the 'from' field of the SMS.
	:return: This returns the status of the sent message.
	:rtype: bool
	"""
	from_address = (from_address or DEFAULT_FROM_ADDRESS)
	phone_number = phone_number.replace('-', '').replace(' ', '')
	# remove the country code for these 10-digit based
	match = re.match('1?(?P<phone_number>[0-9]{10})', phone_number)
	if match is None:
		raise ValueError('the phone number appears invalid')
	phone_number = match.group('phone_number')

	if len(message_text) > 160:
		raise ValueError('message length exceeds 160 characters')
	message = MIMEText(message_text)

	carrier_address = lookup_carrier_gateway(carrier)
	if not carrier_address:
		raise ValueError('unknown carrier specified')

	to_address = "{0}@{1}".format(phone_number, carrier_address)
	message['To'] = to_address
	message['From'] = from_address

	sms_gateways = get_smtp_servers(carrier_address)
	random.shuffle(sms_gateways)
	message_sent = False
	for sms_gateway in sms_gateways:
		try:
			smtp_connection = smtplib.SMTP(sms_gateway)
			smtp_connection.sendmail(from_address, [to_address], message.as_string())
			smtp_connection.quit()
		except (smtplib.SMTPConnectError, smtplib.SMTPDataError, smtplib.SMTPHeloError):
			continue
		message_sent = True
		break
	return message_sent

def _argp_sms_carrier_type(arg):
	if not lookup_carrier_gateway(arg):
		raise argparse.ArgumentTypeError("{0} is not a valid sms carrier".format(repr(arg)))
	return arg

def main():
	parser = argparse.ArgumentParser(description='Send SMS Messages', conflict_handler='resolve')
	parser.add_argument('--from', dest='from_email', default=DEFAULT_FROM_ADDRESS, help='the email address to send the message from')
	parser.add_argument('-v', '--version', action='version', version=parser.prog + ' Version: ' + __version__)
	parser.add_argument('phone_number', help='destination phone number')
	parser.add_argument('carrier', type=_argp_sms_carrier_type, help='target carrier')
	parser.add_argument('message', help='message text to send')
	results = parser.parse_args()

	if send_sms(results.message, results.phone_number, results.carrier, from_address=results.from_email):
		print('[+] Successfully Sent!')  # pylint: disable=superfluous-parens
	else:
		print('[-] Failed To Send')  # pylint: disable=superfluous-parens
	return 0

if __name__ == '__main__':
	main()
