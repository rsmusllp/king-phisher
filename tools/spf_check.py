#!/usr/bin/env python
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
import logging
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from king_phisher import spf
from king_phisher import utilities
from king_phisher import version

def main():
	parser = argparse.ArgumentParser(description='King Phisher SPF Check Utility', conflict_handler='resolve')
	parser.add_argument('-v', '--version', action='version', version=parser.prog + ' Version: ' + version.version)
	parser.add_argument('-L', '--log', dest='loglvl', action='store', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='CRITICAL', help='set the logging level')
	parser.add_argument('smtp_server_ip', help='the ip address of the sending smtp server')
	parser.add_argument('target_email', help='the email address that messages are from')
	arguments = parser.parse_args()

	logging.getLogger('').setLevel(logging.DEBUG)
	console_log_handler = logging.StreamHandler()
	console_log_handler.setLevel(getattr(logging, arguments.loglvl))
	console_log_handler.setFormatter(logging.Formatter("%(levelname)-8s %(message)s"))
	logging.getLogger('').addHandler(console_log_handler)

	server_ip = arguments.smtp_server_ip
	target_email = arguments.target_email

	if not utilities.is_valid_ip_address(server_ip):
		print('[-] the smtp server ip address specified is invalid')
		return

	if not utilities.is_valid_email_address(target_email):
		print('[-] the email address specified is invalid')
		return

	spf_sender, spf_domain = target_email.split('@')
	spf_test = spf.SenderPolicyFramework(server_ip, spf_domain, spf_sender)
	try:
		result = spf_test.check_host()
	except spf.SPFPermError:
		print('[-] check_host failed with error: permerror')
		return
	except spf.SPFTempError:
		print('[-] check_host failed with error: temperror')
		return
	if not result:
		print('[*] no spf policy was found for the specified domain')
		return

	print("[+] spf policy result: {0}".format(result))
	print('[*] top level spf records found:')
	for rid in range(len(spf_test.spf_records)):
		record = spf.record_unparse(spf_test.spf_records[rid])
		print("[*]   #{0} {1: <10} {2}".format(rid + 1, ('(matched)' if rid == spf_test.spf_record_id else ''), record))

if __name__ == '__main__':
	sys.exit(main())
