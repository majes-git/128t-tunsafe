#!/bin/bash

CONFIG_FILE=/etc/128technology/tunsafe/tunsafe1.conf
NEW_HEADER=$(mktemp)
NEW_PEERS=$(mktemp)

if [ ! -e $CONFIG_FILE ]; then
    echo "ERROR: Config file $CONFIG_FILE does not exits."
    exit 1
fi

sed -n '1,/^$/p' $CONFIG_FILE > $NEW_HEADER
awk -F';' '{ print "# "$1"\n[Peer]\nAllowedIPs = "$2"/32\nPublicKey = "$3"\nRequireToken = totp-sha1:"$4",digits=6,period=30,precision=15\n" }' > $NEW_PEERS
# if peers
if [ $(wc -l < $NEW_PEERS) -ne 0 ]; then
    echo "INFO: Creating new config"
    cat $NEW_HEADER $NEW_PEERS > $CONFIG_FILE
fi
rm -f $NEW_HEADER $NEW_PEERS
systemctl restart 128t-tunsafe@tunsafe1
