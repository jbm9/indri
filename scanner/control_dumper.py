#!/usr/bin/env python

# A simple control channel dumper for testing/troubleshooting the
# control decoder.  Takes a filename as an argument, either a proper
# wav file, or a file containing raw 8b unsigned samples.  Either must
# have a sample rate of 8kHz to work.

from gnuradio import blocks
from gnuradio import gr

from smartnet_janky import smartnet_attach_control_dsp

import sys

path = sys.argv[1]
try:
    t0 = int(sys.argv[2])
except:
    t0 = 0


#ts_str = path.split("_")[2]
#ts_str = ts_str[:ts_str.index(".")]
#t0 = int(ts_str)

print "Running %s, t0=%d" % (path, t0)

bitrate = 3600 # Bits per second

tb = gr.top_block()

if path.endswith(".raw"):
    file_source = blocks.file_source(gr.sizeof_char, path, False)
    ctf = blocks.uchar_to_float()
    offset_block = blocks.add_const_ff(-127.0)
    clean_file_source = blocks.multiply_const_ff(1.0/127.0)

    tb.connect(file_source, ctf, offset_block, clean_file_source)

elif path.endswith("wav"):
    clean_file_source = blocks.wavfile_source(path, False)

def print_pkt(s):
    print "pkt: " + str(s)

def print_skipped(n):
    print "      skip: %d" % n

def print_cksum_err(s):
    print "      cksum error: %s" % str(s)

smartnet_attach_control_dsp(tb, clean_file_source,
                            t0,
                            print_pkt,
                            print_skipped,
                            print_cksum_err)

dumper = blocks.file_sink(gr.sizeof_char, "bits")


tb.run()
