#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/client/dialogs.py
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
from king_phisher.client import dialogs
from king_phisher.client import gui_utilities

class ClientDialogTests(testing.KingPhisherTestCase):
	def test_client_dialog_classes(self):
		dialog_names = filter(lambda d: d.endswith('Dialog'), dir(dialogs))
		self.assertGreater(len(dialog_names), 0, msg='failed to identify any dialog objects')
		for dialog_name in dialog_names:
			dialog_obj = getattr(dialogs, dialog_name)
			msg = "{0} is not a subclass of UtilityGladeGObject".format(dialog_name)
			self.assertTrue(issubclass(dialog_obj, gui_utilities.UtilityGladeGObject), msg=msg)
			msg = "{0}.top_gobject is not 'dialog'".format(dialog_name)
			self.assertEqual(getattr(dialog_obj, 'top_gobject', None), 'dialog', msg=msg)
			msg = "{0} has no 'interact' method".format(dialog_name)
			self.assertTrue(hasattr(dialog_obj, 'interact'), msg=msg)

if __name__ == '__main__':
	unittest.main()
