#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/spf.py
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

import ipaddress
import logging
import re

import dns.exception
import dns.resolver

MACRO_REGEX = r'%\{([slodipvh])(\d*)([r]?)(.?)\}'
"""A regular expression which matches SPF record macros."""

QUALIFIERS = {
	'+': 'pass',
	'-': 'fail',
	'~': 'softfail',
	'?': 'neutral'
}
"""A dict object keyed with the qualifier symbols to their readable values."""

class SPFError(Exception):
	"""Base exception for errors raised by this module."""
	pass

class SPFPermError(SPFError):
	"""
	Exception indicating that the domains published records could not be
	correctly interpreted. Described in section 2.6.7 of RFC 7208.
	"""
	pass

class SPFTempError(SPFError):
	"""
	Exception indicating that the verification process encountered a transient
	(generally DNS) error while performing the check. Described in section 2.6.6
	of RFC 7208.
	"""
	pass

def check_host(ip, domain, sender=None):
	"""
	Analyze the Sender Policy Framework of a domain by creating a
	:py:class:`.SenderPolicyFramework` instance and returning the result of
	:py:meth:`.SenderPolicyFramework.check_host`.

	:param ip: The ip address of the host sending the message.
	:type ip: str, :py:class:`ipaddress.IPv4Address`, :py:class:`ipaddress.IPv6Address`
	:param str domain: The domain to check the SPF policy of.
	:param str sender: The "MAIL FROM" identity of the message being sent.
	:return: The SPF policy if one can be found or None.
	:rtype: None, str
	"""
	s = SenderPolicyFramework(ip, domain, sender)
	return s.check_host()

def validate_record(ip, domain, sender=None):
	"""
	Check if an SPF record exists for the domain and can be parsed by this
	module.

	:return: Whether the record exists and is parsable or not.
	:rtype: bool
	"""
	try:
		result = check_host(ip, domain, sender)
	except SPFPermError:
		return False
	return isinstance(result, str)

