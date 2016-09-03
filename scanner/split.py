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

import unirest

import osmosdr
import time
import os

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
            max_dev=5e3,
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
            unirest.get(self.base_url + "%d-start/1" % x, callback=lambda r: "Isn't that nice.")

        def stop_cb(x):
            # print " Stop: %s" % str(x)
            unirest.get(self.base_url + "%d-stop/1" % x, callback=lambda r: "Isn't that nice.")



        ttrig = time_trigger(self.holdoff, started_cb, stop_cb, f_i)
        self.time_triggers.append(ttrig)


        afile_sink = timestamp_file_sink(pattern,
                                         self.holdoff,
                                         header=wav_header,
                                         final_cb=wave_fixup_cb)

        self.connect(f_to_char, afile_sink)
        self.connect(f_to_char, ttrig)



    def attach_control_finals(self, f_i, audio_source):
        print "attach control finals: %d" % f_i
        rational_resampler = gr_filter.rational_resampler_fff(
            interpolation=36,
            decimation=125,
            taps=None,
            fractional_bw=None,
        )


        slicer = digital.binary_slicer_fb()

        def print_pkt(s):
            cmd = int(s["cmd"], 16)
            if 0x2d0 >= cmd:
                tunefreq = 851012500 + 25000*cmd
                if tunefreq not in self.channels:
                    print "UNK** %s" % str(s)
                else:
                    print "tun: %s" % str(s)


        def print_skipped(n):
            return # print "skip: %f / %d" % (time.time(), n)

        def print_cksum_err(s):
            print "   ** err: %s" % str(s)

        snj = smartnet_janky(time.time(), print_pkt, print_skipped, print_cksum_err)

        print "Control set up"
        self.connect(audio_source, rational_resampler, slicer, snj)

    def __init__(self, channels=None, samp_rate=2400000, Fc=852700000, base_url=None, threshold=-50, correction=0):
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


        self.gain = 10     # TODO expose gain settings at CLI
        self.gain_if = 20
        self.gain_bb = 20

        self.freq_corr = correction

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

                if f_i == 851400000:
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

    (options, args) = parser.parse_args()


    channels = None
    if options.channels:
        f = file(options.channels)
        lines = f.read().split("\n")
        channels = map(int, filter(None, lines))
        f.close()

    tb = recording_channelizer(channels, options.samp_rate, options.freq, options.url, options.threshold, options.correction)
    tb.start()

    while True:
        time.sleep(1)
        tb.check_time_triggers()

    try:
        raw_input('Press Enter to quit: ')
    except EOFError:
        pass
    tb.stop()
    tb.wait()
