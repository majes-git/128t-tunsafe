#!/bin/bash

NS_DIR=/etc/128technology/plugins/network-scripts/host/tunsafe1/
mkdir $NS_DIR
cp init monitoring $NS_DIR
chmod 755 $NS_DIR/*
ln -s init $NS_DIR/reinit
cp tunsafe /usr/local/sbin/

mkdir /etc/128technology/tunsafe/
CONFIG=/etc/128technology/tunsafe/tunsafe1.conf
if [ ! -e $CONFIG ]; then
    {
        echo "[Interface]"
        echo "PrivateKey = $(/usr/local/sbin/tunsafe genkey)"
        echo "Address = 10.0.0.1/32"
        echo "ListenPort = 51820"
    } > /etc/128technology/tunsafe/tunsafe1.conf
fi

cp 128t-tunsafe@.service /usr/lib/systemd/system/
systemctl daemon-reload
