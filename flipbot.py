#!/usr/bin/env python2
# Author: txp0wer (github.com/txp0wer)
# License: GNU GPLv3

import sys,os,fnordchat;

prefix=os.getenv("ADDR_PREFIX") or "ff08"

c=fnordchat.chat(["darkfasel#ccc"],prefix=prefix,nick="flipbot")
def talk_handler(timestamp,nick,addr,method,text):
    if method=="normal" and "alarm" in text:
        message=nick+": "+text
        c.talk("flipped to: "+message,method="me")
        # do something with text
c.add_handler("talk",talk_handler)
