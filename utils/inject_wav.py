#!/usr/bin/env python

from optparse import OptionParser

import unirest
import json
import time

parser = OptionParser(usage="%prog: [options]")

parser.add_option("-t", "--talkgroup", help="Talkgroup to inject", type=int, default=None)
parser.add_option("-w", "--wav", help="Wavefile to inject")
parser.add_option("-d", "--delay", help="Delay between the two", default=0.0, type=float)
parser.add_option("-f", "--flip", help="Send the wav before the talkgroup entry", default=False, action="store_true")
parser.add_option("-u", "--url", help="Base URL to submit to")

(options, args) = parser.parse_args()

def _submit(options, msg):
    url = "%s/json/%s" % (options.url, json.dumps(msg))
    unirest.get(url, callback=lambda s: "Isn't that nice.")
    

def do_tgfile(options):
    if None == options.talkgroup:
        return

    _submit(options,
            {"type": "tgfile",
             "tg": options.talkgroup,
             "path": options.wav})
    

def do_wav(options):
    if None == options.wav:
        return
    _submit(options,
            {"type": "fileup",
             "path": options.wav})

def do_step(options, stepno):
    if (stepno == 1) ^ options.flip:
        do_wav(options)
    else:
        do_tgfile(options)
    

do_step(options, 0)
time.sleep(options.delay)
do_step(options, 1)
