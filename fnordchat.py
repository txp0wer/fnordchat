#!/usr/bin/env python2
# Author: txp0wer <txp0wer@noreply.users.github.com>
# License: GNU GPLv3 or later

from hashlib import sha512
from fnordnet import mcast_socket,mcast_leave,mcast_join
import time,select,threading

TALK_NORMAL='\x01'
TALK_ME='\x02'
TALK_NOTICE='\x03'

TALK_CMD={
    "NORMAL":'\x01',
    "ME":'\x02',
    "NOTICE":'\x03'
}

OPCODES={
    '\x00':"KEEPALIVE",
    '\x01':"HI", # JOIN
    '\x02':"PING",
    '\x03':"PONG",
    '\x04':"TALK",
    '\x05':"ACK",
    '\x06':"NICK", # set nick
    '\x07':"BYE", # PART
    '\x08':"NUDGE",
    '\x09':"BLOCK", # signal the peer that we're ignoring their messages
    '\x0a':"UNBLOCK", # signal the peer that we're no longer ignoring their messages
    '\x0b':"COMPOSING", # signal that we're working on a message (max once per minute)
    '\x0c':"AWAY",
    '\x0d':"BACK",
    '\x0e':"QUERY",
    '\x0f':"EXTENDED"
}

SUBCODES={
    '\x00':{},
    '\x01':{},
    '\x02':{},
    '\x03':{},
    '\x04':{'\x01':'NORMAL','\x02':'ME','\x03':'NOTICE'},
    '\x05':{},
    '\x06':{},
    '\x07':{},
    '\x08':{},
    '\x09':{},
    '\x0a':{},
    '\x0b':{},
    '\x0c':{},
    '\x0d':{},
    '\x0e':{},
    '\x0f':{'\x01':'RELAY','\x02':'BINARY'}
}

def build_packet(opcode,subcode,data):
    timestamp=time.time()
    packet=("%016x"%int(timestamp)).decode("hex")
    packet+=("%04x"%int((timestamp%1)*0x10000)).decode("hex")
    packet+=opcode+subcode
    packet+=data;
    return packet

