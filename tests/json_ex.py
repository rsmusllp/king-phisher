import unittest
import datetime

from king_phisher import testing
from king_phisher import json_ex

class JsonExTests(testing.KingPhisherTestCase):
	def test_dumps(self):
		self.assertIsInstance(json_ex.dumps('test'), basestring)
		self.assertIsInstance(json_ex.dumps(True), basestring)
		self.assertIsInstance(json_ex.dumps(100), basestring)

	def test_loads(self):
		try:
			 json_ex.loads(json_ex.dumps("test"))
		except ValueError:
			self.fail('Invalid data type for json_ex.loads()')
