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

from docutils import nodes
from sphinx import addnodes
from sphinx.util import docfields
from king_phisher.third_party.domaintools import custom_domain

http_sig_param_re = re.compile(r'\((?:(?P<type>[^:)]+):)?(?P<name>[\w_]+)\)', re.VERBOSE)

class DescRPCArgument(nodes.Part, nodes.Inline, nodes.TextElement):
	"""Node for an argument wrapper"""

class DescRPCArgumentList(nodes.Part, nodes.Inline, nodes.TextElement):
	"""Node for a general parameter list."""
	child_text_separator = ' '

def argument_visit(self, node):
	pass

def argument_depart(self, node):
	pass

def html_argument_visit(self, node):
	self.body.append('<span class="arg">')

def html_argument_depart(self, node):
	self.body.append('</span>')

def argumentlist_visit(self, node):
	self.visit_desc_parameterlist(node)

def argumentlist_depart(self, node):
	self.depart_desc_parameterlist(node)

def html_argumentlist_visit(self, node):
	self.visit_desc_parameterlist(node)
	if len(node.children) > 3:
		self.body.append('<span class="long-argument-list">')
	else:
		self.body.append('<span class="argument-list">')

def html_argumentlist_depart(self, node):
	self.body.append('</span>')
	self.depart_desc_parameterlist(node)

def parse_macro_arguments(signode, args):
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

def parse_macro_uri_path(signode, uri_path):
	offset = 0
	path = None
	for match in http_sig_param_re.finditer(uri_path):
		path = uri_path[offset:match.start()]
		signode += addnodes.desc_name(path, path)
		params = addnodes.desc_parameterlist()
		typ = match.group('type')
		if typ:
			typ += ': '
			params += addnodes.desc_annotation(typ, typ)
		name = match.group('name')
		params += addnodes.desc_parameter(name, name)
		signode += params
		offset = match.end()
	if offset < len(uri_path):
		path = uri_path[offset:len(uri_path)]
		signode += addnodes.desc_name(path, path)
	if path is None:
		raise RuntimeError('no matches for sig')

def parse_macro(env, sig, signode):
	m = re.match(r'([a-zA-Z0-9_/\(\):]+)\(([a-zA-Z0-9,\'"_= ]*)\)', sig)
	if not m:
		signode += addnodes.desc_name(sig, sig)
		return sig
	uri_path, args = m.groups()
	parse_macro_uri_path(signode, uri_path)
	parse_macro_arguments(signode, args)
	return uri_path

def setup(app):
	app.add_node(
		node=DescRPCArgumentList,
		html=(html_argumentlist_visit, html_argumentlist_depart),
		latex=(argumentlist_visit, argumentlist_depart)
	)
	app.add_node(
		node=DescRPCArgument,
		html=(html_argument_visit, html_argument_depart),
		latex=(argument_visit, argument_depart)
	)
	app.add_domain(custom_domain(
		'RPCDomain',
		name='rpc',
		label='RPC',
		elements=dict(
			function=dict(
				objname='RPC Function',
				indextemplate=None,
				parse=parse_macro,
				role='func',
				fields=(
					docfields.Field(
						'handler',
						label="Handler",
						names=('handler',),
						has_arg=False
					),
					docfields.TypedField(
						'parameter',
						label='Parameters',
						names=('param', 'parameter', 'arg', 'argument'),
						typerolename='obj',
						typenames=('paramtype', 'type')
					)
				)
			)
		)
	))
