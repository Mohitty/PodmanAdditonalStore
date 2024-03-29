# SPDX-License-Identifier: LGPL-2.1-or-later

# Copyright (c) 2019 Red Hat, Inc.
# Copyright (c) 2019 Tomáš Mráz <tmraz@fedoraproject.org>

from subprocess import call, CalledProcessError
from tempfile import mkstemp

import os

from .configgenerator import ConfigGenerator


class OpenSSHGenerator(ConfigGenerator):
	cipher_map = {
		'AES-256-GCM':'aes256-gcm@openssh.com',
		'AES-256-CTR':'aes256-ctr',
		'AES-128-GCM':'aes128-gcm@openssh.com',
		'AES-128-CTR':'aes128-ctr',
		'CHACHA20-POLY1305':'chacha20-poly1305@openssh.com',
		'CAMELLIA-256-GCM':'',
		'AES-128-CCM':'',
		'AES-256-CCM':'',
		'CAMELLIA-128-GCM':'',
		'AES-256-CBC':'aes256-cbc',
		'AES-128-CBC':'aes128-cbc',
		'CAMELLIA-256-CBC':'',
		'CAMELLIA-128-CBC':'',
		'RC4-128':'',
		'DES-CBC':'',
		'CAMELLIA-128-CTS':'',
		'3DES-CBC':'3des-cbc'
	}

	gss_hash_map = {
		'SHA1':'gss-gex-sha1-,gss-group14-sha1-',
		# Newer algorithms not enabled due to RFC not final yet
		'SHA2-256':'',
		'SHA2-384':'',
		'SHA2-512':'',
		'SHA3-256':'',
		'SHA3-384':'',
		'SHA3-512':'',
		'MD5':'',
		'GOST':''
	}

	mac_map_etm = {
		'HMAC-MD5':'hmac-md5-etm@openssh.com',
		'UMAC-64':'umac-64-etm@openssh.com',
		'UMAC-128':'umac-128-etm@openssh.com',
		'HMAC-SHA1':'hmac-sha1-etm@openssh.com',
		'HMAC-SHA2-256':'hmac-sha2-256-etm@openssh.com',
		'HMAC-SHA2-512':'hmac-sha2-512-etm@openssh.com'
	}

	mac_map = {
		'HMAC-MD5':'hmac-md5',
		'UMAC-64':'umac-64@openssh.com',
		'UMAC-128':'umac-128@openssh.com',
		'HMAC-SHA1':'hmac-sha1',
		'HMAC-SHA2-256':'hmac-sha2-256',
		'HMAC-SHA2-512':'hmac-sha2-512'
	}

	kx_map = {
		'ECDHE-SECP521R1-SHA2-512':'ecdh-sha2-nistp521',
		'ECDHE-SECP256R1-SHA2-384':'ecdh-sha2-nistp384',
		'ECDHE-SECP256R1-SHA2-256':'ecdh-sha2-nistp256',
		'ECDHE-X25519-SHA2-256':'curve25519-sha256,curve25519-sha256@libssh.org',
		'DHE-FFDHE-1024-SHA1':'diffie-hellman-group1-sha1',
		'DHE-FFDHE-2048-SHA1':'diffie-hellman-group14-sha1',
		'DHE-FFDHE-2048-SHA2-256':'diffie-hellman-group14-sha256',
		'DHE-FFDHE-4096-SHA2-512':'diffie-hellman-group16-sha512',
		'DHE-FFDHE-8192-SHA2-512':'diffie-hellman-group18-sha512',
	}

	gx_map = {
		'DHE-SHA1':'diffie-hellman-group-exchange-sha1',
		'DHE-SHA2-256':'diffie-hellman-group-exchange-sha256',
	}

	sign_map = {
		'RSA-SHA1':'ssh-rsa',
		'DSA-SHA1':'ssh-dss',
		'RSA-SHA2-256':'rsa-sha2-256',
		'RSA-SHA2-512':'rsa-sha2-512',
		'ECDSA-SHA2-256':'ecdsa-sha2-nistp256',
		'ECDSA-SHA2-384':'ecdsa-sha2-nistp384',
		'ECDSA-SHA2-512':'ecdsa-sha2-nistp521',
		'EDDSA-ED25519':'ssh-ed25519',
	}

	sign_map_certs = {
		'RSA-SHA1':'ssh-rsa-cert-v01@openssh.com',
		'DSA-SHA1':'ssh-dss-cert-v01@openssh.com',
		'RSA-SHA2-256':'rsa-sha2-256-cert-v01@openssh.com',
		'RSA-SHA2-512':'rsa-sha2-512-cert-v01@openssh.com',
		'ECDSA-SHA2-256':'ecdsa-sha2-nistp256-cert-v01@openssh.com',
		'ECDSA-SHA2-384':'ecdsa-sha2-nistp384-cert-v01@openssh.com',
		'ECDSA-SHA2-512':'ecdsa-sha2-nistp521-cert-v01@openssh.com',
		'EDDSA-ED25519':'ssh-ed25519-cert-v01@openssh.com',
	}

	@classmethod
	def generate_options(cls, policy, local_kx_map, local_gss_hash_map, do_host_key):
		p = policy.props
		cfg = ''
		sep = ','

		s = ''
		for i in p['ssh_cipher']:
			try:
				s = cls.append(s, cls.cipher_map[i], sep)
			except KeyError:
				pass

		if s:
			cfg += cls._FORMAT_STRING.format('Ciphers', s)

		s = ''
		if p['ssh_etm'] == 1:
			for i in p['mac']:
				try:
					s = cls.append(s, cls.mac_map_etm[i], sep)
				except KeyError:
					pass
		for i in p['mac']:
			try:
				s = cls.append(s, cls.mac_map[i], sep)
			except KeyError:
				pass

		if s:
			cfg += cls._FORMAT_STRING.format('MACs', s)

		s = ''
		for i in p['hash']:
			try:
				s = cls.append(s, local_gss_hash_map[i], sep)
			except KeyError:
				pass

		if s:
			cfg += cls._FORMAT_STRING.format('GSSAPIKexAlgorithms', s)
		else:
			cfg += cls._FORMAT_STRING.format('GSSAPIKeyExchange', 'no')

		s = ''
		for kx in p['key_exchange']:
		    for h in p['hash']:
		        if p['arbitrary_dh_groups'] == 1:
		            try:
		                val = cls.gx_map[kx + '-' + h]
		                s = cls.append(s, val, sep)
		            except KeyError:
		                pass
		        for g in p['ssh_group']:
		            try:
		                val = local_kx_map[kx + '-' + g + '-' + h]
		                s = cls.append(s, val, sep)
		            except KeyError:
		                pass

		if s:
			cfg += cls._FORMAT_STRING.format('KexAlgorithms', s)

		s = ''
		for i in p['sign']:
			try:
				s = cls.append(s, cls.sign_map[i], sep)
			except KeyError:
				pass
			if p['ssh_certs'] == 1:
				try:
					s = cls.append(s, cls.sign_map_certs[i], sep)
				except KeyError:
					pass

		if s:
			# As OpenSSH currently ignores existing known host
			# entries with this setting we cannot use it on client.
			# Otherwise we could break existing users.
			if do_host_key:
				cfg += cls._FORMAT_STRING.format('HostKeyAlgorithms', s)
			cfg += cls._FORMAT_STRING.format('PubkeyAcceptedKeyTypes', s)

		s = ''
		for i in p['sign']:
			try:
				s = cls.append(s, cls.sign_map[i], sep)
			except KeyError:
				pass

		if s:
			cfg += cls._FORMAT_STRING.format('CASignatureAlgorithms', s)

		return cfg


