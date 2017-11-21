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
import hashlib
import json
import logging

from king_phisher import find
from king_phisher import serializers
from king_phisher import utilities

import cryptography.hazmat.primitives.ciphers
import cryptography.hazmat.primitives.ciphers.algorithms
import cryptography.hazmat.primitives.ciphers.modes
import cryptography.hazmat.primitives.padding as padding
import cryptography.hazmat.backends as backends
import ecdsa
import ecdsa.curves
import ecdsa.keys

ciphers = cryptography.hazmat.primitives.ciphers
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

def _key_cls_from_dict(cls, value, encoding=None, **kwargs):
	key_data = _decode_data(value['data'], encoding=encoding)
	return cls.from_string(key_data, curve=value['type'], **kwargs)

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

def openssl_decrypt_data(ciphertext, password, digest='sha256', encoding='utf-8'):
	"""
	Decrypt *ciphertext* in the same way as OpenSSL. For the meaning of
	*digest* see the :py:func:`.openssl_derive_key_and_iv` function
	documentation.

	.. note::
		This function can be used to decrypt ciphertext created with the
		``openssl`` command line utility.

		.. code-block:: none

			openssl enc -e -aes-256-cbc -in file -out file.enc -md sha256

	:param bytes ciphertext: The encrypted data to decrypt.
	:param str password: The password to use when deriving the decryption key.
	:param str digest: The name of hashing function to use to generate the key.
	:param str encoding: The name of the encoding to use for the password.
	:return: The decrypted data.
	:rtype: bytes
	"""
	salt = b''
	if ciphertext[:8] == b'Salted__':
		salt = ciphertext[8:16]
		ciphertext = ciphertext[16:]
	my_key, my_iv = openssl_derive_key_and_iv(password, salt, 32, 16, digest=digest, encoding=encoding)

	cipher = ciphers.Cipher(
		ciphers.algorithms.AES(my_key),
		ciphers.modes.CBC(my_iv),
		backend=backends.default_backend()
	)
	decryptor = cipher.decryptor()
	plaintext = decryptor.update(ciphertext) + decryptor.finalize()

	unpadder = padding.PKCS7(cipher.algorithm.block_size).unpadder()
	return unpadder.update(plaintext) + unpadder.finalize()

def openssl_derive_key_and_iv(password, salt, key_length, iv_length, digest='sha256', encoding='utf-8'):
	"""
	Derive an encryption key and initialization vector (IV) in the same way as
	OpenSSL.

	.. note::
		Different versions of OpenSSL use a different default value for the
		*digest* function used to derive keys and initialization vectors. A
		specific one can be used by passing the ``-md`` option to the
		``openssl`` command which corresponds to the *digest* parameter of this
		function.

	:param str password: The password to use when deriving the key and IV.
	:param bytes salt: A value to use as a salt for the operation.
	:param int key_length: The length in bytes of the key to return.
	:param int iv_length: The length in bytes of the IV to return.
	:param str digest: The name of hashing function to use to generate the key.
	:param str encoding: The name of the encoding to use for the password.
	:return: The key and IV as a tuple.
	:rtype: tuple
	"""
	password = password.encode(encoding)
	digest_function = getattr(hashlib, digest)
	chunk = b''
	data = b''
	while len(data) < key_length + iv_length:
		chunk = digest_function(chunk + password + salt).digest()
		data += chunk
	return data[:key_length], data[key_length:key_length + iv_length]

