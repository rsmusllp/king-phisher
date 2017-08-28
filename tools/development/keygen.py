#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tools/development/keygen.py
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
import binascii
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import king_phisher.color as color
import king_phisher.serializers as serializers
import king_phisher.utilities as utilities

import ecdsa

def main():
	parser = argparse.ArgumentParser(description='King Phisher Signing-Key Generation Utility', conflict_handler='resolve')
	utilities.argp_add_args(parser)
	parser.add_argument('id', help='this key\'s identifier')
	parser.add_argument('file', type=argparse.FileType('w'), help='the destination to write the PEM file to')
	arguments = parser.parse_args()

	curve = ecdsa.NIST521p
	color.print_status('generating a new ecdsa singing key')
	signing_key = ecdsa.SigningKey.generate(curve=curve)
	verifying_key = signing_key.get_verifying_key()

	signing_key = binascii.b2a_base64(signing_key.to_string()).decode('utf-8').strip()
	verifying_key = binascii.b2a_base64(verifying_key.to_string()).decode('utf-8').strip()

	print('public key information for inclusion in security.json:')
	key_info = {
		'id': arguments.id,
		'verifying-key': {
			'data': verifying_key,
			'type': curve.openssl_name
		}
	}
	print(serializers.JSON.dumps(key_info))

	key_info['signing-key'] = {
		'data': signing_key,
		'type': curve.openssl_name
	}
	serializers.JSON.dump(key_info, arguments.file)

if __name__ == '__main__':
	sys.exit(main())
