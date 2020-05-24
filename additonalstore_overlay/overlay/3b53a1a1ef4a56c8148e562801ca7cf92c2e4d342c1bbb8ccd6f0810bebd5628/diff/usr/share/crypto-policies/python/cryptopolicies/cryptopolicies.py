# SPDX-License-Identifier: LGPL-2.1-or-later

# Copyright (c) 2019 Red Hat, Inc.
# Copyright (c) 2019 Tomáš Mráz <tmraz@fedoraproject.org>

import sys
import os
import os.path
import argparse
import re
import copy

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

class CryptoPolicy:
	string_re = re.compile('^(\w|-|\.)+$', re.ASCII)

	ALL_MAC = ['AEAD', 'UMAC-128', 'HMAC-SHA1', 'HMAC-SHA2-256',
		'HMAC-SHA2-384', 'HMAC-SHA2-512', 'UMAC-64', 'HMAC-MD5']
	ALL_HASH = ['SHA2-256', 'SHA2-384', 'SHA2-512', 'SHA3-256',
		'SHA3-384', 'SHA3-512', 'SHA2-224', 'SHA1', 'MD5', 'GOST']
# we disable curves <= 256 bits by default in Fedora
	ALL_GROUP = ['X25519', 'SECP256R1', 'SECP384R1', 'SECP521R1', 'X448',
		'FFDHE-1536', 'FFDHE-2048', 'FFDHE-3072', 'FFDHE-4096',
		'FFDHE-6144', 'FFDHE-8192', 'FFDHE-1024']

	ALL_SSH_GROUP = ALL_GROUP

	ALL_SIGN = ['RSA-MD5', 'RSA-SHA1', 'DSA-SHA1', 'ECDSA-SHA1',
		'RSA-SHA2-224', 'DSA-SHA2-224', 'ECDSA-SHA2-224',
		'RSA-SHA2-256', 'DSA-SHA2-256', 'ECDSA-SHA2-256',
		'RSA-SHA2-384', 'DSA-SHA2-384', 'ECDSA-SHA2-384',
		'RSA-SHA2-512', 'DSA-SHA2-512', 'ECDSA-SHA2-512',
		'RSA-SHA3-256', 'DSA-SHA3-256', 'ECDSA-SHA3-256',
		'RSA-SHA3-384', 'DSA-SHA3-384', 'ECDSA-SHA3-384',
		'RSA-SHA3-512', 'DSA-SHA3-512', 'ECDSA-SHA3-512',
		'EDDSA-ED25519', 'EDDSA-ED448',
		'RSA-PSS-SHA1', 'RSA-PSS-SHA2-224', 'RSA-PSS-SHA2-256',
		'RSA-PSS-SHA2-384', 'RSA-PSS-SHA2-512', 'RSA-PSS-RSAE-SHA1',
		'RSA-PSS-RSAE-SHA2-224', 'RSA-PSS-RSAE-SHA2-256',
		'RSA-PSS-RSAE-SHA2-384', 'RSA-PSS-RSAE-SHA2-512']

	ALL_CIPHER = ['AES-256-GCM', 'AES-256-CCM', 'AES-128-GCM',
		'AES-128-CCM', 'CHACHA20-POLY1305', 'CAMELLIA-256-GCM',
		'CAMELLIA-128-GCM', 'AES-256-CTR', 'AES-256-CBC',
		'AES-128-CTR', 'AES-128-CBC', 'CAMELLIA-256-CBC',
		'CAMELLIA-128-CBC', '3DES-CBC', 'DES-CBC', 'RC4-40',
		'RC4-128', 'DES40-CBC', 'RC2-CBC', 'IDEA-CBC', 'SEED-CBC',
		'NULL']

	ALL_TLS_CIPHER = ALL_CIPHER

	ALL_SSH_CIPHER = ALL_CIPHER

	ALL_KEY_EXCHANGE = ['PSK', 'DHE-PSK', 'ECDHE-PSK', 'ECDHE', 'RSA',
		'DHE', 'DHE-RSA', 'DHE-DSS', 'EXPORT', 'ANON', 'DH', 'ECDH']

	ALL_PROTOCOL = ['SSL2.0', 'SSL3.0', 'TLS1.0', 'TLS1.1', 'TLS1.2',
		'TLS1.3', 'DTLS1.0', 'DTLS1.2']

	ALL_IKE_PROTOCOL = ['IKEv1', 'IKEv2']

	ALL_PROPS = {'hash':ALL_HASH, 'mac':ALL_MAC, 'group':ALL_GROUP,
		'sign':ALL_SIGN, 'tls_cipher':ALL_TLS_CIPHER,
		'cipher':ALL_CIPHER, 'key_exchange':ALL_KEY_EXCHANGE,
		'protocol':ALL_PROTOCOL, 'ike_protocol':ALL_IKE_PROTOCOL,
		'ssh_cipher':ALL_SSH_CIPHER, 'ssh_group':ALL_SSH_GROUP}

	DEFAULT_PROPS = {'hash':[], 'mac':[], 'group':[],
			 'sign':[], 'tls_cipher':[], 'cipher':[],
			 'key_exchange':[], 'protocol':[],
			 'ike_protocol':[],
			 'min_tls_version': '', 'min_dtls_version':'',
			 'min_dh_size': 0, 'min_rsa_size': 0,
			 'min_dsa_size': 0, 'sha1_in_certs': 0,
			 'arbitrary_dh_groups': 0,
			 'ssh_cipher': [], 'ssh_group': [],
			 'ssh_certs': 0, 'ssh_etm': 0}

	DERIVED_PROPS = {'tls_cipher':'cipher', 'ssh_cipher':'cipher',
			 'ssh_group':'group'}

	CONFIG_DIR = '/etc/crypto-policies'

	SHARE_DIR = '/usr/share/crypto-policies'

	def __init__(self, policydir=None):
		self.props = {}
		self.inverted_props = {}
		self.errors = 0
		self.policydir = policydir

	def lookup_policy(self, policyname, subpolicy):
		if self.policydir:
			pdir = self.policydir
		else:
			pdir = 'policies'
		if subpolicy:
			pdir = os.path.join(pdir, 'modules')
			suffix = '.pmod'
		else:
			suffix = '.pol'

		fname = policyname + suffix
		if os.access(fname, os.R_OK):
			return fname

		path = os.path.join(pdir, fname)
		if os.access(path, os.R_OK):
			return path

		cpath = os.path.join(self.CONFIG_DIR, path)
		if os.access(cpath, os.R_OK):
			return cpath

		spath = os.path.join(self.SHARE_DIR, path)
		if os.access(spath, os.R_OK):
			return spath

		raise ValueError('Unknown policy: ' + policyname)

	@classmethod
	def parse_list(cls, name, value, orig):
		l = value.split()
		for item in l:
			ins = 0
			app = 0
			rem = 0
			if item[:1] == '-':
			    rem = 1
			    item = item[1:]
			if item[:1] == '+':
			    ins = 1
			    item = item[1:]
			if item[-1:] == '+':
			    app = 1
			    item = item[:-1]
			if rem + ins + app > 1:
				raise ValueError('multiple operations for list item \'%s\'' % item)
			if not cls.string_re.match(item):
				raise ValueError('invalid list item \'%s\'' % item)
			if item not in cls.ALL_PROPS[name]:
				raise ValueError('unknown list item \'%s\'' % item)
			if ins:
				orig.insert(0, item)
			elif rem:
				try:
					orig.remove(item)
				except ValueError:
					pass
			else:
				# append is the default
				orig.append(item)
		return orig

	@classmethod
	def parse_str(cls, value):
		s = value.strip()
		if not cls.string_re.match(s):
			raise ValueError('invalid string \'%s\'' % s)
		return s

	@staticmethod
	def parse_int(value):
		i = int(value.strip())
		return i

	def parse(self, f, subpolicy):
		prevline = ''
		for line in f:
			if line.endswith('\\\n'):
				prevline += line[:-2].split('#', 1)[0]
				continue
			line = prevline + line.split('#', 1)[0]
			prevline = ''
			line = line.strip()
			if not line:
				continue
			try:
				(name, value) = line.split('=', 1)
			except ValueError:
				eprint('Syntax error on line: %s' % line)

			name = name.strip()
			if not name in self.DEFAULT_PROPS:
				eprint('Unknown policy property: %s' % name)
				self.errors += 1
				continue
			prop = self.props.get(name, copy.copy(self.DEFAULT_PROPS[name]))
			try:
				if isinstance(prop, list):
					if subpolicy:
						prop = self.parse_list(name, value, prop)
					else:
						prop = self.parse_list(name, value, [])
				elif isinstance(prop, str):
					prop = self.parse_str(value)
				elif isinstance(prop, int):
					prop = self.parse_int(value)
				self.props[name] = prop
			except ValueError as e:
				eprint('Bad value of policy property: %s - %s' % (name, e))
				self.errors += 1
		# resolve property derivation if this is not a subpolicy
		if not subpolicy:
			for name, base in self.DERIVED_PROPS.items():
				if base in self.props:
					self.props.setdefault(name, copy.copy(self.props[base]))
		# assign any missing properties to the default
		for name, default in self.DEFAULT_PROPS.items():
			self.props.setdefault(name, copy.copy(default))

	def load_policy(self, policyname, subpolicy=False):
		fname = self.lookup_policy(policyname, subpolicy)

		with open(fname, "r") as f:
			self.parse(f, subpolicy)

	def load_subpolicies(self, policylist):
		for p in policylist:
			self.load_policy(p, True)

	def finalize(self):
		self.inverted_props = {}
		for prop in self.ALL_PROPS:
			self.inverted_props[prop] = [s for s in self.ALL_PROPS[prop]
				if s not in self.props[prop]]
