#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/graphql/middleware.py
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

from __future__ import absolute_import

import king_phisher.server.database.models as db_models

# authorization middleware
class AuthorizationMiddleware(object):
	"""
	An authorization provider to ensure that the permissions on the objects
	that are queried are respected. If no **rpc_session** key is provided in
	the **context** dictionary then no authorization checks can be performed
	and all objects and operations will be accessible. The **rpc_session**
	key's value must be an instance of :py:class:`~.AuthenticatedSession`.
	"""
	def resolve(self, next_, root, info, **kwargs):
		if isinstance(root, db_models.Base) and not self.info_has_read_prop_access(info, root, instance=root):
			return
		return next_(root, info, **kwargs)

	@classmethod
	def info_has_read_prop_access(cls, info, model, field_name=None, instance=None):
		"""
		Check that the context provided by *info* has access to read the
		specified property of the model. This can be used to ensure that
		sessions which can not read a protected field can also not obtain
		indirect access such as filtering or sorting by it.

		:param info: The resolve information for this execution.
		:type info: :py:class:`graphql.execution.base.ResolveInfo`
		:param model: The SQLAlchemy model to check read-property access on.
		:type model: :py:class:`sqlalchemy.ext.declarative.api.Base`
		:param str field_name: The specific field name to check, otherwise ``info.field_name``.
		:param instance: An optional instance of *model* to use for the access check.
		:return: Whether or not the context is authorized to access the property.
		:rtype: bool
		"""
		rpc_session = info.context.get('rpc_session')
		if rpc_session is None:
			return True
		field_name = field_name or info.field_name
		return model.session_has_read_prop_access(rpc_session, field_name, instance=instance)
