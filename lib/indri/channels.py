import math
import gnuradio

from indri.blocks.time_trigger import time_trigger
from indri.blocks.timestamp_file_sink import timestamp_file_sink

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


class radio_channel(gr.hier_block2):
    def __init__(self, chan_rate, threshold, freq):
        gr.hier_block2.__init__(self, "indri_radio_channel",
                                gr.io_signature(1,1,gr.sizeof_gr_complex),
                                gr.io_signature(1,1,gr.sizeof_float))

        self.chan_rate = chan_rate
        self.threshold = threshold
        self.freq = freq

        self.pwr_squelch = analog.pwr_squelch_cc(self.threshold, 0.001, 0, True)

        self.nbfm_rx = analog.nbfm_rx(
            audio_rate=self.chan_rate,
            quad_rate=self.chan_rate,
            tau=75e-6,
            max_dev=6.25e3,
        )

        self.power_probe = analog.probe_avg_mag_sqrd_cf(self.threshold, 0.001)
        self.null_sink = blocks.null_sink(gr.sizeof_float)

        self.tg = 0
        self.closed_once = False # have we de-squelched since tg assigned?

        self.power_samples = 0
        self.power_total = 0.0

        self.connect(self,
                     self.power_probe,
                     self.null_sink)


        self.connect(self,
                     self.pwr_squelch,
                     self.nbfm_rx,
                     self)

    def power_sample(self):
        if not self.unmuted():
            return
        self.power_total += self.get_db()
        self.power_samples += 1

    def reset_power_samples(self):
        if not self.power_samples:
            return -100.0

        avg_power = self.power_total / self.power_samples
        self.power_total = 0.0
        self.power_samples = 0

        return avg_power

    def unmuted(self):
        return self.pwr_squelch.unmuted()

    def get_db(self):
        db = int(100*math.log10(1e-10 + self.power_probe.level()))/10.0
        return db

    def set_threshold(self, newthreshold):
        self.threshold = newthreshold
        self.pwr_squelch.set_threshold(newthreshold)
        self.power_probe.set_threshold(newthreshold)

    def note_close(self):
        self.closed_once = True

    def set_tg(self, tg):
        self.tg = tg
        self.closed_once = False

    def has_channel_cleared(self, new_tg):
        return (self.tg == new_tg) or self.closed_once


class voice_channel(gr.hier_block2):
    def __init__(self, chan_rate, target_dir, freq, holdoff, file_header, file_cb, start_cb, stop_cb):
        gr.hier_block2.__init__(self, "indri_voice_channel",
                                gr.io_signature(1,1,gr.sizeof_float),
                                gr.io_signature(0,0,0))

        self.connect(self, blocks.null_sink(gr.sizeof_float))

        self.target_dir = target_dir
        self.freq = freq
        self.holdoff = holdoff

        bpf_taps = firdes.band_pass(1, chan_rate,
                                    300.0, 2000.0, 100,
                                    firdes.WIN_HAMMING,
                                    6.76)

        bpf = gr_filter.fir_filter_fff(1, bpf_taps)

        agc = analog.agc_ff(1e-5, 0.6, 1.0)

        rational_resampler = gr_filter.rational_resampler_fff(
            interpolation=16,
            decimation=25,
            taps=None,
            fractional_bw=0.49,
        )

        f_bias = blocks.add_const_ff(1.0)
        f_scale = blocks.multiply_const_ff(125.0)
        f_to_char = blocks.float_to_uchar()

        self.connect(self,
                     #bpf,
                     #agc,
                     rational_resampler,
                     f_bias,f_scale,f_to_char)

        pattern = "%s/audio_%d_%%s.wav" % (self.target_dir, self.freq)
        ttrig = time_trigger(self.holdoff, start_cb, stop_cb, self.freq)
        self.time_trigger = ttrig

        afile_sink = timestamp_file_sink(pattern,
                                         self.holdoff,
                                         header=file_header,
                                         final_cb=file_cb)

        self.connect(f_to_char, afile_sink)
        self.connect(f_to_char, ttrig)

    def poll_end(self):
        self.time_trigger.poll_end()
