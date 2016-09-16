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

import math
import gnuradio
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


import urllib2
import unirest

import osmosdr
import time
import os

import json

from timestamp_file_sink import timestamp_file_sink
from time_trigger import time_trigger

from indri_config import IndriConfig
from smartnet_janky import *
from control_decoder import ControlDecoder

NCORES = 4


def procaff(b, i):
    procmask = [0] * NCORES
    procmask[i%NCORES] = 1
    b.set_processor_affinity(procmask)

class recording_channelizer(gr.top_block):
    def attach_audio_channel(self, f_i, i):
        chain = []

        pwr_squelch = analog.pwr_squelch_cc(self.threshold, 0.001, 0, True)
        nbfm_rx = analog.nbfm_rx(
            audio_rate=self.chan_rate,
            quad_rate=self.chan_rate,
            tau=75e-6,
            max_dev=5e3,
        )


        power_probe = gnuradio.analog.probe_avg_mag_sqrd_cf(self.threshold, 0.001)
        null_sink = blocks.null_sink(gr.sizeof_float)

        self.mags[f_i] = power_probe
        self.squelch[f_i] = pwr_squelch

        self.connect((self.pfb_channelizer_ccf_0, i),
                     power_probe,
                     null_sink)


        self.connect((self.pfb_channelizer_ccf_0, i),
                     pwr_squelch, nbfm_rx)

        procaff(nbfm_rx, i)

        return nbfm_rx

    def attach_voice_finals(self, f_i, i, audio_source):


        bpf_taps = firdes.band_pass(1, self.chan_rate,
                                    300.0, 2000.0, 100,
                                    firdes.WIN_HAMMING,
                                    6.76)

        bpf = gr_filter.fir_filter_fff(1, bpf_taps)

        agc = analog.agc_ff(1e-5, 0.8, 1.0)

        rational_resampler = gr_filter.rational_resampler_fff(
            interpolation=16,
            decimation=25,
            taps=None,
            fractional_bw=0.49,
        )

        f_bias = blocks.add_const_ff(1.0)
        f_scale = blocks.multiply_const_ff(125.0)
        f_to_char = blocks.float_to_uchar()

        procaff(rational_resampler, i)
        procaff(f_bias, i)
        procaff(f_scale, i)
        procaff(f_to_char, i)
        procaff(bpf, i)
        procaff(agc, i)
        self.connect(audio_source,
                     bpf,
                     agc,
                     rational_resampler,
                     f_bias,f_scale,f_to_char)


        pattern = "%s/audio_%d_%%s.wav" % (config["scanner"]["tmp_dir"], f_i)

        self.user_data[f_i] = { "tg": None, "power": 0, "power_samples": 0, "last_power": 0 }
        self.control_counts = { "type": "control_counts", "good": 0, "bad": 0, "t0": time.time() }

        wav_header = wave_header(1, 8000, 8, 0)

        def wave_fixup_cb(fd, n_samples, path):
            wave_fixup_length(fd)
            tg = 0
            avg_power = -100.0

            if self.user_data[f_i]["tg"]:
                tg = self.user_data[f_i]["tg"]
                self.user_data[f_i]["tg"] = None

                if self.user_data[f_i]["power_samples"]:
                    sum_power = self.user_data[f_i]["power"]
                    n = self.user_data[f_i]["power_samples"]
                    avg_power = sum_power / n

                    self.user_data[f_i]["power"] = 0.0
                    self.user_data[f_i]["power_samples"] = 0

            if n_samples < self.min_burst:
                print "\t\tTOO SHORT: talkgroup message, N=%d, pwr=%0.2f, tg=%04x (%d) / %s" % (n_samples, avg_power, tg, tg, path)
                os.remove(path)
                return


            print "\t\tClosed out talkgroup message, N=%d, pwr=%0.2f, tg=%04x (%d) / %s" % (n_samples, avg_power, tg, tg, path)

            filename = path.split("/")[-1]
            newpath = "%s/%s" % (config["scanner"]["out_dir"], filename)
            os.rename(path, newpath)

            msg = { "type": "tgfile", "tg": tg, "path": filename, "avg_power": avg_power }

            self._submit(msg)

        def started_cb(x):
            # print "Start: %s" % str(x)
            self._submit({"type": "start", "freq": x})

        def stop_cb(x):
            # print " Stop: %s" % str(x)
            self._submit({"type": "stop", "freq": x})

        ttrig = time_trigger(self.holdoff, started_cb, stop_cb, f_i)
        self.time_triggers.append(ttrig)


        afile_sink = timestamp_file_sink(pattern,
                                         self.holdoff,
                                         header=wav_header,
                                         final_cb=wave_fixup_cb)
        #procaff(afile_sink, i)
        #procaff(ttrig, i)
        self.connect(f_to_char, afile_sink)
        self.connect(f_to_char, ttrig)



    def attach_control_finals(self, f_i, audio_source):
        control_decoder = ControlDecoder()

        def print_cb(cbname, args):
            if not self.control_log:
                return
            # print "%s: %s" % (cbname, str(args))
            logline = "%s %s\n" % (cbname, " ".join(map(str, args)))
            self.control_log.write(logline)


        def group_call_cb(chan, tg):
            freq = decode_frequency_rebanded(chan)

            self._submit({"type": "tune", "freq": freq, "tg": tg})

            if freq in self.user_data:
                self.user_data[freq]["tg"] = tg

            print_cb("group_call", [chan, tg])

        control_decoder.register_cb("group_call", group_call_cb)
        control_decoder.register_cb("*", print_cb)

        def pkt_cb(pkt):
            self.control_counts["good"] += 1
            unh = control_decoder.handle_packet(pkt)
            if unh:
                s = str(control_decoder)
                print "unhandled: %03x/%d: %s / %s" % (pkt["cmd"], pkt["group"], str(s), str(pkt))

        def skipped_cb(n):
            # print "skip: %d" % n
            control_decoder.handle_skip(n)

        def cksum_err_cb(pkt):
            # print "cksum:"
            self.control_counts["bad"] += 1
            control_decoder.handle_cksum_err(pkt)


        snj = smartnet_attach_control_dsp(self,
                                          audio_source,
                                          time.time(),
                                          pkt_cb,
                                          skipped_cb,
                                          cksum_err_cb)

    def _submit(self, event_body):
        sub_json = json.dumps(event_body)
        try:
            unirest.get("%s/%s/%s" % (self.base_url,
                                      "json",
                                      sub_json), callback=lambda s: "Isn't that nice.")
        except urllib2.URLError, e:
            print "URL upload error! %s" % e
        except Exception, e:
            print e
            raise


    def update_powers(self):
        for f_i in self.channel_dict:
            if f_i in self.squelch and f_i in self.user_data:
                if self.squelch[f_i].unmuted():
                    # we'll take a geometric mean here, because laziness
                    m = 10.0*math.log10(1e-10 + self.mags[f_i].level())
                    self.user_data[f_i]["power"] += m
                    self.user_data[f_i]["power_samples"] += 1


    def __init__(self, config):
        samp_rate = config["scanner"]["Fs"]
        Fc = config["scanner"]["Fc"]
        base_url = config["websocket_uri"]
        threshold = config["scanner"]["threshold"]
        correction = config["scanner"]["receiver"]["freq_corr"]
        gain = config["scanner"]["receiver"]["gain"]


        self.min_burst = 8000*config["scanner"]["min_burst"]

        gr.top_block.__init__(self, "Splitter")


        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate
        self.chan_rate = chan_rate = config["scanner"]["chan_rate"]
        self.n_channels = n_channels = samp_rate/chan_rate


        self.channels = config["channels"]
        self.channel_dict = {}
        for c in self.channels:
            self.channel_dict[c["freq"]] = c

        self.Fc = Fc

        self.holdoff = holdoff = 0.5
        self.threshold = threshold # = -50.0

        self.base_url = base_url

        self.gain = gain
        self.gain_if = 0
        self.gain_bb = 0

        self.freq_corr = correction

        self.user_data = {} # freq => misc metdata (used here for talkgroup)

        self.mags = {}    # freq => magnitude monitor
        self.squelch = {} # freq => squelch


        self.control_log_tmp_dir = config["scanner"]["control_log_tmp_dir"]
        self.control_log_dir = config["scanner"]["control_log_dir"]

        self.control_log = None
        self.control_log_filename = None

        self.roll_control_log()

        def channelizer_frequency(i):
            if i > n_channels/2:
                return Fc - (n_channels - i)*chan_rate
            return Fc + i*chan_rate

        all_freqs = map(channelizer_frequency, range(n_channels))


        print "#"
        print "#"

        print "# Starting up scanner: Fs=%d, Fc=%d, %d~%d,Fchan=%d, n_chan=%d, threshold=%d" % (samp_rate, Fc, min(all_freqs), max(all_freqs), chan_rate, n_channels, threshold)
        if self.channels:
            missing_channels = set(self.channel_dict.keys())
            skipped_channels = 0

            for i in range(n_channels):
                f_i = channelizer_frequency(i)
                if f_i in self.channel_dict:
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

        if not self.osmosdr_source_0.get_gain_range().values():
            print "Looks like the RTL-SDR couldn't be opened, bailing"
            sys.exit(1)

        self.osmosdr_source_0.set_sample_rate(samp_rate)
        self.osmosdr_source_0.set_center_freq(Fc, 0)
        self.osmosdr_source_0.set_freq_corr(self.freq_corr, 0)
        self.osmosdr_source_0.set_dc_offset_mode(0, 0)
        self.osmosdr_source_0.set_iq_balance_mode(0, 0)
        self.osmosdr_source_0.set_gain_mode(config["scanner"]["receiver"]["gain_mode"], 0)
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
        	
        ##################################################
        # Connections
        ##################################################
        self.connect((self.osmosdr_source_0, 0), 
                     (self.pfb_channelizer_ccf_0, 0))

        self.run_time = time.time()

        self.time_triggers = []

        chains = []
        for i in range(self.n_channels):
            f_i = channelizer_frequency(i)

            if not self.channels or f_i in self.channel_dict:
                audio_source = self.attach_audio_channel(f_i, i)

                c = self.channel_dict[f_i]
                if c["is_control"]:
                    self.attach_control_finals(f_i, audio_source)
                else:
                    self.attach_voice_finals(f_i, i, audio_source)

            else:
                null_sink = blocks.null_sink(gr.sizeof_gr_complex)
                self.connect((self.pfb_channelizer_ccf_0, i), null_sink)

    def check_time_triggers(self):
        for ttrig in self.time_triggers:
            ttrig.poll_end()


    def roll_control_log(self):
        if self.control_log:
            self.control_log.close()
            cur_path = os.path.join(self.control_log_tmp_dir, 
                                    self.control_log_filename)

            new_path = os.path.join(self.control_log_dir, 
                                    self.control_log_filename)

            os.rename(cur_path, new_path)

        self.control_log_filename = "control_log_%d.log" % time.time()
        cl_path = os.path.join(self.control_log_tmp_dir,
                               self.control_log_filename)

        self.control_log = file(cl_path, "a")


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


    def splat_levels(self):
        levels = {}
        for f_i in self.mags:
            levels[f_i] = int(1e-10 + 100*math.log10(self.mags[f_i].level()))/10.0

        body = { "type": "levels", "levels": levels, "squelch": self.threshold }
        self._submit(body)

    def send_ping(self):
        body = { "type": "ping", "ts": int(time.time()) }
        self._submit(body)


    def submit_control_counts(self):
        tnow = time.time()
        self.control_counts["dt"] = int(1000*(tnow - self.control_counts["t0"]))/1000.0

        self._submit(self.control_counts)
        self.control_counts = { "type": "control_counts", "good": 0, "bad": 0, "t0": tnow }

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

    tb = recording_channelizer(config)
    tb.start()

    rounds = 0

    while True:
        time.sleep(1)
        tb.check_time_triggers()
        tb.update_powers()

        rounds += 1
        if 0 == rounds % 5:
            tb.splat_levels()
            tb.submit_control_counts()

        if 0 == rounds % 2:
            tb.send_ping()
#        print [ int(100*math.log10(1e-10 + tb.mags[f_i].level()))/10.0 for f_i in sorted(list(tb.mags)) ]
        print [ "***" if tb.squelch[f_i].unmuted() else "   "  for f_i in sorted(list(tb.mags)) ]

        if 0 == rounds % 60:
            tb.roll_control_log()

    tb.stop()
    tb.wait()
