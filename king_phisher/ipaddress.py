#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/ipaddress.py
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

import functools
import ipaddress

from king_phisher import its

def convert_address(func):
	if not its.py_v2:
		return func
	@functools.wraps(func)
	def wrapper(address, *args, **kwargs):
		if isinstance(address, str):
			address = address.decode('utf-8')
		return func(address, *args, **kwargs)
	return wrapper

ip_address = convert_address(ipaddress.ip_address)
ip_network = convert_address(ipaddress.ip_network)
ip_interface = convert_address(ipaddress.ip_interface)

AddressValueError = ipaddress.AddressValueError

IPv4Address = ipaddress.IPv4Address
IPv4Network = ipaddress.IPv4Network
IPv6Address = ipaddress.IPv6Address
IPv6Network = ipaddress.IPv6Network

def is_loopback(address):
	"""
	Check if an address is a loopback address or a common name for the loopback
	interface.

	:param str address: The address to check.
	:return: Whether or not the address is a loopback address.
	:rtype: bool
	"""
	if address == 'localhost':
		return True
	elif is_valid(address) and ip_address(address).is_loopback:
		return True
	return False

@convert_address
def is_valid(address):
	"""
	Check that the string specified appears to be either a valid IPv4 or IPv6
	address.

	:param str address: The IP address to validate.
	:return: Whether the IP address appears to be valid or not.
	:rtype: bool
	"""
	try:
		ipaddress.ip_address(address)
	except ValueError:
		return False
	return True
