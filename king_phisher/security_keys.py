#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/security_keys.py
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

import binascii
import copy
import json
import logging
import os

from king_phisher import find
from king_phisher import serializers
from king_phisher import utilities

import ecdsa
import ecdsa.curves
import ecdsa.keys
import jsonschema

ecdsa_curves = dict((c.name, c) for c in ecdsa.curves.curves)
"""
A dictionary of :py:class:`ecdsa.curves.Curve` objects keyed by their
:py:mod:`ecdsa` and OpenSSL compatible names.
"""
ecdsa_curves.update((c.openssl_name, c) for c in ecdsa.curves.curves)

def _decode_data(value, encoding=None):
	if isinstance(encoding, str):
		encoding = encoding.lower()
	if encoding == 'base64':
		value = binascii.a2b_base64(value)
	elif encoding == 'hex':
		value = binascii.a2b_hex(value)
	elif encoding is not None:
		raise ValueError('unknown encoding: ' + encoding)
	return value

def _encoding_data(value, encoding=None):
	if isinstance(encoding, str):
		encoding = encoding.lower()
	if encoding == 'base64':
		value = binascii.b2a_base64(value).decode('utf-8').strip()
	elif encoding == 'hex':
		value = binascii.b2a_hex(value).decode('utf-8').strip()
	elif encoding is not None:
		raise ValueError('unknown encoding: ' + encoding)
	return value

def _key_cls_from_dict(cls, value, encoding=None):
	key_data = _decode_data(value['data'], encoding=encoding)
	return cls.from_string(key_data, curve=value['type'])

def _kwarg_curve(kwargs):
	if 'curve' not in kwargs:
		return kwargs
	curve = kwargs.pop('curve')
	if isinstance(curve, str):
		if curve not in ecdsa_curves:
			raise ValueError('unknown curve: ' + curve)
		curve = ecdsa_curves[curve]
	elif not isinstance(curve, ecdsa.curves.Curve):
		raise TypeError('curve must either be a curve name or ecdsa.curves.Curve instance')
	kwargs['curve'] = curve
	return kwargs

class SigningKey(ecdsa.SigningKey, object):
	@classmethod
	def from_secret_exponent(cls, *args, **kwargs):
		instance = super(SigningKey, cls).from_secret_exponent(*args, **kwargs)
		orig_vk = instance.verifying_key
		instance.verifying_key = VerifyingKey.from_public_point(orig_vk.pubkey.point, instance.curve, instance.default_hashfunc)
		return instance

	@classmethod
	def from_string(cls, string, **kwargs):
		kwargs = _kwarg_curve(kwargs)
		return super(SigningKey, cls).from_string(string, **kwargs)

	@classmethod
	def from_dict(cls, value, encoding='base64'):
		return _key_cls_from_dict(cls, value, encoding=encoding)

	def sign_dict(self, data, signature_encoding='base64'):
		"""
		Sign a dictionary object. The dictionary will have a 'signature' key
		added is required by the :py:meth:`.VerifyingKey.verify_dict` method.
		To serialize the dictionary to data suitable for the operation the
		:py:func:`json.dumps` function is used and the resulting data is then
		UTF-8 encoded.

		:param dict data: The dictionary of data to sign.
		:param str signature_encoding: The encoding name of the signature data.
		"""
		utilities.assert_arg_type(data, dict, arg_pos=1)
		data = copy.copy(data)
		json_data = json.dumps(data, sort_keys=True).encode('utf-8')
		data['signature'] = _encoding_data(self.sign(json_data), encoding=signature_encoding)
		return data