class OpenSSHClientGenerator(OpenSSHGenerator):
	CONFIG_NAME = 'openssh'

	_FORMAT_STRING = '{0} {1}\n'

	@classmethod
	def generate_config(cls, policy):
		p = policy.props

		local_kx_map = dict(cls.kx_map)
		local_gss_hash_map = dict(cls.gss_hash_map)
		if p['min_dh_size'] <= 1024:
			local_gss_hash_map['SHA1'] = local_gss_hash_map['SHA1'] + ',gss-group1-sha1-'
		elif p['min_dh_size'] > 2048:
			local_gss_hash_map['SHA1'] = ''

		return cls.generate_options(policy, local_kx_map, local_gss_hash_map, False)

	@classmethod
	def test_config(cls, config):
		if not os.access('/usr/bin/ssh', os.X_OK):
			return True

		fd, path = mkstemp()

		try:
			with os.fdopen(fd, 'w') as f:
				f.write(config)
			try:
				call('/usr/bin/ssh -G -F ' + path +
					' bogus654_server >/dev/null 2>/dev/null',
					shell=True)
			except CalledProcessError:
				cls.eprint("There is an error in OpenSSH generated policy")
				cls.eprint("Policy:\n%s" % config)
				return False
		finally:
			os.unlink(path)

		return True

class OpenSSHServerGenerator(OpenSSHGenerator):
	CONFIG_NAME = 'opensshserver'

	# We need restart here, since systemd needs to pick up new command line options
	RELOAD_CMD = 'systemctl try-restart sshd.service 2>/dev/null || :\n'

	_FORMAT_STRING='-o{0}={1} '

	@classmethod
	def generate_config(cls, policy):
		p = policy.props

		# Difference from client, keep group1 disabled on server
		local_kx_map = dict(cls.kx_map)
		local_gss_hash_map = dict(cls.gss_hash_map)
		del local_kx_map['DHE-FFDHE-1024-SHA1']
		if p['min_dh_size'] > 2048:
			local_gss_hash_map['SHA1'] = ''

		cfg = cls.generate_options(policy, local_kx_map, local_gss_hash_map, True)
		cfg = cfg.rstrip()
		return 'CRYPTO_POLICY=\'' + cfg + '\''

	@classmethod
	def _test_setup(cls):
		fd, path = mkstemp()
		os.unlink(path)
		try:
			call('/usr/bin/ssh-keygen -t rsa -b 2048 -f ' + path +
				' -N "" >/dev/null',
				shell=True)
		except CalledProcessError:
			cls.eprint("SSH Keygen failed when testing OpenSSH server policy")
			return ''
		return path

	@classmethod
	def _test_cleanup(cls, path):
		if path:
			os.unlink(path)

	@classmethod
	def test_config(cls, config):
		if not os.access('/usr/sbin/sshd', os.X_OK):
			return True

		host_key_filename = cls._test_setup()
		if not host_key_filename:
			return False

		fd, path = mkstemp()

		try:
			with os.fdopen(fd, 'w') as f:
				f.write(config)
			try:
				call('/usr/bin/bash -c \'source ' + path +
				     ' && /usr/sbin/sshd -T $CRYPTO_POLICY -h ' +
				     host_key_filename +
				     ' -f /dev/null\' >/dev/null 2>/dev/null',
				     shell=True)
			except CalledProcessError:
				cls.eprint("There is an error in OpenSSH server generated policy")
				cls.eprint("Policy:\n%s" % config)
				return False
		finally:
			os.unlink(path)
			cls._test_cleanup(host_key_filename)

		return True
