#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tools/spf_check.py
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
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import king_phisher.color as color
import king_phisher.ipaddress as ipaddress
import king_phisher.spf as spf
import king_phisher.utilities as utilities

def main():
	parser = argparse.ArgumentParser(description='King Phisher SPF Check Utility', conflict_handler='resolve')
	utilities.argp_add_args(parser)
	parser.add_argument('smtp_server_ip', help='the ip address of the sending smtp server')
	parser.add_argument('target_email', help='the email address that messages are from')
	parser.add_argument('--dns-timeout', dest='dns_timeout', default=spf.DEFAULT_DNS_TIMEOUT, type=int, help='the timeout for dns queries')
	arguments = parser.parse_args()

	server_ip = arguments.smtp_server_ip
	target_email = arguments.target_email

	if not ipaddress.is_valid(server_ip):
		color.print_error('the smtp server ip address specified is invalid')
		return

	if not '@' in target_email:
		target_email = utilities.random_string_lower_numeric(8) + '@' + target_email
		color.print_status('target email appears to be just a domain, changed to: ' + target_email)

	if not utilities.is_valid_email_address(target_email):
		color.print_error('the email address specified is invalid')
		return

	spf_sender, spf_domain = target_email.split('@')
	spf_test = spf.SenderPolicyFramework(server_ip, spf_domain, sender=spf_sender, timeout=arguments.dns_timeout)
	try:
		result = spf_test.check_host()
	except spf.SPFParseError as error:
		color.print_error('check_host failed with error: permerror (parsing failed)')
		color.print_error('error reason: ' + error.message)
		return
	except spf.SPFPermError as error:
		color.print_error('check_host failed with error: permerror')
		color.print_error('error reason: ' + error.message)
		return
	except spf.SPFTempError as error:
		color.print_error('check_host failed with error: temperror')
		color.print_error('error reason: ' + error.message)
		return
	if not result:
		color.print_status('no spf policy was found for the specified domain')
		return

	color.print_good("spf policy result: {0}".format(result))
	color.print_status('top level spf records found:')
	match = spf_test.match
	for record_id, record in enumerate(spf_test.records.values(), 1):
		color.print_status("  #{0} {1: <10} {2}".format(
			record_id,
			('(matched)' if match.record == record else ''),
			record.domain
		))
		for directive_id, directive in enumerate(record.directives, 1):
			color.print_status("    #{0}.{1: <2} {2: <10} {3}".format(
				record_id,
				directive_id,
				('(matched)' if match.record == record and match.directive == directive else ''),
				directive
			))

if __name__ == '__main__':
	sys.exit(main())
