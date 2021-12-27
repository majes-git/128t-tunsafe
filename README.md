# 128t-tunsafe
Tunsafe and scripts to be used with 128T (Session Smart Router)

## Installation

```
$ unzip 128t-tunsafe-main.zip
$ cd 128t-tunsafe-main
$ sudo bash install.bash
```

## 128T/SSR Config

```
config
    authority
        tenant   corp
        exit
        tenant   vpn.corp
        exit
        tenant   netadmin.vpn.corp
        exit

        service  intranet
            address               10.0.0.0/8
            address               172.16.0.0/12
            address               192.168.0.0/16
            share-service-routes  false
        exit

        service  testclient.intranet
            name                  testclient.intranet
            address               172.16.1.1
            access-policy         netadmin.vpn.corp
            exit
            share-service-routes  false
        exit

        service  tunsafe1-endpoint
            name                  tunsafe1-endpoint
            scope                 public

            transport             udp
                port-range  51820
                exit
            exit
            address               100.100.128.128
            share-service-routes  false
        exit

        router   tunsafe-router
            node           node1
                device-interface  tunsafe1
                    type               host
                    network-namespace  tunsafe1
                    network-interface  tunsafe1
                        name             tunsafe1
                        tenant-prefixes  netadmin.vpn.corp
                            source-address  10.0.0.11/32
                        exit
                        address          169.254.141.1
                            prefix-length  30
                            gateway        169.254.141.2
                        exit
                    exit
                exit
            exit

            service-route  tunsafe1-endpoint
                service-name  tunsafe1-endpoint
                nat-target    169.254.141.2
                next-hop      node1 tunsafe1
                exit
            exit
        exit
    exit
exit
```
