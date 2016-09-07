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


from gnuradio import blocks
from gnuradio import analog
from gnuradio import digital
from gnuradio import filter as gr_filter
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from gnuradio.filter import pfb
from optparse import OptionParser

from wavheader import wave_header, wave_fixup_length

from collections import defaultdict

import unirest

import osmosdr
import time
import os

import json

from timestamp_file_sink import timestamp_file_sink
from time_trigger import time_trigger


from smartnet_janky import *

class recording_channelizer(gr.top_block):
    def attach_audio_channel(self, f_i, i):
        chain = []

        pwr_squelch = analog.pwr_squelch_cc(self.threshold, 0.0001, 0, True)
        nbfm_rx = analog.nbfm_rx(
            audio_rate=self.chan_rate,
            quad_rate=self.chan_rate,
            tau=75e-6,
            max_dev=2.5e3,
        )


        self.connect((self.pfb_channelizer_ccf_0, i),
                     pwr_squelch, nbfm_rx)

        return nbfm_rx

    def attach_voice_finals(self, f_i, audio_source):
        rational_resampler = gr_filter.rational_resampler_fff(
            interpolation=16,
            decimation=25,
            taps=None,
            fractional_bw=None,
        )

        scanpath = "scanner/%d/" % self.run_time

        print "#"
        print "# Output dir: %s" % scanpath
        print "#"

        try:
            os.makedirs(scanpath)
        except:
            pass

        f_bias = blocks.add_const_ff(1.0)
        f_scale = blocks.multiply_const_ff(125.0)
        f_to_char = blocks.float_to_uchar()


        self.connect(audio_source,
                     rational_resampler,
                     f_bias,f_scale,f_to_char)


        pattern = "%s/audio_%d_%%s.wav" % (scanpath, f_i)

        wav_header = wave_header(1, 8000, 8, 0)

        def wave_fixup_cb(fd, n_samples):
            wave_fixup_length(fd)


        def started_cb(x):
            # print "Start: %s" % str(x)
            unirest.get(self.base_url + "start/%d" % x, callback=lambda r: "Isn't that nice.")

        def stop_cb(x):
            # print " Stop: %s" % str(x)
            unirest.get(self.base_url + "stop/%d" % x, callback=lambda r: "Isn't that nice.")



        ttrig = time_trigger(self.holdoff, started_cb, stop_cb, f_i)
        self.time_triggers.append(ttrig)


        afile_sink = timestamp_file_sink(pattern,
                                         self.holdoff,
                                         header=wav_header,
                                         final_cb=wave_fixup_cb)

        self.connect(f_to_char, afile_sink)
        self.connect(f_to_char, ttrig)



    def attach_control_finals(self, f_i, audio_source):
        self.control_counts[f_i] = { "tun": 0, "unk": 0, "err": 0, "skip": 0, "oth": 0 }
        
        def print_pkt(s):
            cmd = int(s["cmd"], 16)

            self.cmd_file.write(json.dumps(s) + "\n")

            self.cmd_counts[cmd] += 1


            def decode_frequency_rebanded(cmd):
                # Based on http://home.ica.net/~phoenix/wap/TRUNK88/Motorola%20Channel%20Numbers.txt
                if cmd <= 0x1B7:
                    return 851012500 + 25000*cmd
                if cmd <= 0x22F:
                    return 851025000 + 25000*cmd
                if cmd <= 0x2CF:
                    return 865012500 + 25000*cmd
                if cmd <= 0x2F7:
                    return 866000000 + 25000*cmd
                if cmd <= 0x32E:
                    return 0 # Bogon
                if cmd <= 0x33F:
                    return 867000000 + 25000*cmd
                if cmd <= 0x3BD:
                    return 0 # Bogon
                if cmd == 0x3BE:
                    return 868975000
                if cmd <= 0x3C0:
                    return 0
                if cmd <= 0x3FE:
                    return 867425000 + 25000*cmd
                if cmd == 0x3FF:
                    return 0

                return 0

            if 0x2d0 >= cmd:
                tunefreq = decode_frequency_rebanded(cmd)
                if self.channels and tunefreq not in self.channels:
                    #print "UNK** %s" % str(s)
                    self.control_counts[f_i]["unk"] += 1
                    if tunefreq not in self.unk_counts:
                        self.unk_counts[tunefreq] = 0
                    self.unk_counts[tunefreq] += 1
                else:
                    #print "tun: %s" % str(s)
                    self.control_counts[f_i]["tun"] += 1
                    if self.base_url:
                        unirest.get(self.base_url + "tune/%d/%d" % (tunefreq, s["idno"]), callback=lambda r: "Isn't that nice.")
            else:
                self.control_counts[f_i]["oth"] += 1


        def print_skipped(n):
            self.control_counts[f_i]["skip"] += 1
            self.cmd_file.write(json.dumps({"skip": n}) + "\n")
            return # print "skip: %f / %d" % (time.time(), n)

        def print_cksum_err(s):
            self.control_counts[f_i]["err"] += 1
            self.cmd_file.write(json.dumps({"err": 1}) + "\n")
            # print "   ** err: %s" % str(s)

        smartnet_attach_control_dsp(self, audio_source, time.time(), print_pkt, print_skipped, print_cksum_err)


    def __init__(self, channels=None, samp_rate=2400000, Fc=852700000, base_url=None, threshold=-50, correction=0, gain=10):
        gr.top_block.__init__(self, "Splitter")


        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate
        self.chan_rate = chan_rate = 12500
        self.n_channels = n_channels = samp_rate/chan_rate


        self.channels = channels

        self.Fc = Fc

        self.holdoff = holdoff = 0.5
        self.threshold = threshold # = -50.0

        self.base_url = base_url


        self.gain = gain
        self.gain_if = 0
        self.gain_bb = 0

        self.freq_corr = correction

        self.control_counts = {} # freq => counts of control types

        self.cmd_counts = defaultdict(int) # cmd => N

        self.cmd_file = file("/tmp/commandstream", "a")
        self.cmd_file.write("null\n")

        self.unk_counts = {} # freq => counts

        def channelizer_frequency(i):
            if i > n_channels/2:
                return Fc - (n_channels - i)*chan_rate
            return Fc + i*chan_rate


        print "#"
        print "#"

        print "# Starting up scanner: Fs=%d, Fchan=%d, n_chan=%d, threshold=%d" % (samp_rate, chan_rate, n_channels, threshold)
        if channels:
            missing_channels = set(channels)
            skipped_channels = 0
            for i in range(n_channels):
                f_i = channelizer_frequency(i)
                if f_i in channels:
                    print "#   * %03d %d" % (i, f_i)
                    missing_channels.remove(f_i)
                else:
                    skipped_channels += 1

            print "#   Skipped %d channels" % skipped_channels

            print "#   Input channels missing:"

            for f_i in sorted(list(missing_channels)):
                print "#   ! ___ %d" % f_i

        print "#"
        print "#"


        self.lpf_taps = lpf_taps = firdes.low_pass(1.0,
                                                   samp_rate,
                                                   samp_rate/n_channels/2,
                                                   samp_rate/n_channels/4,
                                                   firdes.WIN_HAMMING,
                                                   6.76)

        print "# LPF taps: %d long" % len(self.lpf_taps)


        ##################################################
        # Blocks
        ##################################################

        # Set up the RTL-SDR source
        self.osmosdr_source_0 = osmosdr.source( args="numchan=" + str(1) + " " + "" )
        self.osmosdr_source_0.set_sample_rate(samp_rate)
        self.osmosdr_source_0.set_center_freq(Fc, 0)
        self.osmosdr_source_0.set_freq_corr(self.freq_corr, 0)
        self.osmosdr_source_0.set_dc_offset_mode(0, 0)
        self.osmosdr_source_0.set_iq_balance_mode(0, 0)
        self.osmosdr_source_0.set_gain_mode(False, 0)
        self.osmosdr_source_0.set_gain(self.gain, 0)
        self.osmosdr_source_0.set_if_gain(self.gain_if, 0)
        self.osmosdr_source_0.set_bb_gain(self.gain_bb, 0)
        self.osmosdr_source_0.set_antenna("", 0)
        self.osmosdr_source_0.set_bandwidth(0, 0)



        # Set up the Polyphase Filter Bank Channelizer:
        self.pfb_channelizer_ccf_0 = pfb.channelizer_ccf(
        	  self.n_channels,
        	  (lpf_taps),
        	  1.0,
        	  100)
        self.pfb_channelizer_ccf_0.set_channel_map(([]))
        self.pfb_channelizer_ccf_0.declare_sample_delay(0)
        	
        ##################################################
        # Connections
        ##################################################
        self.connect((self.osmosdr_source_0, 0), (self.pfb_channelizer_ccf_0, 0))

        self.run_time = time.time()

        self.time_triggers = []

        chains = []
        for i in range(self.n_channels):
            f_i = channelizer_frequency(i)

            if None == channels or f_i in channels:
                audio_source = self.attach_audio_channel(f_i, i)
                self.attach_voice_finals(f_i, audio_source)

                if f_i == 851400000 or f_i == 851425000:
                    self.attach_control_finals(f_i, audio_source)

            else:
                null_sink = blocks.null_sink(gr.sizeof_gr_complex)
                self.connect((self.pfb_channelizer_ccf_0, i), null_sink)

    def check_time_triggers(self):
        for ttrig in self.time_triggers:
            ttrig.poll_end()

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate

    def get_port_out(self):
        return self.port_out

    def set_port_out(self, port_out):
        self.port_out = port_out

    def get_port_in(self):
        return self.port_in

    def set_port_in(self, port_in):
        self.port_in = port_in

    def get_lpf_taps(self):
        return self.lpf_taps

    def set_lpf_taps(self, lpf_taps):
        self.lpf_taps = lpf_taps
        self.pfb_channelizer_ccf_0.set_taps((self.lpf_taps))


