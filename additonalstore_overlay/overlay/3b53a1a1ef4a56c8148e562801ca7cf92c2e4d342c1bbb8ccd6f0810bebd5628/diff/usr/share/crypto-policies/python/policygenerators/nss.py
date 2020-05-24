# SPDX-License-Identifier: LGPL-2.1-or-later

# Copyright (c) 2019 Red Hat, Inc.
# Copyright (c) 2019 Tomáš Mráz <tmraz@fedoraproject.org>

from subprocess import call, CalledProcessError
from tempfile import mkstemp

import os

from .configgenerator import ConfigGenerator


class NSSGenerator(ConfigGenerator):
	CONFIG_NAME = 'nss'

	mac_map = {
		'AEAD':'',
		'HMAC-SHA1':'HMAC-SHA1',
		'HMAC-MD5':'HMAC-MD5',
		'HMAC-SHA2-256':'HMAC-SHA256',
		'HMAC-SHA2-384':'HMAC-SHA384',
		'HMAC-SHA2-512':'HMAC-SHA512'
	}

	hash_map = {
		'SHA1':'SHA1',
		'MD5':'MD5',
		'SHA2-224':'SHA224',
		'SHA2-256':'SHA256',
		'SHA2-384':'SHA384',
		'SHA2-512':'SHA512',
		'SHA3-256':'',
		'SHA3-384':'',
		'SHA3-512':'',
		'GOST':''
	}

	curve_map = {
		'X25519':'CURVE25519',
		'X448':'',
		'SECP256R1':'SECP256R1',
		'SECP384R1':'SECP384R1',
		'SECP521R1':'SECP521R1'
	}

	cipher_map = {
		'AES-256-CTR':'',
		'AES-128-CTR':'',
		'RC2-CBC':'rc2',
		'RC4-128':'rc4',
		'AES-256-GCM':'aes256-gcm',
		'AES-128-GCM':'aes128-gcm',
		'AES-256-CBC':'aes256-cbc',
		'AES-128-CBC':'aes128-cbc',
		'CAMELLIA-256-CBC':'camellia256-cbc',
		'CAMELLIA-128-CBC':'camellia128-cbc',
		'CAMELLIA-256-GCM':'',
		'CAMELLIA-128-GCM':'',
		'AES-256-CCM':'',
		'AES-128-CCM':'',
		'CHACHA20-POLY1305':'chacha20-poly1305',
		'3DES-CBC':'des-ede3-cbc'
	}

	key_exchange_map = {
		'PSK':'',
		'DHE-PSK':'',
		'ECDHE-PSK':'',
		'RSA':'RSA',
		'DHE-RSA':'DHE-RSA',
		'DHE-DSS':'DHE-DSS',
		'ECDHE':'ECDHE-RSA:ECDHE-ECDSA',
		'ECDH':'ECDH-RSA:ECDH-ECDSA',
		'DH':'DH-RSA:DH-DSS'
	}

	protocol_map = {
		'SSL3.0':'ssl3.0',
		'TLS1.0':'tls1.0',
		'TLS1.1':'tls1.1',
		'TLS1.2':'tls1.2',
		'TLS1.3':'tls1.3',
		'DTLS1.0':'dtls1.0',
		'DTLS1.2':'dtls1.2'
	}

	@classmethod
	def generate_config(cls, policy):
		p = policy.props

		cfg = 'library=\n'
		cfg += 'name=Policy\n'
		cfg += 'NSS=flags=policyOnly,moduleDB\n'
		cfg += 'config="disallow=ALL allow='

		s = ''
		for i in p['mac']:
			try:
				s = cls.append(s, cls.mac_map[i])
			except KeyError:
				pass

		for i in p['group']:
			try:
				s = cls.append(s, cls.curve_map[i])
			except KeyError:
				pass

		for i in p['tls_cipher']:
			try:
				s = cls.append(s, cls.cipher_map[i])
			except KeyError:
				pass

		for i in p['hash']:
			try:
				s = cls.append(s, cls.hash_map[i])
			except KeyError:
				pass

		for i in p['key_exchange']:
			try:
				s = cls.append(s, cls.key_exchange_map[i])
			except KeyError:
				pass

		dsa = [i for i in p['sign'] if i.find('DSA-') == 0]
		if dsa:
			s = cls.append(s, 'DSA')

		try:
			minver = cls.protocol_map[p['min_tls_version']]
		except KeyError:
			minver = '0'
		s = cls.append(s, 'tls-version-min=' + minver)

		try:
			minver = cls.protocol_map[p['min_dtls_version']]
		except KeyError:
			minver = '0'
		s = cls.append(s, 'dtls-version-min=' + minver)

		s = cls.append(s, 'DH-MIN=' + str(p['min_dh_size']))
		s = cls.append(s, 'DSA-MIN=' + str(p['min_dsa_size']))
		s = cls.append(s, 'RSA-MIN=' + str(p['min_rsa_size']))

		cfg += s + '"\n\n\n'
		return cfg

	@classmethod
	def test_config(cls, config):
		if not os.access('/usr/bin/nss-policy-check', os.X_OK):
			return True

		fd, path = mkstemp()

		try:
			with os.fdopen(fd, 'w') as f:
				f.write(config)
			try:
				call('/usr/bin/nss-policy-check ' + path +
					' >/dev/null 2>/dev/null',
					shell=True)
			except CalledProcessError:
				cls.eprint("There is an error in NSS generated policy")
				cls.eprint("Policy:\n%s" % config)
				return False
		finally:
			os.unlink(path)

		return True
