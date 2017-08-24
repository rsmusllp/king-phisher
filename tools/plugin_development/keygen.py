#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tools/plugin_development/keygen.py
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
	parser.add_argument('file', type=argparse.FileType('wb'), help='the destination to write the PEM file to')
	arguments = parser.parse_args()

	color.print_status('generating a new ecdsa singing key')
	signing_key = ecdsa.SigningKey.generate(curve=ecdsa.NIST521p)
	verifying_key = signing_key.get_verifying_key()
	verifying_key = binascii.b2a_base64(verifying_key.to_string())
	verifying_key = verifying_key.decode('utf-8').strip()

	arguments.file.write(signing_key.to_pem())
	print(serializers.JSON.dumps({'id': arguments.id, 'verifying-key': {'type': ecdsa.NIST521p.openssl_name, 'data': verifying_key}}))

if __name__ == '__main__':
	sys.exit(main())
