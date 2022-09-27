#!/usr/bin/env python3

import argparse
import base64
import os
import segno
import subprocess
import sys
import yaml


class Config(object):
    has_changes = False

    def __init__(self, backend_file, server_config_filename, peer_config_directory):
        self.backend_file = backend_file
        self.server_config_filename = server_config_filename
        self.peer_config_directory = peer_config_directory
        self.read()
        if not self.data:
            self.init_server()
        self.check_peers()

    def init_server(self):
        privkey, pubkey = generate_key()
        self.data['server'] = {
            'dns': '8.8.8.8',
            'host': 'example.com',
            'keepalive': 25,
            'mtu': 1400,
            'port': 51820,
            'privkey': privkey,
            'pubkey': pubkey,
            'routes': '0.0.0.0/0',
            'tunnel_address': '10.0.0.1/32',
            'issuer': 'Acme Inc.',
        }
        self.data['peers'] = {}

    def read(self):
        try:
            with open(self.backend_file) as fd:
                self.data = yaml.safe_load(fd)
        except:
            self.data = {}

    def write(self):
        with open(self.backend_file, 'w') as fd:
            yaml.dump(self.data, fd, sort_keys=False)

    def check_peers(self):
        for username, peer in self.data['peers'].items():
            if not (peer.get('privkey') and peer.get('pubkey')):
                debug('Generating new keys for user:', username)
                privkey, pubkey = generate_key()
                peer['privkey'] = privkey
                peer['pubkey'] = pubkey
                self.has_changes = True

            if 'passphrase' in peer and not peer['passphrase']:
                debug('Generating new passphrase for user:', username)
                peer['passphrase'] = generate_passphrase()
                self.has_changes = True

    def add_peer(self, username, ip_address, totp):
        if username in self.data['peers']:
            error('Username already exists in peer list:', username)

        privkey, pubkey = generate_key()
        peer = {
            'ip_address': ip_address,
            'privkey': privkey,
            'pubkey': pubkey,
        }
        if totp:
            peer['passphrase'] = generate_passphrase()
        self.data['peers'][username] = peer
        self.write_peer_config(username, peer)
        self.has_changes = True

    def remove_peer(self, username):
        if username not in self.data['peers']:
            error('Username does not exist in peer list:', username)
        del(self.data['peers'][username])
        self.has_changes = True

    def write_server_config(self):
        config = '''[Interface]
                    Address = {tunnel_address}
                    PrivateKey = {privkey}
                 '''.format(**self.data['server'])

        for username, peer in self.data['peers'].items():
            tunnel_address = peer['ip_address']
            if not tunnel_address.endswith('/32'):
                tunnel_address += '/32'

            config += '''
                # {username}
                [Peer]
                AllowedIPs = {tunnel_address}
                PersistentKeepalive = {keepalive}
                PublicKey = {pubkey}
            '''.format(username=username, tunnel_address=tunnel_address,
                       keepalive=self.data['server']['keepalive'],
                       **peer)

            if 'passphrase' in peer:
                config += 'RequireToken = totp-sha1:{},digits=6,period=30,precision=15\n'.format(peer['passphrase'])

        config = strip_config(config)
        with open(self.server_config_filename, 'w') as fd:
            fd.write(config.strip())
            fd.write('\n')

    def write_peer_config(self, username, peer):
        issuer = self.data['server']['issuer']
        tunnel_address = peer['ip_address']
        if not tunnel_address.endswith('/32'):
            tunnel_address += '/32'

        # write config
        config = '''[Interface]
                    Address = {ip_address}
                    DNS = {dns}
                    MTU = {mtu}
                    PrivateKey = {peer_privkey}

                    [Peer]
                    AllowedIPs = {routes}
                    Endpoint = {host}:{port}
                    PersistentKeepalive = {keepalive}
                    PublicKey = {pubkey}
        '''.format(**self.data['server'],
                   ip_address=tunnel_address,
                   peer_privkey=peer['privkey'])
        config = strip_config(config)
        with open(os.path.join(self.peer_config_directory,
                               '{}-{}.conf'.format(issuer, username)), 'w') as fd:
            fd.write(config)

        # write qrcode
        if 'passphrase' in peer:
            qrcode = segno.make('otpauth://totp/{}?secret={}&issuer={}'.format(
                                username,
                                peer['passphrase'],
                                issuer,
                            )
            )
            qrcode.save(os.path.join(self.peer_config_directory,
                                     '{}-{}-totp.png'.format(issuer, username)),
                        scale=10)

    def write_peer_configs(self):
        for username, peer in self.data['peers'].items():
            self.write_peer_config(username, peer)

