from gnuradio import gr
import numpy

class deframer(gr.sync_block):
    PREAMBLE = [1,0,1,0,1,1,0,0]
    PREAMBLE_LEN = len(PREAMBLE)
    FRAME_LEN = 84
    BODY_LEN = FRAME_LEN - PREAMBLE_LEN

    def __init__(self, packet_cb=None, skipped_cb=None, cksum_err_cb=None):
        gr.sync_block.__init__(self, "indri_smartnet_deframer",
                                in_sig=[numpy.byte],
                                out_sig=None)

        self.set_history(self.FRAME_LEN)
        self.nsamples = 0

        self.packet_cb = packet_cb
        self.skipped_cb = skipped_cb
        self.cksum_err_cb = cksum_err_cb

        self.counts = { "good": 0, "bad": 0, "nsamples": 0 }


    def fetch_counts(self):
        dsamples = self.nsamples - self.counts["nsamples"]
        exp = dsamples / self.FRAME_LEN

        retval = { "good": self.counts["good"],
                   "bad": self.counts["bad"],
                   "exp": exp }

        self.counts = { "good": 0, "bad": 0, "nsamples": self.nsamples }

        return retval


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

        # print preamble_at, len(inbuf)

        if preamble_at is None:
            self.nsamples += len(inbuf)
            return len(inbuf)

        if 0 == preamble_at:
            g = self._parse(inbuf[:self.FRAME_LEN])

            if g is None:
                logging.debug("BOGON: " + "".join(map(str, inbuf[:self.FRAME_LEN])))

            if g is not None and g["cksum"] == g["cksum_e"]:
                if self.packet_cb:
                    self.packet_cb(g)

                #print str(g)
                self.counts["good"] += 1
                self.nsamples += self.FRAME_LEN
                return self.FRAME_LEN
            else:
                #print "\tBogus checksum: %x / %x / %x" % (g["cksum"], g["cksum_e"], g["cksum"] ^ g["cksum_e"])
                self.counts["bad"] += 1
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
