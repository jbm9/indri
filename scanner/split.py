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

import indri
from indri.channels import radio_channel, voice_channel
from indri.config import IndriConfig

from collections import defaultdict


import urllib2
import unirest

import osmosdr
import time
import os

import json


from smartnet_janky import *
from control_decoder import ControlDecoder

from janky_cpumeter import CPUMeter

NCORES = 4


def procaff(b, i):
    procmask = [0] * NCORES
    procmask[i%NCORES] = 1
    b.set_processor_affinity(procmask)


class recording_channelizer(gr.hier_block2):
    def __init__(self, config, tune_offset_cb):
        gr.hier_block2.__init__(self, "indri_recording_channelizer",
                                gr.io_signature(1,1,gr.sizeof_gr_complex),
                                gr.io_signature(0,0,0))
        self.config = config
        self.tune_offset_cb = tune_offset_cb

        self.samp_rate = config["scanner"]["Fs"]
        self.Fc = config["scanner"]["Fc"]
        self.base_url = config["websocket_uri"]
        self.threshold = config["scanner"]["threshold"]

        self.freq_corr = config["scanner"]["receiver"]["freq_corr"]
        self.gain = config["scanner"]["receiver"]["gain"]
        self.gain_if = 0
        self.gain_bb = 0

        self.chan_rate = chan_rate = config["scanner"]["chan_rate"]

        self.min_burst = 8000*config["scanner"]["min_burst"]

        ##################################################
        # Variables
        ##################################################

        self.freq_offset = 0.0

        self.perflog = file("/tmp/indri.perflog", "a")

        self.cpu_meter = CPUMeter()

        self.control_counts = { "type": "control_counts",
                                "good": 0,
                                "bad": 0,
                                "t0": time.time(),
                                "offset": self.freq_offset }

        self.radio_channels = {} # freq => radio_channel object
        self.voice_channels = {} # freq => voice_channel object

        self.n_channels = self.samp_rate/self.chan_rate

        self.channels = config["channels"]

        self.channel_dict = {}
        for c in self.channels:
            self.channel_dict[c["freq"]] = c

        self.holdoff = holdoff = 0.5
        self.snj = {}     # freq => snj

        self.control_log_tmp_dir = config["scanner"]["control_log_tmp_dir"]
        self.control_log_dir = config["scanner"]["control_log_dir"]

        self.control_log = None
        self.control_log_filename = None

        self.roll_control_log()

        def channelizer_frequency(i):
            if i > self.n_channels/2:
                return self.Fc - (self.n_channels - i)*self.chan_rate
            return self.Fc + i*self.chan_rate

        all_freqs = map(channelizer_frequency, range(self.n_channels))


        print "#"
        print "#"

        print "# Starting up scanner: Fs=%d, Fc=%d, %d~%d,Fchan=%d, n_chan=%d, threshold=%d" % (self.samp_rate, self.Fc, min(all_freqs), max(all_freqs), self.chan_rate, self.n_channels, self.threshold)
        if self.channels:
            missing_channels = set(self.channel_dict.keys())
            skipped_channels = 0

            for i in range(self.n_channels):
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


        self.lpf_taps = firdes.low_pass(1.0,
                                        self.samp_rate,
                                        self.samp_rate/self.n_channels/2,
                                        self.samp_rate/self.n_channels/4,
                                        firdes.WIN_HAMMING,
                                        6.76)

        print "# LPF taps: %d long" % len(self.lpf_taps)


        ##################################################
        # Blocks
        ##################################################


        # Set up the Polyphase Filter Bank Channelizer:
        self.pfb_channelizer_ccf_0 = pfb.channelizer_ccf(
            self.n_channels,
            self.lpf_taps,
            1.0,
            100)
        self.pfb_channelizer_ccf_0.set_channel_map(([]))

        ##################################################
        # Connections
        ##################################################
        self.connect(self,
                     (self.pfb_channelizer_ccf_0, 0))

        self.run_time = time.time()

        chains = []
        for i in range(self.n_channels):
            f_i = channelizer_frequency(i)

            if not self.channels or f_i in self.channel_dict:
                radio_source = self.attach_radio_channel(f_i, i)
                self.radio_channels[f_i] = radio_source

                c = self.channel_dict[f_i]
                if c["is_control"]:
                    self.attach_control_finals(f_i, radio_source)
                else:
                    self.attach_voice_finals(f_i, i, radio_source)

            else:
                null_sink = blocks.null_sink(gr.sizeof_gr_complex)
                self.connect((self.pfb_channelizer_ccf_0, i), null_sink)


    def attach_radio_channel(self, f_i, i):

        channel = radio_channel(self.chan_rate, self.threshold, f_i)
        self.connect((self.pfb_channelizer_ccf_0, i),
                     channel)

        procaff(channel, i)

        return channel

    def attach_voice_finals(self, f_i, i, audio_source):

        wav_header = wave_header(1, 8000, 8, 0)

        def wave_fixup_cb(fd, n_samples, path):
            wave_fixup_length(fd)
            tg = 0
            avg_power = -100
            if f_i in self.radio_channels:
                tg = self.radio_channels[f_i].tg
                avg_power = self.radio_channels[f_i].reset_power_samples()

            if n_samples < self.min_burst:
                print "\t\tTOO SHORT: talkgroup message, N=%d, pwr=%0.2f, tg=%04x (%d) / %s" % (n_samples, avg_power, tg, tg, path)
                os.remove(path)
                return


            print "\t\tClosed out talkgroup message, N=%d, pwr=%0.2f, tg=%04x (%d) / %s" % (n_samples, avg_power, tg, tg, path)

            filename = path.split("/")[-1]
            newpath = "%s/%s" % (self.config["scanner"]["out_dir"], filename)
            os.rename(path, newpath)

            msg = { "type": "tgfile", "tg": tg, "path": filename, "avg_power": avg_power }

            self._submit(msg)

        def started_cb(x):
            #print "Start: %s" % str(x)
            self._submit({"type": "start", "freq": x})

        def stop_cb(x):
            #print " Stop: %s" % str(x)
            self._submit({"type": "stop", "freq": x})

        channel = voice_channel(
            self.chan_rate,
            self.config["scanner"]["tmp_dir"],
            f_i,
            self.holdoff,
            wav_header,
            wave_fixup_cb,
            started_cb,
            stop_cb
            )

        procaff(channel, i)

        self.voice_channels[f_i] = channel
        self.connect(self.radio_channels[f_i],
                     self.voice_channels[f_i])




    def attach_control_finals(self, f_i, audio_source):
        control_decoder = ControlDecoder()

        def print_cb(cbname, args):
            if not self.control_log:
                return
            # print "%s: %s" % (cbname, str(args))
            logline = "%s %s\n" % (cbname, " ".join(map(str, args)))
            try:
                self.control_log.write(logline)
            except Exception, e:
                # This sometimes races with the log cycling
                pass


        def group_call_cb(chan, tg):
            freq = decode_frequency_rebanded(chan)

            self._submit({"type": "tune", "freq": freq, "tg": tg})

            if freq in self.radio_channels:
                self.radio_channels[freq].tg = tg

            print_cb("group_call", [chan, tg])

        control_decoder.register_cb("group_call", group_call_cb)
        control_decoder.register_cb("*", print_cb)

        def pkt_cb(pkt):
            self.control_counts["good"] += 1
            unh = control_decoder.handle_packet(pkt)
            if unh:
                s = str(control_decoder)
                #print "unhandled: %03x/%d: %s / %s" % (pkt["cmd"], pkt["group"], str(s), str(pkt))

        def skipped_cb(n):
            # print "skip: %d" % n
            control_decoder.handle_skip(n)

        def cksum_err_cb(pkt):
            # print "cksum:"
            self.control_counts["bad"] += 1
            control_decoder.handle_cksum_err(pkt)


        self.snj[f_i] = smartnet_attach_control_dsp(self,
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
        for c in self.radio_channels.values():
            c.power_sample()


    def check_time_triggers(self):
        for c in self.voice_channels.values():
            c.poll_end()

    def roll_control_log(self):
        if self.control_log:
            while True:
                try:
                    self.control_log.close()
                    break
                except IOError:
                    time.sleep(0.01) # TODO mutexes

            cur_path = os.path.join(self.control_log_tmp_dir, 
                                    self.control_log_filename)

            new_path = os.path.join(self.control_log_dir, 
                                    self.control_log_filename)

            os.rename(cur_path, new_path)

        self.control_log_filename = "control_log_%d.log" % time.time()
        cl_path = os.path.join(self.control_log_tmp_dir,
                               self.control_log_filename)

        self.control_log = file(cl_path, "a")


    def sample_offset(self):
        for f_i in self.snj:
            if self.radio_channels[f_i].unmuted():
                errterm = self.snj[f_i].read_offset()
                print "%d: %f: %f" % (f_i, errterm, self.freq_offset)
                self.freq_offset += errterm*12500/8
                self.tune_offset_cb(self.freq_offset)
                # self.osmosdr_source_0.set_center_freq(self.Fc+self.freq_offset, 0)


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

    def get_levels(self):
        retval = {} # f => dB
        for f_i in self.radio_channels:
            retval[f_i] = self.radio_channels[f_i].get_db()
        return retval

    def splat_levels(self):
        body = { "type": "levels", "levels": self.get_levels(), "squelch": self.threshold }
        self._submit(body)

    def send_ping(self):
        body = { "type": "ping", "ts": int(time.time()) }
        self._submit(body)


    def submit_control_counts(self):
        tnow = time.time()
        self.control_counts["dt"] = int(1000*(tnow - self.control_counts["t0"]))/1000.0

        self._submit(self.control_counts)
        self.control_counts = { "type": "control_counts", "good": 0, "bad": 0, "t0": tnow, "offset": self.freq_offset }


    def hit_perflog(self):
        content = { "ts": int(time.time()) }

        content["cc_good"] = self.control_counts["good"]
        content["cc_bad"] = self.control_counts["bad"]
        content["cc_dt"] = time.time() - self.control_counts["t0"]

        content["offset"] = self.freq_offset

        content["levels"] = self.get_levels()

        content["idle"] = self.cpu_meter.get_idle_percs()

        self.perflog.write(json.dumps(content) + "\n")

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
            ic.splat_levels()
            ic.submit_control_counts()

        if 0 == rounds % 2:
            ic.send_ping()

        if 0 == rounds % 60:
            ic.roll_control_log()

    tb.stop()
    tb.wait()
