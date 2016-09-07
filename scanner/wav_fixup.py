#!/usr/bin/env python

from wavheader import wave_fixup_length

import sys

f = file(sys.argv[1], "r+b")
wave_fixup_length(f)
f.flush()
f.close()
