#!/usr/bin/env python2
# Author: txp0wer <txp0wer@noreply.users.github.com>
# License: MIT

import netifaces
import socket
import struct

def get_addrs(protocol=netifaces.AF_INET6,if_prefix="ew"):
    # Get list of network interfaces
    ifaces = netifaces.interfaces()
    # Get addresses for each interface
    if_addrs = [(netifaces.ifaddresses(iface), iface) for iface in ifaces]
    # Filter for only IPv4 addresses
    if_inet_addrs = [(tup[0][protocol], tup[1]) for tup in if_addrs if protocol in tup[0]]
    # get addresses
    iface_addrs = [(s['addr'], tup[1]) for tup in if_inet_addrs for s in tup[0] if 'addr' in s]
    return [ x[0] for x in iface_addrs if x[1][0] in if_prefix ]

def mcast_socket(maddrs,port,host="::"):
    sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, 1)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, 128)
    haddr = socket.getaddrinfo(host, port, socket.AF_INET6, socket.SOCK_DGRAM)[0][-1]
    for addr in maddrs:
        mcast_join(sock,addr)
    sock.bind(haddr)
    sock.setblocking(False)
    return sock

def mcast_join(sock,addr):
    haddr=sock.getsockname()
    port=haddr[2]
    ifn= haddr[3]
    ifn = struct.pack("I", ifn)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF, ifn)
    maddr = socket.getaddrinfo(addr, port, socket.AF_INET6, socket.SOCK_DGRAM)[0][-1]
    # get a suitable interface
    # join the mcast group
    group = socket.inet_pton(socket.AF_INET6, maddr[0]) + ifn
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, group)

def mcast_leave(sock,addr):
    haddr=sock.getsockname()
    port=haddr[2]
    ifn= haddr[3]
    ifn = struct.pack("I", ifn)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF, ifn)
    maddr = socket.getaddrinfo(addr, port, socket.AF_INET6, socket.SOCK_DGRAM)[0][-1]
    # get a suitable interface
    # join the mcast group
    group = socket.inet_pton(socket.AF_INET6, maddr[0]) + ifn
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_LEAVE_GROUP, group)


def send_packet(sockets,addrs,port,data):
    for s in sockets:
        for a in addrs:
            s.sendto(a,port,data)
