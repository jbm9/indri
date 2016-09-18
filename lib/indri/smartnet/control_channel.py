from gnuradio import gr
from gnuradio import blocks
from gnuradio import digital
import gnuradio.filter as gr_filter

class control_channel(gr.hier_block2):
    def __init__(self, interpolation=36, decimation=125):
        gr.hier_block2.__init__(self, "indri_smartnet_control_channel",
                                gr.io_signature(1,1,gr.sizeof_float),
                                gr.io_signature(1,1,1))
        
        # Figure out where zero should be, despite RTL-SDR drift
        avglen = 1000 # should be big enough to catch drifts
        offset = blocks.moving_average_ff(avglen, 1.0/avglen, 40*avglen)
        differential = blocks.sub_ff()
        self.connect(self, (differential,0))
        self.connect(self, offset)
        self.connect(offset, (differential,1))

        # sample off the offsets to adjust tuning
        offset_sampler = blocks.keep_one_in_n(gr.sizeof_float, 10*avglen)
        offset_mag_block = blocks.probe_signal_f()
        self.offset_mag = offset_mag_block
        self.connect(offset, offset_sampler, offset_mag_block)

        rational_resampler = gr_filter.rational_resampler_fff(
            interpolation=interpolation,
            decimation=decimation,
            taps=None,
            fractional_bw=0.45,
        )


        slicer = digital.binary_slicer_fb()

        self.connect(differential, rational_resampler, slicer, self)

    def read_offset(self):
        if not self.offset_mag:
            return 0.0

        return self.offset_mag.level()
