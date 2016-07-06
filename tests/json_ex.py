from king_phisher import testing
from king_phisher import json_ex

class JsonExTests(testing.KingPhisherTestCase):
	def test_json_ex_dumps(self):
		self.assertIsInstance(json_ex.dumps('test'), str)
		self.assertIsInstance(json_ex.dumps(True), str)
		self.assertIsInstance(json_ex.dumps(100), str)

	def test_json_ex_loads(self):
		try:
			json_ex.loads(json_ex.dumps('test'))
		except ValueError:
			self.fail('Invalid data type for json_ex.loads()')

	def test_json_ex_loads_invalid(self):
		with self.assertRaises(ValueError):
			json_ex.loads("'test")
