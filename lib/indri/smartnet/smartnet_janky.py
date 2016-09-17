import numpy
from gnuradio import gr

from gnuradio import blocks
from gnuradio import analog
from gnuradio import digital
from gnuradio import filter as gr_filter
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from gnuradio.filter import pfb


def decode_frequency_rebanded(cmd):
    # Based on http://home.ica.net/~phoenix/wap/TRUNK88/Motorola%20Channel%20Numbers.txt
    if cmd <= 0x1B7:
        return 851012500 + 25000*cmd
    if cmd <= 0x22F:
        return 851025000 + 25000*(cmd-0x1B8)
    if cmd <= 0x2CF:
        return 865012500 + 25000*(cmd-0x230)
    if cmd <= 0x2F7:
        return 866000000 + 25000*(cmd-0x2D0)
    if cmd <= 0x32E:
        return 0 # Bogon
    if cmd <= 0x33F:
        return 867000000 + 25000*(cmd-0x32F)
    if cmd <= 0x3BD:
        return 0 # Bogon
    if cmd == 0x3BE:
        return 868975000
    if cmd <= 0x3C0:
        return 0
    if cmd <= 0x3FE:
        return 867425000 + 25000*(cmd-0x3C0)
    if cmd == 0x3FF:
        return 0

    return 0

class smartnet_janky(gr.sync_block):
    PREAMBLE = [1,0,1,0,1,1,0,0]
    PREAMBLE_LEN = len(PREAMBLE)
    FRAME_LEN = 84
    BODY_LEN = FRAME_LEN - PREAMBLE_LEN

    def __init__(self, t0=0, packet_cb=None, skipped_cb=None, cksum_err_cb=None, offset_mag=None):
        gr.sync_block.__init__(self, "smartnet_janky",
                                in_sig=[numpy.byte],
                                out_sig=None)

        self.set_history(self.FRAME_LEN)
        self.t0 = t0
        self.nsamples = 0

        self.packet_cb = packet_cb
        self.skipped_cb = skipped_cb
        self.cksum_err_cb = cksum_err_cb

        self.offset_mag = offset_mag

    def read_offset(self):
        if not self.offset_mag:
            return 0.0

        return self.offset_mag.level()

    def _find_preamble(self, a):
        for i in range(len(a) - len(self.PREAMBLE)):
            found_preamble = True
            for j, bp in enumerate(self.PREAMBLE):
                if bp != a[i+j]:
                    found_preamble = False
                    # print i, bp
                    break

            if found_preamble:
                return i

        return None
                    
    def _deinterleave(self, pkt_in):
        # print "Deint: %s" % "".join(map(str, pkt_in))
        retval = [0] * self.BODY_LEN
        for i in range(self.BODY_LEN/4):
            for j in range(4):
                retval[i*4+j] = pkt_in[i+j*19]

                # print "Deint= %s" % "".join(map(str, retval))
        return retval

    def _syndrome_check(self, frame):
        l = len(frame)
        i = [ frame[j] for j in range(0, l, 2) ]
        k = [ frame[j] for j in range(1, l, 2) ]
        errors = [ 0^i[0]^k[0] ] + [ k[1+j]^i[j]^i[j+1] for j in range(l/2-1) ]

        return i,k,errors


    def _ecc(self, frame):
        l = len(frame)
        i,k,errors = self._syndrome_check(frame)

        #print i
        #print k
        #print errors

        flips = 0

        for j in range(len(errors)-1):
            if errors[j]:
                if errors[j+1]:
                    i[j] ^= 1
                    errors[j+1] = 0
                    flips += 1
                else:
                    k[j] ^= 1
                    flips += 1

        if errors[-1]:
            k[-1] ^= 1

        errors = [ 0^i[0]^k[0] ] + [ k[1+j]^i[j]^i[j+1] for j in range(l/2-1) ]

        return i,k,errors, flips

    def _deframe(self, pkt_in):
        i,k,errors, flips = self._ecc(self._deinterleave(pkt_in[self.PREAMBLE_LEN:]))

        # print flips
        if numpy.sum(errors):
            #print self._ecc(pkt_in)
            #print "Unresolved errors in packet."
            return None

        return i

    def _crc(self, p):
        crcaccum = 0x0393
        crcop = 0x036e
        for b in p[:27]:
            if crcop & 1:
                crcop = (crcop >> 1) ^ 0x0225
            else:
                crcop = (crcop >> 1)

            if int(b) & 1:
                crcaccum ^= crcop

        return crcaccum


    def _parse(self, pkt_in):
        # print "".join(map(str, pkt_in[:self.FRAME_LEN]))

        pkt = self._deframe(pkt_in)

        if None == pkt:
            return None

            # print "DeECC: %s" % "".join(map(str, pkt))

        def _fetch(i, n, invert=1):
            retval = 0
            for j in range(n):
                retval *= 2
                p_ij = int(pkt[i+j])
                retval += invert^(1&p_ij)
                # print "_fetch(%d,%d,%d): %d / %d => %d" % (i, n, invert, j, p_ij, retval)
            return i+n, retval

        cursor = 0
        cursor, idno = _fetch(cursor, 16)
        cursor, group = _fetch(cursor, 1)
        cursor, cmd = _fetch(cursor, 10)
        cursor, cksum = _fetch(cursor, 10)

        cksum_expected = self._crc(pkt)


        cmd ^= 0x32A
        idno ^= 0x33C7

        retval = { "cmd": cmd, "group": group, "idno": idno, "cksum": cksum, "cksum_e": cksum_expected }

        #if cksum != cksum_expected:
        #    retval["pkt"] = pkt

        return retval


    def time(self):
        return self.t0 + self.nsamples/3600.0

    def work(self, input_items, output_items):
        inbuf = input_items[0]
        # print len(inbuf)
        # print inbuf[:80]

        preamble_at = self._find_preamble(inbuf)

        if None == preamble_at:
            self.nsamples += len(inbuf)
            if self.skipped_cb:
                self.skipped_cb(len(inbuf))
            return len(inbuf)
        timestamp = self.t0 + (self.nsamples+preamble_at)/3600.0

        # print preamble_at, len(inbuf)

        if preamble_at is None:
            self.nsamples += len(inbuf)
            return len(inbuf)

        if 0 == preamble_at:
            g = self._parse(inbuf[:self.FRAME_LEN])

            if g is None:
                print "BOGON: " + "".join(map(str, inbuf[:self.FRAME_LEN]))

            if g is not None and g["cksum"] == g["cksum_e"]:
                if self.packet_cb:
                    self.packet_cb(g)

                #print str(g)
                self.nsamples += self.FRAME_LEN
                return self.FRAME_LEN
            else:
                #print "\tBogus checksum: %x / %x / %x" % (g["cksum"], g["cksum_e"], g["cksum"] ^ g["cksum_e"])
                if self.cksum_err_cb:
                    self.cksum_err_cb(g)
                #print g
                if self.skipped_cb:
                    self.skipped_cb(1)

                self.nsamples += 1
                return 1

        else:
            self.nsamples += preamble_at
            if self.skipped_cb:
                self.skipped_cb(preamble_at)
            # print "\tSkipped: %d" % preamble_at
            return preamble_at