# http://tools.ietf.org/html/rfc7208
class SenderPolicyFramework(object):
	"""
	Analyze the Sender Policy Framework configuration for a domain to determine
	if an ip address is authorized to send messages on it's behalf. Sender
	Policy Framework is defined in
	`RFC 7208 <http://tools.ietf.org/html/rfc7208>`_. The exp modifier defined
	in section 6.2 of the RFC is not supported.
	"""
	def __init__(self, ip, domain, sender=None, spf_records=None):
		"""
		:param ip: The ip address of the host sending the message.
		:type ip: str, :py:class:`ipaddress.IPv4Address`, :py:class:`ipaddress.IPv6Address`
		:param str domain: The domain to check the SPF policy of.
		:param str sender: The "MAIL FROM" identity of the message being sent.
		"""
		if isinstance(ip, str):
			ip = ipaddress.ip_address(ip)
		self.ip = ip
		self.domain = domain
		self.helo_domain = 'unknown'
		sender = (sender or 'postmaster')
		if not '@' in sender:
			sender = sender + '@' + self.domain
		self.sender = sender
		self.spf_records = (spf_records or [])
		self.spf_record_id = -1

		# dns lookup limit per https://tools.ietf.org/html/rfc7208#section-4.6.4
		self.query_limit = 10
		self.policy = None
		self._policy_checked = False
		self.logger = logging.getLogger('KingPhisher.SPF.SenderPolicyFramework')

	def __repr__(self):
		return "<{0} ip={1} domain={2} sender={3} >".format(self.__class__.__name__, self.ip, self.domain, self.sender)

	def __str__(self):
		return (self.check_host() or '')

	def check_host(self):
		"""
		Check the SPF policy described by the object. The string representing the
		matched policy is returned if an SPF policy exists, otherwise None will
		be returned if no policy is defined.

		:return: The SPF policy described by the object.
		:rtype: None, str
		"""
		if not self._policy_checked:
			self.policy = self._check_host(self.ip, self.domain, self.sender)
			self._policy_checked = True
		return self.policy

	def _check_host(self, ip, domain, sender, top_level=True):
		try:
			answers = self._dns_query(domain, 'TXT')
		except SPFTempError:
			if not top_level:
				raise
			answers = []
		if len(answers) == 0:
			return None

		if len(answers) > 1:
			answers = list(filter(lambda answer: answer.strings[0].startswith('v=spf1 '), answers))
		record = ''.join(answers[0].strings)
		if not record.startswith('v=spf1 '):
			raise SPFPermError('failed to parse spf data')

		records = record[7:].split(' ')
		if not len(records):
			raise SPFPermError('failed to parse spf data')

		for record_id in range(len(records)):
			record = records[record_id]
			if len(self.spf_records) and self.spf_records[-1][0] == 'all':
				break

			if record.startswith('redirect='):
				if len(list(filter(lambda r: r.endswith('all'), records))):
					# ignore redirects when all is present per https://tools.ietf.org/html/rfc7208#section-6.1
					continue
				record = record[9:]
				domain = self.expand_macros(record, self.ip, domain, self.sender)
				return self._check_host(ip, domain, sender, top_level=False)

			if ':' in record:
				(mechanism, rvalue) = record.split(':', 1)
			else:
				(mechanism, rvalue) = (record, None)
			mechanism = mechanism.lower()

			qualifier = '+'
			if mechanism[0] in QUALIFIERS:
				qualifier = mechanism[0]
				mechanism = mechanism[1:]
			if not mechanism in ('a', 'all', 'exists', 'include', 'ip4', 'ip6', 'mx', 'ptr'):
				raise SPFPermError("unknown mechanism type: '{0}'".format(mechanism))

			if top_level:
				self.spf_records.append((mechanism, qualifier, rvalue))
			if self._evaluate_mechanism(ip, domain, sender, mechanism, rvalue):
				self.spf_record_id = record_id
				self.logger.debug("found matching spf record: '{0}'".format(record))
				return QUALIFIERS[qualifier]

		self.logger.debug('no records matched, returning default policy of \'neutral\'')
		# default result per https://tools.ietf.org/html/rfc7208#section-4.7
		return 'neutral'

	def _dns_query(self, qname, qtype):
		self.query_limit -= 1
		if not self.query_limit:
			raise SPFPermError('dns query limit reached')
		try:
			answers = dns.resolver.query(qname, qtype)
		except dns.exception.DNSException:
			raise SPFTempError('dns resolution error')
		return answers

	def _evaluate_mechanism(self, ip, domain, sender, mechanism, rvalue):
		if isinstance(rvalue, str):
			rvalue = self.expand_macros(rvalue, ip, domain, sender)
		else:
			rvalue = domain

		if mechanism == 'a':
			if self._hostname_matches_ip(ip, rvalue):
				return True
		elif mechanism == 'all':
			return True
		elif mechanism == 'exists':
			if len(self._dns_query(rvalue, 'A')):
				return True
		elif mechanism == 'include':
			# pass results in match per https://tools.ietf.org/html/rfc7208#section-5.2
			return self._check_host(ip, rvalue, sender, top_level=False) == 'pass'
		elif mechanism == 'ip4':
			ip_network = ipaddress.IPv4Network(rvalue, strict=False)
			if ip in ip_network:
				return True
		elif mechanism == 'ip6':
			ip_network = ipaddress.IPv6Network(rvalue, strict=False)
			if ip in ip_network:
				return True
		elif mechanism == 'mx':
			for mx_record in self._dns_query(domain, 'MX'):
				mx_record = str(mx_record.exchange).rstrip('.')
				if self._hostname_matches_ip(ip, mx_record):
					return True
		elif mechanism == 'ptr':
			if isinstance(ip, ipaddress.IPv4Address):
				ip = str(ip)
				suffix = 'in-addr'
			else:
				ip = '.'.join(ip.exploded.replace(':', ''))
				suffix = 'ip6'
			ptr_domain = (rvalue or domain)
			ip = ip.split('.')
			ip.reverse()
			ip = '.'.join(ip)
			for ptr_record in self._dns_query(ip + '.' + suffix + '.arpa', 'PTR'):
				ptr_record = str(ptr_record.target).rstrip('.')
				if ptr_domain == ptr_record or ptr_domain.endswith('.' + ptr_record):
					return True
		else:
			raise SPFPermError("unsupported mechanism type: '{0}'".format(mechanism))
		return False

	def _hostname_matches_ip(self, ip, name):
		qtype = ('A' if isinstance(ip, ipaddress.IPv4Address) else 'AAAA')
		answers = self._dns_query(name, qtype)
		return str(ip) in map(lambda a: a.address, answers)

	def expand_macros(self, value, ip, domain, sender):
		"""
		Expand a string based on the macros it contains as specified by section
		7 of RFC 7208.

		:param str value: The string containing macros to expand.
		:param ip: The ip address to use when expanding macros.
		:type ip: str, :py:class:`ipaddress.IPv4Address`, :py:class:`ipaddress.IPv6Address`
		:param str domain: The domain name to use when expanding macros.
		:param str sender: The email address of the sender to use when expanding macros.
		:return: The string with the interpreted macros replaced within it.
		:rtype: str
		"""
		if isinstance(ip, str):
			ip = ipaddress.ip_address(ip)

		macro_table = {
			's': sender,
			'l': sender.split('@', 1)[0],
			'o': sender.split('@', 1)[1],
			'd': domain,
			'i': (str(ip) if isinstance(ip, ipaddress.IPv4Address) else '.'.join(ip.exploded.replace(':', ''))),
			#'p'
			'v': ('in-addr' if isinstance(ip, ipaddress.IPv4Address) else 'ip6'),
			'h': self.helo_domain
		}

		for escape in (('%%', '%'), ('%-', '%20'), ('%_', ' ')):
			value = value.replace(*escape)

		end = 0
		result = ''
		for match in re.finditer(MACRO_REGEX, value):
			result += value[end:match.start()]
			macro_type = match.group(1)
			macro_digit = int(match.group(2) or 128)
			macro_reverse = (match.group(3) == 'r')
			macro_delimiter = (match.group(4) or '.')

			if not macro_type in macro_table:
				raise SPFPermError("unsupported macro type: '{0}'".format(macro_type))
			macro_value = macro_table[macro_type]
			macro_value = macro_value.split(macro_delimiter)
			if macro_reverse:
				macro_value.reverse()
			macro_value = macro_value[-macro_digit:]
			macro_value = '.'.join(macro_value)

			result += macro_value
			end = match.end()
		result += value[end:]
		return result