DEBUG = False

def debug(*message):
    if DEBUG:
        print('DEBUG:', *message)


def error(*message):
    print(*message)
    sys.exit(1)


def generate_key():
    try:
        privkey = subprocess.run(['wg', 'genkey'], stdout=subprocess.PIPE).stdout
        pubkey = subprocess.run(['wg', 'pubkey'], input=privkey, stdout=subprocess.PIPE).stdout
        return privkey.decode('ascii').strip(), pubkey.decode('ascii').strip()
    except FileNotFoundError as e:
        if e.filename == 'wg':
            error('wg tool is not installed.')


def generate_passphrase():
    return base64.b32encode(open('/dev/random', 'rb').read(20)).decode('ascii')


def strip_config(config):
    return '\n'.join([line.strip() for line in config.split('\n')])


def parse_arguments():
    """Get commandline arguments."""
    parser = argparse.ArgumentParser(
        description='Create tunsafe peer and update server config')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--add-peer', '-a', action='store_true',
                        help='Add a new peer')
    group.add_argument('--remove-peer', '-r', action='store_true',
                        help='Remove an existing peer')
    group.add_argument('--write-peer-configs', action='store_true',
                        help='Create peer config files from backend file')
    group.add_argument('--write-server-config', action='store_true',
                        help='Create server config file from backend file')
    parser.add_argument('--username', '-u',
                        help='Username to annotate peer')
    parser.add_argument('--ip-address', '-i',
                        help='IP address for the new peer')
    parser.add_argument('--totp', '-t', action='store_true',
                        help='Generate secret for TOTP 2-factor-authentication')
    parser.add_argument('--backend-file', default='/etc/128technology/tunsafe/tunsafe-backend.yaml',
                        help='Load sessions from file for testing')
    parser.add_argument('--server-config-filename', default='/etc/128technology/tunsafe/tunsafe1.conf',
                        help='Tunsafe config filename')
    parser.add_argument('--peer-config-directory', default='/tmp/tunsafe/',
                        help='Tunsafe peer config directory')
    parser.add_argument('--num-rand-bytes', type=int, default=20,
                        help='Number of random bytes')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Print debug messages')

    return parser.parse_args()


def read_config(filename):
    try:
        with open(filename) as fd:
            config = yaml.safe_load(fd)
            return config
    except:
        return {}


def main():
    args = parse_arguments()
    global RAND_BYTES
    RAND_BYTES = args.num_rand_bytes
    global DEBUG
    DEBUG = args.debug

    config = Config(args.backend_file,
                    args.server_config_filename,
                    args.peer_config_directory)

    if args.add_peer or args.remove_peer:
        if not args.username:
            error('Username is required for add/remove operation!')
        if args.add_peer:
            if not args.ip_address:
                error('IP address for new peer is required!')
            config.add_peer(args.username, args.ip_address, args.totp)
        if args.remove_peer:
            config.remove_peer(args.username)
        config.write_server_config()

    if args.write_peer_configs:
        config.write_peer_configs()

    if args.write_server_config:
        config.write_server_config()

    if config.has_changes:
        config.write()


if __name__ == '__main__':
    main()
