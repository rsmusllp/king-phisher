#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/errors.py
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

class KingPhisherError(Exception):
	"""
	The base exception that is inherited by all custom King Phisher error
	classes.
	"""
	def __init__(self, message=''):
		super(KingPhisherError, self).__init__()
		self.message = message

class KingPhisherAbortError(KingPhisherError):
	"""
	An exception that can be raised to indicate that an arbitrary operation
	needs to be aborted when no better method can be used.
	"""
	pass

class KingPhisherAbortRequestError(KingPhisherAbortError):
	"""
	An exception that can be raised which when caught will cause the handler to
	immediately stop processing the current request.
	"""
	def __init__(self, response_sent=False):
		"""
		:param bool response_sent: Whether or not a response has already been sent to the client.
		"""
		super(KingPhisherAbortRequestError, self).__init__()
		self.response_sent = response_sent

class KingPhisherAPIError(KingPhisherAbortError):
	"""
	An exception that can be raised to indicate that an error occurred while
	handling an API related request.
	"""
	pass

class KingPhisherDatabaseError(KingPhisherError):
	"""
	An exception that can be raised by King Phisher when there is any error
	relating to the database, it's configuration or any action involving it. The
	underlying database API will raise exceptions of it's own kind.
	"""
	pass

class KingPhisherDatabaseAuthenticationError(KingPhisherDatabaseError):
	"""
	An exception that is raised when King Phisher can not authenticate to the
	database. This is usually due to the configured password being incorrect.
	"""
	def __init__(self, message, username=None):
		super(KingPhisherDatabaseAuthenticationError, self).__init__(message)
		self.username = username

class KingPhisherGraphQLQueryError(KingPhisherError):
	"""
	An exception raised when a GraphQL query fails to execute correctly.
	"""
	def __init__(self, message='', errors=None, query=None, query_vars=None):
		super(KingPhisherGraphQLQueryError, self).__init__(message)
		self.errors = errors
		self.query = query
		self.query_vars = query_vars

class KingPhisherInputValidationError(KingPhisherError):
	"""
	An exception that is raised when any kind of input into King Phisher fails
	to be properly validated.
	"""
	pass

class KingPhisherPermissionError(KingPhisherError):
	"""
	An exception that is raised by King Phisher when some form of a request can
	not be satisfied due to the configured level of access.
	"""
	pass

class KingPhisherPluginError(KingPhisherError):
	"""
	An exception that is raised by King Phisher to indicate an error regarding
	a particular plugin.
	"""
	def __init__(self, plugin_name, *args, **kwargs):
		super(KingPhisherPluginError, self).__init__(*args, **kwargs)
		self.plugin_name = plugin_name

class KingPhisherResourceError(KingPhisherError):
	"""
	An exception that is raised by King Phisher when there is a problem relating
	to a resource such as it is missing, locked, inaccessible or otherwise
	invalid.
	"""
	pass

class KingPhisherTimeoutError(KingPhisherError):
	"""
	An exception that is raised by King Phisher when some form of a request
	fails to complete within a specified time period.
	"""
	pass
