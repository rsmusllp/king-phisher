#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/sphinxext/rpc.py
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

import re

from . import _exttools

from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import ObjType
from sphinx.roles import XRefRole

class DescRPCArgument(_exttools.ArgumentBase):
	"""Node for an argument wrapper"""

class DescRPCArgumentList(_exttools.ArgumentListBase):
	"""Node for a general parameter list."""

class RPCFunction(ObjectDescription):
	def add_target_and_index(self, name, sig, signode):
		targetname = 'rpc:%s-%s' % (self.objtype, name)
		signode['ids'].append(targetname)
		self.state.document.note_explicit_target(signode)
		self.env.domaindata[self.domain]['objects'][self.objtype, name] = self.env.docname, targetname
		self.indexnode['entries'].append(('single', name + ' (RPC function)', targetname, '', None))

	def handle_signature(self, sig, signode):
		m = re.match(r'([a-zA-Z0-9_/\(\):]+)\(([a-zA-Z0-9,\'"_= ]*)\)', sig)
		if not m:
			signode += addnodes.desc_name(sig, sig)
			return sig
		uri_path, args = m.groups()
		signode += addnodes.desc_name(uri_path, uri_path)
		plist = DescRPCArgumentList()
		args = args.split(',')
		for pos, arg in enumerate(args):
			arg = arg.strip()
			if pos < len(args) - 1:
				arg += ','
			x = DescRPCArgument()
			x += addnodes.desc_parameter(arg, arg)
			plist += x
		signode += plist
		return uri_path

class RPCDomain(_exttools.DomainBase):
	name = 'rpc'
	label = 'RPC'
	directives = {
		'function': RPCFunction,
	}
	object_types = {
		'function': ObjType('RPC Function', 'func'),
	}
	roles = {
		'func': XRefRole(),
	}

def setup(app):
	_exttools.add_app_node_arguments(app, DescRPCArgument, DescRPCArgumentList)
	app.add_domain(RPCDomain)
