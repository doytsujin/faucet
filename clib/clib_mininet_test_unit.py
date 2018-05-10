"""Mininet tests for clib."""

# pylint: disable=missing-docstring
# pylint: disable=too-many-arguments

import os
import re
import time

from mininet.net import Mininet

import mininet_test_base
import mininet_test_util
import mininet_test_topo

from tcpdump_helper import TcpdumpHelper
from docker_host import MakeDockerHost

class FaucetSimpleTest(mininet_test_base.FaucetTestBase):
    """Basic untagged VLAN test."""

    N_UNTAGGED = 4
    CONFIG_GLOBAL = """
vlans:
    100:
        description: "untagged"
"""

    CONFIG = """
        interface_ranges:
            1-4:
                native_vlan: 100
"""

    def setUp(self):
        super(FaucetSimpleTest, self).setUp()
        self.topo = self.topo_class(
            self.OVS_TYPE, self.ports_sock, self._test_name(), [self.dpid],
            n_tagged=self.N_TAGGED, n_untagged=self.N_UNTAGGED,
            n_extended=self.N_EXTENDED, e_cls=self.EXTENDED_CLS,
            tmpdir=self.tmpdir, links_per_host=self.LINKS_PER_HOST)
        self.start_net()

    def test_ping_all(self):
        """All hosts should have connectivity."""
        self.ping_all_when_learned()


class FaucetTcpdumpHelperTest(FaucetSimpleTest):
    """Test for TcpdumpHelper class"""

    def test_tcpdump_execute(self):
        """Check tcpdump filter monitors ping using execute"""
        self.ping_all_when_learned()
        from_host = self.net.hosts[0]
        to_host = self.net.hosts[1]
        tcpdump_filter = ('icmp')
        tcpdump_helper = TcpdumpHelper(to_host, tcpdump_filter, [
                lambda: from_host.cmd('ping -c1 %s' % to_host.IP())])
        tcpdump_txt = tcpdump_helper.execute()
        self.assertTrue(re.search(
            '%s: ICMP echo request' % to_host.IP(), tcpdump_txt))


class FaucetDockerHostTest(FaucetSimpleTest):

    N_UNTAGGED=2
    N_EXTENDED=2
    EXTENDED_CLS=MakeDockerHost('faucet/test-host')

    def test_containers(self):
        """Test containers to make sure they're actually docker."""
        count=0
        host_name = None

        for host in self.net.hosts:
            marker = host.cmd('cat /root/test_marker.txt').strip()
            if marker == 'faucet-test-host':
                host_name = host.name
                count = count + 1
                host.activate()
                host.wait()

        self.assertTrue(count == self.N_EXTENDED,
            'Found %d containers, expected %d' % (count, self.N_EXTENDED))

        self.assertTrue(os.path.exists(os.path.join(self.tmpdir, host_name, 'tmp')),
            'container tmp dir missing')

        host_log = os.path.join(self.tmpdir, host_name, 'activate.log')
        with open(host_log, 'r') as host_log_file:
            lines = host_log_file.readlines()
            output = ' '.join(lines).strip()
            self.assertEqual(output, 'hello faucet')
