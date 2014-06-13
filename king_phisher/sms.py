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
import smtplib
from email.MIMEText import MIMEText

from king_phisher import utilities

import dns.resolver

__version__ = '0.1'
__all__ = ['send_sms']

CARRIERS = {
	'Alltel':        'message.alltel.com',
	'AT&T':          'txt.att.net',
	'Boost':         'myboostmobile.com',
	'Sprint':        'messaging.sprintpcs.com',
	'T-Mobile':      'tmomail.net',
	'Verizon':       'vtext.com',
	'Virgin Mobile': 'vmobl.com',
}
"""A dictionary for mapping carrier names to SMS via email gateways."""

@utilities.Cache('6h')
def get_smtp_servers(domain):
	mx_records = dns.resolver.query(domain, 'MX')
	return map(lambda r: str(r.exchange).rstrip('.'), mx_records)

def normalize_name(name):
	return name.lower().replace('&', '').replace('-', '')

def send_sms(message_text, phone_number, carrier, from_address=None):
	"""
	Send an SMS message by emailing the carriers SMS gateway. This method
	requires no money however some networks are blocked by the carriers
	due to being flagged for spam which can cause issues.

	:param str message_text: The message to send.
	:param str phone_number: The phone number to send the SMS to.
	:param str carrier: The cellular carrier that the phone number belongs to.
	:param str from_address: The optional address to display in the 'from' field of the SMS.
	:return: This returns the status of the sent messsage.
	:rtype: bool
	"""
	from_address = (from_address or 'donotreply@nowhere.com')
	phone_number = phone_number.replace('-', '').replace(' ', '')
	if len(message_text) > 160:
		raise ValueError('message length exceeds 160 characters')
	message = MIMEText(message_text)

	carrier = normalize_name(carrier)
	carrier_address = filter(lambda c: normalize_name(c) == carrier, CARRIERS.keys())
	if len(carrier_address) != 1:
		raise ValueError('unknown carrier specified')
	carrier_address = CARRIERS[carrier_address[0]]

	to_address = "{0}@{1}".format(phone_number, carrier_address)
	message['To'] = to_address
	message['From'] = from_address

	sms_gateways = get_smtp_servers(carrier_address)
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

def main():
	parser = argparse.ArgumentParser(description='Send SMS Messages', conflict_handler='resolve')
	parser.add_argument('-v', '--version', action='version', version=parser.prog + ' Version: ' + __version__)
	parser.add_argument('phone_number', help='destination phone number')
	parser.add_argument('carrier', help='target carrier')
	parser.add_argument('message', help='message text to send')
	results = parser.parse_args()

	if send_sms(results.message, results.phone_number, results.carrier):
		print('[+] Successfully Sent!')
	else:
		print('[-] Failed To Send')
	return 0

if __name__ == '__main__':
	main()
