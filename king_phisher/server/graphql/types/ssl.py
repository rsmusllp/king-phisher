#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/graphql/types/ssl.py
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
import logging

from . import misc as gql_misctypes
from king_phisher.server import letsencrypt

import advancedhttpserver
import graphene.types.utils

__all__ = ('SSL',)

logger = logging.getLogger('KingPhisher.Server.GraphQL.Types.Templates')

class SNIHostname(graphene.ObjectType):
	enabled = graphene.Field(graphene.Boolean)
	hostname = graphene.Field(graphene.String)
	@classmethod
	def resolve(cls, info, **kwargs):
		hostname = kwargs.pop('hostname')
		sni_config = letsencrypt.get_sni_hostname_config(hostname)
		if sni_config is None:
			return None
		return cls(enabled=sni_config.enabled, hostname=hostname)

class SNIHostnameConnection(graphene.relay.Connection):
	class Meta:
		node = SNIHostname
	total = graphene.Int()
	@classmethod
	def resolve(cls, info, **kwargs):
		sni_hostnames = []
		for hostname, sni_config in letsencrypt.get_sni_hostnames(info.context.get('server_config')).items():
			sni_hostnames.append(SNIHostname(hostname=hostname, enabled=sni_config.enabled))
		return sni_hostnames

class SSLStatus(graphene.ObjectType):
	enabled = graphene.Field(graphene.Boolean)
	has_letsencrypt = graphene.Field(graphene.Boolean)
	has_sni = graphene.Field(graphene.Boolean)
	@classmethod
	def resolve(cls, info, **kwargs):
		server_config = info.context.get('server_config')
		if server_config:
			enabled = any(address.get('ssl', False) for address in server_config.get('server.addresses'))
		else:
			enabled = False
		instance = cls(
			enabled=enabled,
			has_letsencrypt=letsencrypt.get_certbot_bin_path(server_config) is not None,
			has_sni=advancedhttpserver.g_ssl_has_server_sni
		)
		return instance

class SSL(graphene.ObjectType):
	sni_hostname = graphene.Field(SNIHostname, hostname=graphene.String())
	sni_hostnames = gql_misctypes.ConnectionField(SNIHostnameConnection)
	status = graphene.Field(SSLStatus)
	def resolve_sni_hostname(self, info, **kwargs):
		return SNIHostname.resolve(info, **kwargs)

	def resolve_sni_hostnames(self, info, **kwargs):
		return SNIHostnameConnection.resolve(info, **kwargs)

	def resolve_status(self, info, **kwargs):
		return SSLStatus.resolve(info, **kwargs)

	@classmethod
	def resolve(cls, info, **kwargs):
		return cls()
