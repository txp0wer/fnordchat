#!/usr/bin/env python2
# Author: txp0wer <txp0wer@users.github.com>
# License: GNU GPLv3

import sys,os,fnordchat;

prefix=os.getenv("ADDR_PREFIX") or "ff08"

import sys
import fnordchat;
c=fnordchat.chat(sys.argv[2:],prefix=prefix,nick=sys.argv[1])
l=sys.stdin.readline()[0:-1]
while not c.shutdown:
    try:
        if len(l):
            if l[0]=="/":
                cmd=l[1:].split(" ")
                if cmd[0]=="me":
                    c.talk(" ".join(cmd[1:]),method="me")
                elif cmd[0]=="join":
                    for channel in cmd[1:]:
                        c.join(channel)
                elif cmd[0]=="part":
                    for channel in cmd[1:]:
                        c.part(channel)
                elif cmd[0]=="nick":
                    c.send_nick(nick=cmd[1])
                elif cmd[0]=="msg":
                    try:
                        c.talk(" ".join(cmd[2:]),method="notice",channels=[],peers=[cmd[1]])
                    except:
                        pass
                elif cmd[0]=="quit":
                    c.shutdown=True
                elif cmd[0]=="ping":
                    c.ping(cmd[1])
                else:
                    print "unknown command /"+cmd[0]
            else:
                c.talk(l)
    except:
        c.shutdown=True
    try:
        l=sys.stdin.readline()[0:-1]
    except:
        c.shutdown=True


