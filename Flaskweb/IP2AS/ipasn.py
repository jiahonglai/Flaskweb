#!/usr/bin/env python
import radix


class IP2AS():

    def __init__(self, v4_path=None, v6_path=None):
        '''
            @v4_path: path to routeviews IP2ASN dataset for v4 prefixes
            @v6_path: path to routeviews IP2ASN dataset for v6 prefixes
        '''
        self.private_address_space = radix.Radix()
        self.private_address_space.add('10.0.0.0', 8)
        self.private_address_space.add('100.64.0.0', 10)
        self.private_address_space.add('172.16.0.0', 12)
        self.private_address_space.add('192.0.0.0', 24)
        self.private_address_space.add('192.168.0.0', 16)
        self.private_address_space.add('198.18.0.0', 15)

        self.private_address_space.add('::1', 128)
        self.private_address_space.add('fc00::', 7)
        self.private_address_space.add('fe80::', 10)
        self.private_address_space.add('2001:db8::', 32)

        self.radix_tree = radix.Radix()
        if v4_path:
            with open(v4_path) as fp:
                for line in fp:
                    prefix, prefix_len, ases = line.strip().split()
                    if self.private_address_space.search_best(prefix) is None:
                        node = self.radix_tree.add(prefix, int(prefix_len))
                        node.data['data'] = [
                            int(asn)
                            for asn in ases.replace(',', '_').split('_')
                        ]

        if v6_path:
            with open(v6_path) as fp:
                for line in fp:
                    prefix, prefix_len, ases = line.strip().split()
                    if self.private_address_space.search_best(prefix) is None:
                        node = self.radix_tree.add(prefix, int(prefix_len))
                        node.data['data'] = [
                            int(asn)
                            for asn in ases.replace(',', '_').split('_')
                        ]

    def getASNum(self, ip):
        '''
            return ASN if we have a matching prefix, otherwise 0 is returned
        '''
        if len(ip):
            # Best-match search will return the longest matching prefix
            node = self.radix_tree.search_best(ip)
            if node:
                return min(node.data['data'])
        return 0

    def isPrivate(self, ip):
        '''
            check if the given address belongs to the reserved address ranges
        '''
        if self.private_address_space.search_best(ip) is None:
            return False
        return True
