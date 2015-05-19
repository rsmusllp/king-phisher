#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tools/targets_from_recon_ng.py
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
import csv
import os
import random
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from king_phisher import color
from king_phisher import version

PARSER_EPILOG = """The format string uses Python's native .format syntax.

Format string examples:
  first initial followed by the last name (default)
    {first:.1}{last}
  first name dot last name
    {first}.{last}
"""

def main():
	parser = argparse.ArgumentParser(description='King Phisher Recon-ng Converter', conflict_handler='resolve', formatter_class=argparse.RawTextHelpFormatter)
	parser.add_argument('-f', '--format', dest='email_format', default='{first:.1}{last}', help='the email format string to use')
	parser.add_argument('-n', '--number', dest='limit', type=int, help='only process the specified number of contacts')
	parser.add_argument('--shuffle', action='store_true', default=False, help='shuffle the contacts to randomize their order')
	parser.add_argument('-v', '--version', action='version', version=parser.prog + ' Version: ' + version.version)
	parser.add_argument('in_file', help='the csv file of contacts from recon-ng')
	parser.add_argument('out_file', help='the target csv file to create for')
	parser.add_argument('domain', help='the domain to append to emails')
	parser.epilog = PARSER_EPILOG
	arguments = parser.parse_args()

	targets = []
	color.print_status('reading contacts from: ' + os.path.abspath(arguments.in_file))
	with open(arguments.in_file, 'r') as file_h:
		for row in csv.reader(file_h):
			targets.append((row[0], row[2]))

	color.print_status("read in {0:,} contacts from recon-ng csv output".format(len(targets)))
	if arguments.shuffle:
		random.shuffle(targets)
		color.print_status("shuffled the list of contacts")

	color.print_status('writing the results to: ' + os.path.abspath(arguments.out_file))
	with open(arguments.out_file, 'w') as file_h:
		writer = csv.writer(file_h)
		for first_name, last_name in targets[:arguments.limit]:
			email_address = arguments.email_format.format(first=first_name.lower(), last=last_name.lower())
			email_address += '@' + arguments.domain
			writer.writerow([first_name, last_name, email_address])

if __name__ == '__main__':
	sys.exit(main())