def smartnet_attach_control_dsp(top_block, audio_source, t0, pkt_cb, skip_cb, cksum_cb, interpolation=36, decimation=125):


        # Figure out where zero should be, despite RTL-SDR drift
        avglen = 1000 # should be big enough to catch drifts
        offset = blocks.moving_average_ff(avglen, 1.0/avglen, 40*avglen)
        differential = blocks.sub_ff()
        top_block.connect(audio_source, (differential,0))
        top_block.connect(audio_source, offset)
        top_block.connect(offset, (differential,1))

        # sample off the offsets to adjust tuning
        offset_sampler = blocks.keep_one_in_n(gr.sizeof_float, 10*avglen)
        offset_mag_block = blocks.probe_signal_f()
        top_block.connect(offset, offset_sampler, offset_mag_block)

        rational_resampler = gr_filter.rational_resampler_fff(
            interpolation=interpolation,
            decimation=decimation,
            taps=None,
            fractional_bw=0.45,
        )


        slicer = digital.binary_slicer_fb()
        snj = smartnet_janky(t0, pkt_cb, skip_cb, cksum_cb, offset_mag_block)

        top_block.connect(differential, rational_resampler, slicer, snj)
        return snj


    



def smartnet_pkt_print(g):
    raw_addr = g["idno"]
    talkgroup = raw_addr & ~0xF
    flags = raw_addr & 0xF
    freq = 0
    cmd = int(g["cmd"], 16)
    if cmd < 0x2d0:
        freq = 851.0125 + 0.025*cmd

    print "%d CC id=%s / tg=%d => cmd=%s / g=%s / f=%x / freq=%f" % (timestamp, str(g["idno"]), talkgroup, str(g["cmd"]), str(g["group"]), flags, freq)
