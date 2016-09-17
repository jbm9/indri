# A class to trigger callbacks when data stops flowing
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

class time_trigger(decim_block):
    """Dead-end sink that triggers callbacks when a channel opens/closes,
    based on timeout (but you have to poll)

    Note that this doesn't create its own clock thread.  You need to
    explicitly call poll_end() on it periodically to find stop events.
    
    You create this by specifying a timeout and two callbacks, along
    with an optional user_param.  When the channel starts receiving
    data, your start_cb is called with that parameter.  If no data is
    seen on the channel for timeout, the next call to poll_end() will
    trigger the stop_cb.

    This should be low-overhead, but I'd always love to see better ways
    to accomplish the same goal.
    
    """  
    def __init__(self, timeout, start_cb, end_cb, user_param=None):
        decim_block.__init__(
            self,
            name = "Timeout trigger",
            in_sig  = [ numpy.uint8 ],
            out_sig = [ ],
            decim = 1
        )

        self.timeout = timeout

        self.last_sample = 0

        self.start_cb = start_cb
        self.end_cb = end_cb
        self.user_param = user_param

        self.in_xmit = False # in-transmission?

    def poll_end(self):
        if not self.in_xmit:
            return

        t = time.time()

        dt = t - self.last_sample

        if dt > self.timeout:
            self.end_cb(self.user_param)
            self.in_xmit = False


    def work(self, input_items, output_items):
        self.poll_end()

        if not self.in_xmit:
            self.start_cb(self.user_param)
            self.in_xmit = True
            
        self.last_sample = time.time()

        return len(input_items[0])
