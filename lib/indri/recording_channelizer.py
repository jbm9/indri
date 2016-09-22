import errno

import logging

from gnuradio import blocks
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from gnuradio.filter import pfb
from optparse import OptionParser

from indri.channels import radio_channel, voice_channel
from indri.smartnet.control_sink import control_sink

from indri.server_api import ServerAPI
from indri.control_log import ControlLog
from indri.misc.janky_cpumeter import CPUMeter
from indri.misc.wavheader import wave_header, wave_fixup_length
from indri.smartnet.util import decode_frequency_rebanded

import urllib2
import unirest
import json

import time
import os

class recording_channelizer(gr.hier_block2):
    def __init__(self, config, tune_offset_cb):
        gr.hier_block2.__init__(self, "indri_recording_channelizer",
                                gr.io_signature(1,1,gr.sizeof_gr_complex),
                                gr.io_signature(0,0,0))
        self.config = config
        self.tune_offset_cb = tune_offset_cb

        self.server_api = ServerAPI(config)

        self.samp_rate = config["scanner"]["Fs"]
        self.Fc = config["scanner"]["Fc"]
        self.base_url = config["websocket_uri"]
        self.threshold = config["scanner"]["threshold"]

        self.freq_corr = config["scanner"]["receiver"]["freq_corr"]
        self.gain = config["scanner"]["receiver"]["gain"]
        self.gain_if = 0
        self.gain_bb = 0

        self.control_counts = {"good": 0, "bad": 0, "exp": 0, "offset": 0}

        self.chan_rate = chan_rate = config["scanner"]["chan_rate"]

        self.min_burst = 8000*config["scanner"]["min_burst"]

        ##################################################
        # Variables
        ##################################################

        self.freq_offset = 0.0

        self.perflog = file("/tmp/indri.perflog", "a")

        self.cpu_meter = CPUMeter()

        self.radio_channels = {} # freq => radio_channel object
        self.voice_channels = {} # freq => voice_channel object

        self.n_channels = self.samp_rate/self.chan_rate

        self.channels = config["channels"]

        self.channel_dict = {}
        for c in self.channels:
            self.channel_dict[c["freq"]] = c

        self.holdoff = holdoff = 0.5
        self.control_sinks = {}     # freq => control sinks

        self.control_log_tmp_dir = config["scanner"]["control_log_tmp_dir"]
        self.control_log_dir = config["scanner"]["control_log_dir"]
        self.control_log = ControlLog(self.control_log_tmp_dir, self.control_log_dir)

        def channelizer_frequency(i):
            if i > self.n_channels/2:
                return self.Fc - (self.n_channels - i)*self.chan_rate
            return self.Fc + i*self.chan_rate

        all_freqs = map(channelizer_frequency, range(self.n_channels))


        logging.info("Starting up scanner: Fs=%d, Fc=%d, %d~%d,Fchan=%d, n_chan=%d, threshold=%d" % (self.samp_rate, self.Fc, min(all_freqs), max(all_freqs), self.chan_rate, self.n_channels, self.threshold))
        if self.channels:
            missing_channels = set(self.channel_dict.keys())
            skipped_channels = 0

            for i in range(self.n_channels):
                f_i = channelizer_frequency(i)
                if f_i in self.channel_dict:
                    logging.debug("  * %03d %d" % (i, f_i))
                    missing_channels.remove(f_i)
                else:
                    skipped_channels += 1

            logging.info("   Skipped %d channels" % skipped_channels)

            logging.info("   Input channels missing:")

            for f_i in sorted(list(missing_channels)):
                logging.info("   ! ___ %d" % f_i)

        self.lpf_taps = firdes.low_pass(1.0,
                                        self.samp_rate,
                                        self.samp_rate/self.n_channels/2,
                                        self.samp_rate/self.n_channels/4,
                                        firdes.WIN_HAMMING,
                                        6.76)

        logging.debug(" LPF taps: %d long" % len(self.lpf_taps))


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
        logging.debug("Attaching radio channel to %d" % f_i)
        channel = radio_channel(self.chan_rate, self.threshold, f_i)
        self.connect((self.pfb_channelizer_ccf_0, i),
                     channel)

        return channel

    def attach_voice_finals(self, f_i, i, audio_source):
        logging.debug("Attaching voice/audio sink to %d" % f_i)
        wav_header = wave_header(1, 8000, 8, 0)

        def wave_fixup_cb(fd, n_samples, path):
            wave_fixup_length(fd)
            tg = 0
            avg_power = -100
            if f_i in self.radio_channels:
                tg = self.radio_channels[f_i].tg
                avg_power = self.radio_channels[f_i].reset_power_samples()

            if n_samples < self.min_burst:
                logging.info("TOO SHORT: talkgroup message, N=%d, pwr=%0.2f, tg=%04x (%d) / %s" % (n_samples, avg_power, tg, tg, path))
                os.remove(path)
                return


            logging.info("Closed out talkgroup message, N=%d, pwr=%0.2f, tg=%04x (%d) / %s" % (n_samples, avg_power, tg, tg, path))

            filename = path.split("/")[-1]
            newpath = "%s/%s" % (self.config["scanner"]["out_dir"], filename)
            os.rename(path, newpath)

            msg = { "type": "tgfile", "tg": tg, "path": filename, "avg_power": avg_power }

            if self.config["scanner"]["self_upload"]:
                msg["available"] = True
            
            self._submit(msg)

        def started_cb(x):
            logging.debug("Channel opened on frequency %d" % x)
            # self._submit({"type": "start", "freq": x})
            pass

        def stop_cb(x):
            logging.debug("Channel closed on frequency %d" % x)
            # self._submit({"type": "stop", "freq": x})
            self.radio_channels[x].note_close()
            pass

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

        self.voice_channels[f_i] = channel
        self.connect(self.radio_channels[f_i],
                     self.voice_channels[f_i])




    def attach_control_finals(self, f_i, audio_source):
        logging.debug("Attaching smartnet control sink to %d" % f_i)
        def print_cb(cbname, args):
            logline = "%s %s\n" % (cbname, " ".join(map(str, args)))
            self.control_log.write(logline)

        def group_call_cb(chan, tg):
            freq = decode_frequency_rebanded(chan)

            # self._submit({"type": "tune", "freq": freq, "tg": tg})

            if freq in self.radio_channels:
                if not self.radio_channels[freq].has_channel_cleared(tg) and self.radio_channels[freq].tg != 0:
                    logging.warning("**** Reusing an unsquelched channel! f=%d, tg_old=%x, tg_new=%x" % (freq, self.radio_channels[freq].tg, tg))
                self.radio_channels[freq].set_tg(tg)

            print_cb("group_call", [chan, tg])

        self.control_sinks[f_i] = control_sink()
        self.control_sinks[f_i].register_cb("group_call", group_call_cb)
        self.control_sinks[f_i].register_cb("*", print_cb)
        self.connect(audio_source, self.control_sinks[f_i])

    def _submit(self, event_body):
        self.server_api.submit(event_body['type'], event_body)


    def update_powers(self):
        for c in self.radio_channels.values():
            c.power_sample()


    def check_time_triggers(self):
        for c in self.voice_channels.values():
            c.poll_end()

    def roll_control_log(self):
        self.control_log.roll()


    def sample_offset(self):
        for f_i in self.control_sinks:
            if self.radio_channels[f_i].unmuted():
                errterm = self.control_sinks[f_i].read_offset()
                self.freq_offset += errterm*12500/8
                self.tune_offset_cb(self.freq_offset)


    def get_levels(self):
        retval = {} # f => dB
        for f_i in self.radio_channels:
            retval[f_i] = self.radio_channels[f_i].get_db()
        return retval


    def splat_levels(self):
        body = { "type": "levels", "levels": self.get_levels(), "squelch": self.threshold }
        self._submit(body)


    def send_channel_states(self):
        states = {}
        for f_i in self.radio_channels:
            states[f_i] = [ self.radio_channels[f_i].get_db(),
                            self.radio_channels[f_i].tg ]
        body = { "type": "states", "states": states, "squelch": self.threshold }
        self._submit(body)


    def send_ping(self):
        body = { "type": "ping", "ts": int(time.time()) }
        self._submit(body)


    def submit_control_counts(self):
        self.control_counts = { "type": "control_counts",
                            "good": 0,
                            "bad": 0,
                            "exp": 0,
                            "offset": self.freq_offset }

        for cs in self.control_sinks.values():
            d = cs.control_counts()
            for k in ["good", "bad", "exp"]:
                self.control_counts[k] += d[k]
        
        self._submit(self.control_counts)


    def hit_perflog(self):
        content = { "ts": int(time.time()) }

        content["cc_good"] = self.control_counts["good"]
        content["cc_bad"] = self.control_counts["bad"]
        content["cc_exp"] = self.control_counts["exp"]

        content["offset"] = self.freq_offset

        content["levels"] = self.get_levels()

        content["idle"] = self.cpu_meter.get_idle_percs()

        self.perflog.write(json.dumps(content) + "\n")


    def distribute_processor_affinity(self, NCORES):
        def procaff(b, i):
            procmask = [0] * NCORES
            procmask[i%NCORES] = 1
            b.set_processor_affinity(procmask)
            
        for k, f_i in enumerate(self.radio_channels):
            procaff(self.radio_channels[f_i], k)
