import random

def xor_encode(data, seed_key = None):
	seed_key = (seed_key or random.randint(0, 255))
	data = map(ord, data)
	encoded_data = [seed_key]
	last_key = seed_key
	for b in data:
		e = (b ^ last_key)
		last_key = e
		encoded_data.append(e)
	return ''.join(map(chr, encoded_data))

def xor_decode(data):
	data = map(ord, data)
	last_key = data.pop(0)
	decoded_data = []
	for b in data:
		d = (b ^ last_key)
		last_key = b
		decoded_data.append(d)
	return ''.join(map(chr, decoded_data))