if __name__ == '__main__':
    parser = OptionParser(option_class=eng_option, usage="%prog: [options]")
    parser.add_option("-c", "--channels", help="File containing channels list: will only emit these")
    parser.add_option("-r", "--samp-rate", help="Sample rate (Hz)", default=2400000, type=int)
    parser.add_option("-f", "--freq", help="Center frequency (Hz)", default=852700000, type=int)
    parser.add_option("-u", "--url", help="Server base URL", default=None)
    parser.add_option("-t", "--threshold", help="Squelch threshold on audio channels, dB", default=-50, type=int)
    parser.add_option("-o", "--correction", help="Correction offset, PPM", default=0, type=int)
    parser.add_option("-g", "--gain", help="Gain, dB", default=10, type=int)

    (options, args) = parser.parse_args()


    channels = None
    if options.channels:
        f = file(options.channels)
        lines = f.read().split("\n")
        channels = map(int, filter(None, lines))
        f.close()

    tb = recording_channelizer(channels, options.samp_rate, options.freq, options.url, options.threshold, options.correction, options.gain)
    tb.start()

    cycles = 0
    while True:
        time.sleep(1)
        tb.check_time_triggers()

        cycles += 1
        if False and 0 == (cycles % 3):
            print
            print "CONTROLS W/MEAN: %d %s" % (time.time(), str(tb.control_counts))

            print
            print "Unks: %s" % (str(tb.unk_counts))

            print



            print "cmds: %s" % str(tb.cmd_counts)

            cmdids = tb.cmd_counts.keys()
            cmdids.sort(key = lambda c: -1*tb.cmd_counts[c])
            for cmd in cmdids[:15]:
                print "    0x%x: %d" % (cmd, tb.cmd_counts[cmd])

            print

    try:
        raw_input('Press Enter to quit: ')
    except EOFError:
        pass
    tb.stop()
    tb.wait()
