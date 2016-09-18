#!/usr/bin/env python

# Audio extraction/split functionality
#
# Creates directories full of wav files containing 8b/8kHz audio of
# all channels monitored.  Accepts a list of frequencies via a file,
# or will just do all channels in the sample passband.
#
# Copyright (c) 2016 Josh Myer <josh@joshisanerd.com>
# License: GPL v2
#
# This is a fairly decent multi-channel audio recorder / "scanner" in
# GNURadio.  It currently only works with RTL-SDR dongles using
# osmocom's SDR bindings, but wouldn't be too hard to adapt to other
# input modules.
#
# This is mostly an overgrown Proof-of-Concept, and it could use some
# serious refactoring and polish.  For now, the key thing is that it
# works, at least here in San Francisco.
#
# It assumes all channesl are FM audio. If you need to add P25 or some
# other decoding, you can do it downstream of each channel's squelch.


import sys
import os.path
sys.path.append(os.path.dirname(__file__) + "/../lib")

import errno

from gnuradio import blocks
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from gnuradio.filter import pfb
from optparse import OptionParser

from indri.config import IndriConfig

from indri.recording_channelizer import recording_channelizer

import osmosdr
import time
import os

import json

NCORES = 4

class indri_osmocom(gr.top_block):
    def __init__(self, config):
        gr.top_block.__init__(self, "Splitter")

        self.config = config
        self.Fc = config["scanner"]["Fc"]
        self.samp_rate = config["scanner"]["Fs"]
        self.freq_offset = 0.0
        self.freq_corr = config["scanner"]["receiver"]["freq_corr"]
        self.gain = config["scanner"]["receiver"]["gain"]
        self.gain_if = 0
        self.gain_bb = 0

        # Set up the RTL-SDR source
        osmosdr_h = osmosdr.source( args="numchan=" + str(1) + " " + "" )

        if not osmosdr_h.get_gain_range().values():
            print "Looks like the RTL-SDR couldn't be opened, bailing"
            sys.exit(1)

        osmosdr_h.set_sample_rate(self.samp_rate)
        osmosdr_h.set_center_freq(self.Fc+self.freq_offset, 0)
        osmosdr_h.set_freq_corr(self.freq_corr, 0)
        osmosdr_h.set_dc_offset_mode(0, 0)
        osmosdr_h.set_iq_balance_mode(0, 0)
        osmosdr_h.set_gain_mode(config["scanner"]["receiver"]["gain_mode"], 0)
        osmosdr_h.set_gain(self.gain, 0)
        osmosdr_h.set_if_gain(self.gain_if, 0)
        osmosdr_h.set_bb_gain(self.gain_bb, 0)
        osmosdr_h.set_antenna("", 0)
        osmosdr_h.set_bandwidth(0, 0)

        self.osmosdr_h = osmosdr_h


        self.channelizer = recording_channelizer(config, self.tune_offset_cb)
        self.connect(osmosdr_h, self.channelizer)

    def tune_offset_cb(self, freq_offset):
        self.freq_offset = freq_offset
        self.osmosdr_h.set_center_freq(self.Fc + self.freq_offset, 0)
        

if __name__ == '__main__':
    parser = OptionParser(option_class=eng_option, usage="%prog: [options]")
    parser.add_option("-c", "--config", help="File containing config file")

    (options, args) = parser.parse_args()

    if not options.config:
        print "Need a config file, -c indri.json"
        sys.exit(1)


    config = IndriConfig(options.config)

    for dir_key in ["tmp_dir", "out_dir", "control_log_tmp_dir", "control_log_dir"]:
        try:
            if dir_key in config["scanner"]:
                os.makedirs(config["scanner"][dir_key])
        except OSError, e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise e

    tb = indri_osmocom(config)
    ic = tb.channelizer
    ic.distribute_processor_affinity(NCORES)
    tb.start()

    rounds = 0

    while True:
        time.sleep(1)
        ic.check_time_triggers()
        ic.update_powers()

        ic.hit_perflog()
        ic.sample_offset()
        rounds += 1

        if 0 == rounds % 5:
        #    ic.splat_levels()
            ic.submit_control_counts()

        if 0 == rounds % 2:
            ic.send_ping()
            ic.send_channel_states()

        if 0 == rounds % 60:
            ic.roll_control_log()

    tb.stop()
    tb.wait()