class chat:
    def __init__(self,channels,port=0xccc,prefix='ff08',nick="",default_handlers=True,listen=True):
        assert(type(port)==int)
        assert(type(nick)==bytes)
        assert(type(channels)==list)
        assert(type(prefix)==bytes)
        self.port=port
        self.channels={} # name->mcast_ip
        self.peers={} # ip->nick
        self.peers_inv={} # nick->ip
        self.handlers={}
        for opcode in OPCODES.keys():
            self.handlers[OPCODES[opcode].lower()]=set()
        self.prefix=prefix
        self.nick=nick
        self.socket=mcast_socket([],port)
        self.shutdown=False
        self.redundancy=1
        self.lru_capacity=1024
        self.pings={}
        self.recent_packets={}
        if default_handlers:
            self.add_default_handlers()
        if listen:
            self.listen()
        for c in channels:
            assert(type(c)==bytes)
            self.join(c)

    def add_default_handlers(self):
        self.add_handler("nick",self.default_nick_handler)
        self.add_handler("ping",self.default_ping_handler)
        self.add_handler("query",self.default_query_handler)
        for x in self.handlers.keys():
            self.add_handler(x,self.print_event(x))

    def talk(self,text,method="NORMAL",channels=None,peers=[]):
        self.send('\x04',TALK_CMD[method.upper()],text,channels=channels,peers=peers)

    def get_peer_addrs(self,peers=[]):
        if type(peers)==bytes:
            peers=[peers]
        assert(type(peers)==list)
        return [(self.peers_inv[n] if n in self.peers_inv.keys() else n) for n in peers]

    def send_nick(self,nick=None,channels=None,peers=None):
        if nick==None:
            nick=self.nick
        self.nick=nick;
        self.send('\x06','\x00',nick,channels,peers)

    def query(self,term,channels=None,peers=None):
        self.send('\x0e','\x00',term,channels,peers)

    def ping(self,channels=None,peers=None):
        echo_data=str(time.time())
        self.send('\x02','\x00',echo_data,channels=channels,peers=peers)

    def send(self,opcode,subcode,data,channels=None,peers=[]):
        if channels==None:
            channels=self.channels.keys()
        if peers==None:
            peers=self.peers.keys()
        targets=[
            self.channels[c] for c in channels if c in self.channels.keys()
        ]+self.get_peer_addrs(peers)
        p=build_packet(opcode,subcode,data)
        for t in targets:
            for i in range(0,self.redundancy):
                try:
                    self.socket.sendto(p,(t,self.port))
                except:
                    print "can't send to "+t

    def join(self,channel,interface="",query=True):
        if not (channel in self.channels.keys()):
            binary_addr=self.prefix+sha512(sha512(channel).digest()).digest()[0:14].encode("hex").lower()
            mcast_addr=(lambda x:":".join([
                x[0:4],x[4:8],x[8:12],x[12:16],
                x[16:20],x[20:24],x[24:28],x[28:32]
            ]))(binary_addr)+("%"+interface if len(interface) else "")
            self.channels[channel]=mcast_addr
            mcast_join(self.socket,mcast_addr)
            # send HI
            self.send('\x01','\x00','',channels=[channel])
            # send NICK
            self.send_nick(channels=[channel])
            # ask others about their nicks
            if query:
                self.query("",channels=[channel])

    def part(self,channel):
        if channel in self.channels.keys():
            mcast_addr=self.channels.pop(channel)
            # send "BYE"
            self.send('\x07','\x00','',channels=[],peers=[mcast_addr])
            # leave multicast
            mcast_leave(self.socket,mcast_addr)

    def get_nick(self,addr,alt=None):
        if addr in self.peers.keys():
            return self.peers[addr]
        else:
            return alt

    def get_packet(self):
        if select.select([self.socket],[],[],1)[0]:
            dgram=self.socket.recvfrom(2**16+12)
            data=dgram[0]
            addr=dgram[1][0]
            if len(data)<12:
                return None
            timestamp=data[0:10].encode("hex")
            dgram_hash=sha512(addr+data).digest()[0:8]
            # check if we've seen this packet before
            if dgram_hash in self.recent_packets.keys():
                return None
            # no? then let's remember it
            self.recent_packets[dgram_hash]=time.time();
            # avoid memleaks
            if len(self.recent_packets)>self.lru_capacity:
                self.recent_packets={} # TODO implement real LRU
            timestamp=int(timestamp[0:16],base=16)+(int(timestamp[16:20],base=16)*1.0/2**16)
            n=self.get_nick(addr,alt=None)
            payload=data[10:]
            if payload[0] in OPCODES.keys():
                event=OPCODES[payload[0]].lower()
                method=None
                if payload[1] in SUBCODES[payload[0]].keys():
                    method=SUBCODES[payload[0]][payload[1]].lower()
                if event in self.handlers.keys():
                    for f in list(self.handlers[event]):
                        f(timestamp,n,addr,method,payload[2:])
            return (addr,timestamp,payload)
        else:
            return None

    def add_handler(self,event,function):
        try:
            self.handlers[event.lower()].add(function)
            return True
        except:
            return False

    def listen(self):
        def thread_function():
            while not self.shutdown:
                self.get_packet()
        self.handler_thread=threading.Thread(None,thread_function)
        self.handler_thread.start()

    def print_event(self,event):
        def out(timestamp,nick,addr,method,payload):
            print timestamp,nick,addr,event,method,payload
        return out

    def default_nick_handler(self,timestamp,old_nick,addr,unused,new_nick):
        if not ":" in new_nick: # safeguard against address spoofing
            self.peers[addr]=new_nick
            self.peers_inv[new_nick]=addr

    def default_query_handler(self,timestamp,nick,addr,unused,requested_nick):
        if requested_nick in self.nick:
            self.send_nick(channels=[],peers=[addr])

    def default_ping_handler(self,timestamp,nick,addr,unused_1,ping_data):
        self.send('\x03','\x00',ping_data,channels=[],peers=[addr])
