#!/usr/bin/python3

# SPDX-License-Identifier: LGPL-2.1-or-later

# Copyright (c) 2019 Red Hat, Inc.
# Copyright (c) 2019 Tomáš Mráz <tmraz@fedoraproject.org>

import sys
import argparse
import re
import os
import subprocess
from tempfile import mkstemp

import cryptopolicies
from cryptopolicies.cryptopolicies import eprint

import policygenerators


try:
	profile_dir = os.environ['profile_dir']
	cryptopolicies.CryptoPolicy.SHARE_DIR = profile_dir
except KeyError:
	profile_dir = '/usr/share/crypto-policies'

try:
	base_dir = os.environ['base_dir']
	cryptopolicies.CryptoPolicy.CONFIG_DIR = base_dir
except KeyError:
	base_dir = '/etc/crypto-policies'

local_dir = base_dir + '/local.d'
backend_config_dir = base_dir + '/back-ends'
state_dir = base_dir + '/state'

reload_cmd_name = 'reload-cmds.sh'
reload_cmd_path = profile_dir + '/' + reload_cmd_name


def parse_args():
	"Parse the command line"
	parser = argparse.ArgumentParser(allow_abbrev=False)
	group = parser.add_mutually_exclusive_group()
	group.add_argument('--set', nargs='?', default='', metavar='POLICY',
		help='set the policy POLICY')
	group.add_argument('--show', action='store_true',
		help='show the current policy from the configuration')
	group.add_argument('--is-applied', action='store_true',
		help='check whether the current policy is applied')
	parser.add_argument('--no-check', action='store_true',
		help=argparse.SUPPRESS)
	parser.add_argument('--no-reload', action='store_true',
		help='do not run the reload scripts when setting a policy')
	return parser.parse_args()


def is_applied():
	try:
		time1 = os.stat(state_dir + '/current').st_mtime
		time2 = os.stat(base_dir + '/config').st_mtime
	except:
		sys.exit(77)

	if time1 >= time2:
		print("The configured policy is applied")
		sys.exit(0)
	print("The configured policy is NOT applied")
	sys.exit(1)


def setup_directories():
	try:
		os.makedirs(backend_config_dir)
		os.makedirs(state_dir)
	except:
		pass


def fips_mode():
	try:
		with open('/proc/sys/crypto/fips_enabled') as f:
			return int(f.read()) > 0
	except:
		return False


def safe_write(directory, filename, contents):
	(fd, path) = mkstemp(prefix = filename, dir = directory)
	os.write(fd, bytes(contents, 'utf-8'))
	os.fsync(fd)
	os.fchmod(fd, 0o644)
	try:
		os.rename(path, directory + '/' + filename)
	except OSerror as e:
		os.unlink(path)
		os.close(fd)
		raise e
	finally:
		os.close(fd)


def safe_symlink(directory, filename, target):
	(fd, path) = mkstemp(prefix = filename, dir = directory)
	os.close(fd)
	os.unlink(path)
	os.symlink(target, path)
	try:
		os.rename(path, directory + '/' + filename)
	except OSerror as e:
		os.unlink(path)
		raise e


def save_config(pconfig, cfgname, cfgdata, cfgdir, localdir, profiledir):
	# This is not fully safe but not worse than original shell script
	try:
		output = subprocess.check_output('ls ' + local_dir + '/' + cfgname +
			 '-*.config 2>/dev/null', shell=True)
		local_cfg = True
	except subprocess.CalledProcessError:
		local_cfg = False

	profilepath = profiledir + '/' + str(pconfig) + '/' + cfgname + '.txt'

	if not local_cfg and os.access(profilepath, os.R_OK):
		safe_symlink(cfgdir, cfgname + '.config', profilepath)
		return

	safe_write(cfgdir, cfgname + '.config', cfgdata)

	if local_cfg:
		try:
			subprocess.call('cat ' + local_dir + '/' + cfgname + '-*.config >> ' +
				cfgdir + '/' + cfgname + '.config', shell=True)
		except subprocess.CalledProcessError:
			eprint("Error applying local configuration to " + cfgname)


