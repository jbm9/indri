# A class to create separate wave files for squelched bursts
#
# Could probably use a rework to use messages from a better upstream
# squelch implementation.
#
# Copyright (c) 2016 Josh Myer <josh@joshisanerd.com>
# License: GPL v2
#

from gnuradio import gr
from gnuradio.gr.gateway import decim_block, basic_block, sync_block
import numpy

import datetime
import time



class timestamp_file_sink(decim_block):
    """Creates timestamped files of data, breaking over into a new file when it hasn't seen input for a while

    This is basically used to create new files based on the output of a
    squelched upstream data source.  If it doesn't see any input for some
    span of wall time, it creates a new file.  It would be better to do
    this based on messages from upstream squelch, because that would allow
    you to run the algorithm based on recorded input data (ie: faster than
    real time).

    It takes in a pattern to use when creating the filename of the output,
    and a timeout, both of which are clear given the above.

    It also takes in the file mode to use, as you're likely writing binary.

    The last arguments are a header and a callback to finalize the file.
    This is designed to accept a dummy WAVE header, and then use the
    callback to touch-up the header so the .wav file plays everywhere.
    """
    def __init__(self, path_pattern, timeout, mode="wb", header=[], final_cb=None):
        decim_block.__init__(
            self,
            name = "Timestamp file sink",
            in_sig  = [ numpy.uint8 ],
            out_sig = [ ],
            decim = 1
        )

        self.path_pattern = path_pattern
        self.timeout = timeout

        self.path = None
        self.fd = None
        self.last_sample = 0
        self.mode = mode
        self.header = header
        self.final_cb = final_cb
        self.file_samples = 0

    def work(self, input_items, output_items):
        t = time.time()

        dt = t - self.last_sample

        if dt > self.timeout:
            if None != self.fd:
                if self.final_cb:
                    self.final_cb(self.fd, self.file_samples, self.path)
                self.path = None
                self.fd.close()
                self.file_samples = 0

            path = datetime.datetime.now().strftime(self.path_pattern)
            # print "Starting new file: last=%d, now=%d, new file=%s" % (self.last_sample, t, path)

            self.path = path
            self.fd = file(path, self.mode)
            self.fd.write(self.header)


        self.fd.write(input_items[0])
        self.last_sample = time.time()
        self.file_samples += len(input_items[0])

        return len(input_items[0])
