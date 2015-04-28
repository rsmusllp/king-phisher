#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/spf.py
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

import unittest

from king_phisher import testing
from king_phisher import spf

class SPFTests(testing.KingPhisherTestCase):
	@testing.skip_if_offline
	def test_spf_check_host(self):
		s = spf.SenderPolicyFramework('1.2.3.4', 'king-phisher.com')
		check_host_result = s.check_host()
		self.assertIsNotNone(check_host_result)
		self.assertEqual(check_host_result, 'fail')

		self.assertEqual(spf.check_host('1.2.3.4', 'king-phisher.com'), 'fail')

	@testing.skip_if_offline
	def test_spf_evaluate_mechanism(self):
		s = spf.SenderPolicyFramework('1.2.3.4', 'doesnotexist.king-phisher.com')
		eval_mech = lambda m, r: s._evaluate_mechanism(s.ip_address, s.domain, s.sender, m, r)
		self.assertTrue(eval_mech('all', None))
		self.assertTrue(eval_mech('exists', '%{d2}'))
		self.assertTrue(eval_mech('ip4', '1.2.3.0/24'))
		self.assertTrue(eval_mech('ip4', '1.2.3.4'))
		self.assertFalse(eval_mech('ip4', '1.1.1.0/24'))

	def test_spf_evaluate_mechanism_permerror(self):
		s = spf.SenderPolicyFramework('1.2.3.4', 'doesnotexist.king-phisher.com')
		eval_mech = lambda m, r: s._evaluate_mechanism(s.ip_address, s.domain, s.sender, m, r)
		with self.assertRaises(spf.SPFPermError):
			eval_mech('ip4', 'thisisnotanetwork')
		with self.assertRaises(spf.SPFPermError):
			eval_mech('ip6', 'thisisnotanetwork')
		with self.assertRaises(spf.SPFPermError):
			eval_mech('fake', None)

	def test_spf_evaluate_mechanism_temperror(self):
		s = spf.SenderPolicyFramework('1.2.3.4', 'doesnotexist.king-phisher.com')
		eval_mech = lambda m, r: s._evaluate_mechanism(s.ip_address, s.domain, s.sender, m, r)
		with self.assertRaises(spf.SPFTempError):
			eval_mech('a', None)
		with self.assertRaises(spf.SPFTempError):
			eval_mech('exists', None)
		with self.assertRaises(spf.SPFTempError):
			eval_mech('mx', None)

	def test_spf_nonexistent_domain(self):
		s = spf.SenderPolicyFramework('1.2.3.4', 'doesnotexist.king-phisher.com')
		self.assertIsNone(s.check_host())
		self.assertIsNone(spf.check_host('1.2.3.4', 'doesnotexist.king-phisher.com'))

	def test_spf_rfc7208_macro_expansion(self):
		spf_records = [('all', '-', None)]
		s = spf.SenderPolicyFramework('192.0.2.3', 'email.example.com', 'strong-bad@email.example.com', spf_records=spf_records)
		expand_macro = lambda m: s.expand_macros(m, '192.0.2.3', 'email.example.com', 'strong-bad@email.example.com')

		self.assertEqual(expand_macro('%{s}'), 'strong-bad@email.example.com')
		self.assertEqual(expand_macro('%{o}'), 'email.example.com')
		self.assertEqual(expand_macro('%{d}'), 'email.example.com')
		self.assertEqual(expand_macro('%{d4}'), 'email.example.com')
		self.assertEqual(expand_macro('%{d3}'), 'email.example.com')
		self.assertEqual(expand_macro('%{d2}'), 'example.com')
		self.assertEqual(expand_macro('%{d1}'), 'com')
		self.assertEqual(expand_macro('%{dr}'), 'com.example.email')
		self.assertEqual(expand_macro('%{d2r}'), 'example.email')
		self.assertEqual(expand_macro('%{l}'), 'strong-bad')
		self.assertEqual(expand_macro('%{l-}'), 'strong.bad')
		self.assertEqual(expand_macro('%{lr}'), 'strong-bad')
		self.assertEqual(expand_macro('%{lr-}'), 'bad.strong')
		self.assertEqual(expand_macro('%{l1r-}'), 'strong')

		self.assertEqual(expand_macro('%{ir}.%{v}._spf.%{d2}'), '3.2.0.192.in-addr._spf.example.com')
		self.assertEqual(expand_macro('%{lr-}.lp._spf.%{d2}'), 'bad.strong.lp._spf.example.com')
		self.assertEqual(expand_macro('%{lr-}.lp.%{ir}.%{v}._spf.%{d2}'), 'bad.strong.lp.3.2.0.192.in-addr._spf.example.com')
		self.assertEqual(expand_macro('%{ir}.%{v}.%{l1r-}.lp._spf.%{d2}'), '3.2.0.192.in-addr.strong.lp._spf.example.com')
		self.assertEqual(expand_macro('%{d2}.trusted-domains.example.net'), 'example.com.trusted-domains.example.net')

	def test_spf_record_unparse(self):
		self.assertEqual(spf.record_unparse(('all', '+', None)), 'all')
		self.assertEqual(spf.record_unparse(('all', '-', None)), '-all')

		self.assertEqual(spf.record_unparse(('include', '+', '_spf.wonderland.com')), 'include:_spf.wonderland.com')
		self.assertEqual(spf.record_unparse(('ip4', '+', '10.0.0.0/24')), 'ip4:10.0.0.0/24')

if __name__ == '__main__':
	unittest.main()