class ProfileConfig:
	def __init__(self):
		self.policy = ''
		self.subpolicies = []

	def parse_string(self, s, subpolicy = False):
		l = s.upper().split(':')
		if l[0] and not subpolicy:
			self.policy = l[0]
			l = l[1:]
		l = [i for i in l if l]
		if subpolicy:
			self.subpolicies.append(l)
		else:
			self.subpolicies = l

	def parse_file(self, filename):
		subpolicy = False
		with open(filename) as f:
			for line in f:
				line = line.split('#', 1)[0]
				line = line.strip()
				if line:
					self.parse_string(line, subpolicy)
					subpolicy = True

	def remove_subpolicies(self, s):
		l = s.upper().split(':')
		self.subpolicies = [i for i in self.subpolicies if not i in l]

	def __str__(self):
		s = self.policy
		subs = ':'.join(self.subpolicies)
		if subs:
			s = s + ':' + subs
		return s

	def show(self):
		print(str(self))


def main():
	"The actual command implementation"
	cmdline = parse_args()

	if cmdline.is_applied:
		is_applied()
		sys.exit(0)

	err = 0

	setup_directories()

	pconfig = ProfileConfig()

	set_config = False

	configfile = base_dir + '/config'
	if os.access(configfile, os.R_OK):
		pconfig.parse_file(configfile)
	else:
		pconfig.parse_file(profile_dir + '/default-config')

	if cmdline.show:
		pconfig.show()
		sys.exit(0)

	profile = cmdline.set

	if profile:
		oldpolicy = pconfig.policy
		pconfig.parse_string(profile)
		set_config = True

		# FIPS profile is a special case
		if pconfig.policy != oldpolicy:
			if pconfig.policy == 'FIPS':
				eprint("Warning: Using 'update-crypto-policies --set FIPS' is not sufficient for")
				eprint("         FIPS compliance.")
				eprint("         Use 'fips-mode-setup --enable' command instead.")
			elif fips_mode():
				eprint("Warning: Using 'update-crypto-policies --set' in FIPS mode will make the system")
				eprint("         non-compliant with FIPS.")
				eprint("         It can also break the ssh access to the system.")
				eprint("         Use 'fips-mode-setup --disable' to disable the system FIPS mode.")

	cp = cryptopolicies.CryptoPolicy()

	try:
		cp.load_policy(pconfig.policy)
		cp.load_subpolicies(pconfig.subpolicies)
	except ValueError as e:
		eprint('Error: ' + str(e))
		sys.exit(1)

	if cp.errors:
		eprint('Errors found in policy')
		sys.exit(1)

	cp.finalize()

	print("Setting system policy to " + str(pconfig))

	generators = [g for g in dir(policygenerators) if 'Generator' in g]

	for g in generators:
		cls = policygenerators.__dict__[g]
		gen = cls()
		try:
			config = gen.generate_config(cp)
		except:
			eprint('Error generating config for ' + gen.CONFIG_NAME)
			eprint('Keeping original configuration')
			err = 1

		try:
			save_config(pconfig, gen.CONFIG_NAME, config,
				    backend_config_dir, local_dir, profile_dir)
		except:
			eprint('Error saving config for ' + gen.CONFIG_NAME)
			eprint('Keeping original configuration')
			err = 1

	if set_config:
		try:
			safe_write(base_dir, 'config', str(pconfig) + '\n')
		except:
			eprint('Error setting the current policy configuration')
			err = 3

	try:
		safe_write(state_dir, 'current', str(pconfig) + '\n')
	except:
		eprint('Error updating current policy marker')
		err = 2

	print("Note: System-wide crypto policies are applied on application start-up.")
	print("It is recommended to restart the system for the change of policies")
	print("to fully take place.")

	if not cmdline.no_reload:
		subprocess.call(['/bin/bash', reload_cmd_path])

	sys.exit(err)

# Entry point
if __name__ == "__main__":
        main()
