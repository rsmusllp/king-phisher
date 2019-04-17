#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/database/validation.py
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
import logging
import re

logger = logging.getLogger('KingPhisher.Server.Database.Validation')

# it is important for all of the field names to also be valid for a database Credential object
CredentialCollection = collections.namedtuple('CredentialCollection', ('username', 'password', 'mfa_token'))
"""A collection describing raw credential information."""

def validate_credential(credential, campaign):
	"""
	Validate a *credential* object with regards to the configuration provided in
	*campaign*. This uses :py:func:`~.validate_credential_fields` to validate
	each field individually and then return either ``None``, ``True`` or
	``False``. If no validation took place on any field, ``None`` is returned,
	otherwise if any field was validated then a boolean is returned indicating
	whether or not all validated (non-``None``) fields passed validation.

	:param credential: The credential object to validate.
	:param campaign: The campaign with the validation configuration.
	:return: Either a boolean or ``None`` depending on the results.
	"""
	fields = validate_credential_fields(credential, campaign)
	fields = tuple(getattr(fields, field) for field in CredentialCollection._fields)
	if all(field is None for field in fields):
		return None
	return all(field is None or field is True for field in fields)

def validate_credential_fields(credential, campaign):
	"""
	Validate a *credential* object with regards to the configuration provided in
	*campaign*. Each field in the *credential* object is validated and a new
	:py:class:`~.CredentialCollection` is returned with it's fields set to the
	results of the validation. A fields validation results are either ``None``,
	``True`` or ``False``. If no validation took place on the field, either
	because nothing was configured for it in *campaign*,or the validation
	information was invalid (a malformed regex for example) the result will be
	``None``. Otherwise, the result is either ``True`` or ``False`` for the
	field depending on the validation.

	:param credential: The credential object to validate.
	:param campaign: The campaign with the validation configuration.
	:return: A :py:class:`~.CredentialCollection` object with the fields set to the results of their respective validation.
	:rtype: :py:class:`~.CredentialCollection`
	"""
	# note that this uses duck-typing so the *credential* object could be either a db_models.Credential instance or a
	# db_validation.CredentialCollection instance
	validated = True
	results = {}
	for field in CredentialCollection._fields:
		results[field] = None  # default to None (no validation occurred on this field)
		regex = getattr(campaign, 'credential_regex_' + field, None)
		if regex is None:
			continue
		try:
			regex = re.compile(regex)
		except re.error:
			logger.warning("regex compile error while validating credential field: {0}".format(field), exc_info=True)
			continue
		value = getattr(credential, field)
		if value is None:
			validated = False
		else:
			validated = validated and regex.match(value) is not None
		if not validated:
			logger.debug("credential failed regex validation on field: {0}".format(field))
		results[field] = validated
	return CredentialCollection(**results)
