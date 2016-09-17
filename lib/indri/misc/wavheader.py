import struct

# Utility functions: creates dummy WAVE headers you can stuff into a
# file, then patches them up to match reality after you're done
# appending samples onto it.
#
# Detaching and attaching wavfile sinks was going poorly, so I just
# made a trivial wav file sink.  The problem is that we need to ensure
# the header is correct, or downstream players will refuse to play them.
#
# It's only actually tested with 8b/8kHz audio.  Apologies if it
# mangles other bit depth or sample rates.
#

def wave_header(num_channels, sample_rate, sample_depth_bits, num_samples):
    "Creates a filled-in, zero-length WAVE header for you, returns a bunch of bytes in a string"
    data_size = num_samples * num_channels * sample_depth_bits/8
    block_size = num_channels * sample_depth_bits/8

    header = [
        ("chunk_id",       "4s", "RIFF"),
        ("chunk_size",      "l", 44 - 8 + data_size),

        ("data_format",    "4s", "WAVE"),
        ("subchunk1_id",   "4s", "fmt "),
        ("subchunk1_size",  "l", 16),
        ("audio_format",    "h", 1),
        ("num_channels",    "h", num_channels),
        ("sample_rate",     "l", sample_rate),
        ("byte_rate",       "l", sample_rate * block_size),
        ("block_align",     "h", block_size),
        ("bits_per_sample", "h",sample_depth_bits),

        ("subchunk2_id",   "4s", "data"),
        ("subchunk2_size", "l", data_size),
    ]

    pack_fmt = "<" + "".join([f[1] for f in header])
    pack_args = [f[2] for f in header]

    return struct.pack(pack_fmt, *pack_args)


def wave_fixup_length(fd):
    "Given an open file object containing a WAVE file, fix up the length field.  WARNING: Doesn't check it's actually a wav file!"
    curpos = fd.tell()

    fd.seek(0, 2)
    data_size = fd.tell() - 44

    chunk_size = 44 - 8 + data_size
    subchunk2_size = data_size

    fd.seek(4, 0)
    fd.write(struct.pack("<l", chunk_size))
    fd.seek(40, 0)
    fd.write(struct.pack("<l", data_size))

    fd.seek(curpos, 0)
    

if __name__ == "__main__":
    print wave_header(1, 8000, 8, 62849) # pipe to xxd(1) and sanity check
