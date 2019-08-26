#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/xor.py
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

import collections
import random

def xor_encode(data, seed_key=None, encoding='utf-8'):
	"""
	Encode data using the XOR algorithm. This is not suitable for encryption
	purposes and should only be used for light obfuscation. The key is
	prepended to the data as the first byte which is required to be decoded
	py the :py:func:`.xor_decode` function.

	:param bytes data: The data to encode.
	:param int seed_key: The optional value to use as the for XOR key.
	:return: The encoded data.
	:rtype: bytes
	"""
	if isinstance(data, str):
		data = data.encode(encoding)
	if seed_key is None:
		seed_key = random.randint(0, 255)
	else:
		seed_key &= 0xff
	encoded_data = collections.deque([seed_key])
	last_key = seed_key
	for byte in data:
		e_byte = (byte ^ last_key)
		last_key = e_byte
		encoded_data.append(e_byte)
	return bytes(encoded_data)

def xor_decode(data, encoding='utf-8'):
	"""
	Decode data using the XOR algorithm. This is not suitable for encryption
	purposes and should only be used for light obfuscation. This function
	requires the key to be set as the first byte of *data* as done in the
	:py:func:`.xor_encode` function.

	:param str data: The data to decode.
	:return: The decoded data.
	:rtype: str
	"""
	if isinstance(data, str):
		data = data.encode(encoding)
	data = collections.deque(data)
	last_key = data.popleft()
	decoded_data = collections.deque()
	for b in data:
		d = (b ^ last_key)
		last_key = b
		decoded_data.append(d)
	return bytes(decoded_data)