class VerifyingKey(ecdsa.VerifyingKey, object):
	@classmethod
	def from_string(cls, string, **kwargs):
		kwargs = _kwarg_curve(kwargs)
		return super(VerifyingKey, cls).from_string(string, **kwargs)

	@classmethod
	def from_dict(cls, value, encoding='base64'):
		return _key_cls_from_dict(cls, value, encoding=encoding)

	def verify_dict(self, data, signature_encoding='base64'):
		"""
		Verify a signed dictionary object. The dictionary must have a
		'signature' key as added by the :py:meth:`.SigningKey.sign_dict`
		method. To serialize the dictionary to data suitable for the operation
		the :py:func:`json.dumps` function is used and the resulting data is
		then UTF-8 encoded.

		:param dict data: The dictionary of data to verify.
		:param str signature_encoding: The encoding name of the signature data.
		"""
		utilities.assert_arg_type(data, dict, arg_pos=1)
		data = copy.copy(data)
		signature = _decode_data(data.pop('signature'), encoding=signature_encoding)
		data = json.dumps(data, sort_keys=True).encode('utf-8')
		return self.verify(signature, data)

class SecurityKeys(object):
	"""
	The security keys that are installed on the system. These are then used to
	validate the signatures of downloaded files to ensure they have not been
	corrupted or tampered with.

	.. note::
		Keys are first loaded from the security.json file included with the
		application source code and then from an optional security.local.json
		file. Keys loaded from the optional file can not over write keys loaded
		from the system file.
	"""
	logger = logging.getLogger('KingPhisher.SecurityKeys')
	def __init__(self):
		self.keys = utilities.FreezableDict()
		"""The dictionary of the loaded security keys, keyed by their identity string."""
		if not self._load_key_store('security.json'):
			raise RuntimeError('failed to load any keys from the primary store')
		self._load_key_store('security.local.json')
		self.keys.freeze()
		self.logger.info("security key store initialized with {0:,} keys".format(len(self.keys)))

	def _get_verifying_key(self, key_id):
		key = self.keys.get(key_id)
		if key is None:
			self.logger.warning("verification of data with key {0} failed (unknown key)".format(key_id))
			raise ecdsa.keys.BadSignatureError('unknown key for signature')
		verifying_key = key.get('verifying-key')
		if verifying_key is None:
			self.logger.warning("verification of data with key {0} failed (missing verifying-key)".format(key_id))
			raise ecdsa.keys.BadSignatureError('unknown key for signature')
		return verifying_key

	def _load_key_store(self, file_name):
		file_path = find.data_file(file_name)
		if not file_path:
			return 0
		with open(file_path, 'r') as file_h:
			key_store = serializers.JSON.load(file_h)
		utilities.validate_json_schema(key_store, 'king-phisher.security')
		key_store = key_store['keys']
		loaded = 0
		for key_idx, key in enumerate(key_store, 1):
			identifier = key['id']
			if identifier in self.keys:
				self.logger.warning("skipping loading {0}:{1} due to a duplicate id".format(file_name, key_idx))
				continue
			verifying_key = key['verifying-key']
			key['verifying-key'] = VerifyingKey.from_dict(verifying_key, encoding=verifying_key.pop('encoding', 'base64'))
			self.keys[identifier] = key
			self.logger.debug("loaded key id: {0} from: {1}".format(identifier, file_path))
			loaded += 1
		return loaded

	def verify(self, key_id, data, signature):
		"""
		Verify the data with the specified signature as signed by the specified
		key. This function will raise an exception if the verification fails
		for any reason, including if the key can not be found.

		:param str key_id: The key's identifier.
		:param bytes data: The data to verify against the signature.
		:param bytes signature: The signature of the data to verify.
		"""
		verifying_key = self._get_verifying_key(key_id)
		return verifying_key.verify(signature, data)

	def verify_dict(self, data, signature_encoding='base64'):
		"""
		Verify the signed dictionary, using the key specified within the
		'signed-by' key. This function will raise an exception if the
		verification fails for any reason, including if the key can not be
		found.

		:param str key_id: The key's identifier.
		:param bytes data: The data to verify against the signature.
		:param bytes signature: The signature of the data to verify.
		"""
		key_id = data['signed-by']
		verifying_key = self._get_verifying_key(key_id)
		return verifying_key.verify_dict(data, signature_encoding=signature_encoding)