class SigningKey(ecdsa.SigningKey, object):
	def __init__(self, *args, **kwargs):
		self.id = kwargs.pop('id', None)
		"""An optional string identifier for this key instance."""
		super(SigningKey, self).__init__(*args, **kwargs)

	@classmethod
	def from_secret_exponent(cls, *args, **kwargs):
		id_ = kwargs.pop('id', None)
		instance = super(SigningKey, cls).from_secret_exponent(*args, **kwargs)
		orig_vk = instance.verifying_key
		instance.verifying_key = VerifyingKey.from_public_point(orig_vk.pubkey.point, instance.curve, instance.default_hashfunc, id=id_)
		instance.id = id_
		return instance

	@classmethod
	def from_string(cls, string, **kwargs):
		kwargs = _kwarg_curve(kwargs)
		id_ = kwargs.pop('id', None)
		inst = super(SigningKey, cls).from_string(string, **kwargs)
		inst.id = id_
		inst.verifying_key.id = id_
		return inst

	@classmethod
	def from_dict(cls, value, encoding='base64', **kwargs):
		"""
		Load the signing key from the specified dict object.

		:param dict value: The dictionary to load the key data from.
		:param str encoding: The encoding of the required 'data' key.
		:param dict kwargs: Additional key word arguments to pass to the class on initialization.
		:return: The new signing key.
		:rtype: :py:class:`.SigningKey`
		"""
		return _key_cls_from_dict(cls, value, encoding=encoding, **kwargs)

	@classmethod
	def from_file(cls, file_path, password=None, encoding='utf-8'):
		"""
		Load the signing key from the specified file. If *password* is
		specified, the file is assumed to have been encrypted using OpenSSL
		with ``aes-256-cbc`` as the cipher and ``sha256`` as the message
		digest. This uses :py:func:`.openssl_decrypt_data` internally for
		decrypting the data.

		:param str file_path: The path to the file to load.
		:param str password: An optional password to use for decrypting the file.
		:param str encoding: The encoding of the data.
		:return: A tuple of the key's ID, and the new :py:class:`.SigningKey` instance.
		:rtype: tuple
		"""
		with open(file_path, 'rb') as file_h:
			file_data = file_h.read()
		if password:
			file_data = openssl_decrypt_data(file_data, password, encoding=encoding)

		file_data = file_data.decode(encoding)
		file_data = serializers.JSON.loads(file_data)
		utilities.validate_json_schema(file_data, 'king-phisher.security.key')
		return cls.from_dict(file_data['signing-key'], encoding=file_data.pop('encoding', 'base64'), id=file_data['id'])

	def sign_dict(self, data, signature_encoding='base64'):
		"""
		Sign a dictionary object. The dictionary will have a 'signature' key
		added is required by the :py:meth:`.VerifyingKey.verify_dict` method.
		To serialize the dictionary to data suitable for the operation the
		:py:func:`json.dumps` function is used and the resulting data is then
		UTF-8 encoded.

		:param dict data: The dictionary of data to sign.
		:param str signature_encoding: The encoding name of the signature data.
		:return: The dictionary object is returned with the 'signature' key added.
		"""
		utilities.assert_arg_type(data, dict, arg_pos=1)
		data = copy.copy(data)
		data.pop('signature', None)  # remove a pre-existing signature
		json_data = json.dumps(data, sort_keys=True).encode('utf-8')
		data['signature'] = _encoding_data(self.sign(json_data), encoding=signature_encoding)
		return data

class VerifyingKey(ecdsa.VerifyingKey, object):
	def __init__(self, *args, **kwargs):
		self.id = kwargs.pop('id', None)
		"""An optional string identifier for this key instance."""
		super(VerifyingKey, self).__init__(*args, **kwargs)

	@classmethod
	def from_public_point(cls, *args, **kwargs):
		id_ = kwargs.pop('id', None)
		inst = super(VerifyingKey, cls).from_public_point(*args, **kwargs)
		inst.id = id_
		return inst

	@classmethod
	def from_string(cls, string, **kwargs):
		kwargs = _kwarg_curve(kwargs)
		id_ = kwargs.pop('id', None)
		inst = super(VerifyingKey, cls).from_string(string, **kwargs)
		inst.id = id_
		return inst

	@classmethod
	def from_dict(cls, value, encoding='base64', **kwargs):
		"""
		Load the verifying key from the specified dict object.

		:param dict value: The dictionary to load the key data from.
		:param str encoding: The encoding of the required 'data' key.
		:param dict kwargs: Additional key word arguments to pass to the class on initialization.
		:return: The new verifying key.
		:rtype: :py:class:`.VerifyingKey`
		"""
		return _key_cls_from_dict(cls, value, encoding=encoding, **kwargs)

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
