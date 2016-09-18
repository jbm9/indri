from gnuradio import gr

from indri.smartnet.deframer import deframer
from indri.smartnet.control_channel import control_channel
from indri.smartnet.control_decoder import control_decoder


class control_sink(gr.hier_block2):
    def __init__(self, interpolation=36, decimation=125):
        gr.hier_block2.__init__(self, "indri_smartnet_control_sink",
                                gr.io_signature(1,1,gr.sizeof_float),
                                gr.io_signature(0,0,0))

        self.control_channel = control_channel(interpolation, decimation)
        self.control_decoder = control_decoder()
        self.deframer = deframer(self.control_decoder.handle_packet,
                                 self.control_decoder.handle_skip,
                                 self.control_decoder.handle_cksum_err)

        self.connect(self, self.control_channel, self.deframer)
    

    def register_cb(self, name, func):
        self.control_decoder.register_cb(name, func)


    def read_offset(self):
        return self.control_channel.read_offset()


    def control_counts(self):
        return self.deframer.fetch_counts()
