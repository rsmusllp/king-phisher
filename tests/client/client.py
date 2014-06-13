#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/client/client.py
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

import sys
import unittest

from king_phisher import find
from king_phisher.client.client import *

from gi.repository import GObject
from gi.repository import Gtk

class ClientGUITests(unittest.TestCase):
	def test_client_initialization(self):
		find.data_path_append('data/client')
		os.environ['KING_PHISHER_GLADE_FILE'] = 'KingPhisherClient.glade'
		self.assertTrue(isinstance(gui_utilities.which_glade(), (str, unicode)))
		try:
			Gtk.init(sys.argv)
			main_window = KingPhisherClient()
			main_window.set_position(Gtk.WindowPosition.CENTER)
		except Exception as error:
			self.fail("failed to initialize KingPhisherClient (error: {0})".format(error.__class__.__name__))

if __name__ == '__main__':
	unittest.main()
