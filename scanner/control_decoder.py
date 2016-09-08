# This is a basic state machine for decoding the control protocol of
# Motorola Smartnet II systems.  It's wildly incomplete and likely
# inaccurate in a few places (some of which are obvious kludgy
# corner-cutting before, but most of which are probably invisible, as
# my ignorance extends beyond them, so I don't even know they're
# missing).
#
# My primary reference for this is the slightly-annotated dump of OSW
# (Outbound Signalling Words) by radioreference user slicerwizard:
# http://forums.radioreference.com/voice-control-channel-decoding-software/132039-control-channel-decoding-help.html

class ControlDecoder:
    STATE_ANY = 0 # used for wildcard rules
    STATE_IDLE = 1

    STATE_IN_308_G = 10
    STATE_IN_309_I = 20


    STATE_IN_NET_INFO = 30

    CMD_ANY = 0xFFFF # wildcard command
    CMD_CHANNEL = 0xFFFE # any command that's a channel allocation

    CMD_SITE_ID = 0xFFFD # commands 360~39F, inclusive

    def __init__(self):
        self.state = self.STATE_IDLE
        self.callbacks = {} # event => callback

        self.stack = [] # stack of packets

        self._handlers = [
            #  state,         cmd, group, handler

            # 360 ~ 39F: Site ID
            [ self.STATE_ANY,   self.CMD_SITE_ID, 1, self.handle_site_id ],

            [ self.STATE_ANY,   0x3A0, 1, self.handle_diagnostic ],

            # 2F8: Idle
            [ self.STATE_ANY,           0x2F8,        0, self.handle2F8i ],            
            #####
            # A bunch of 308s, which are AKA 321 in digital mode
            [ self.STATE_ANY,           0x308,        1, self.handle308g0 ],
            [ self.STATE_ANY,           0x321,        1, self.handle308g0 ],

            # 308: Patch established
            [ self.STATE_IN_308_G, 0x340,        1, self.handle_patch ],

            # 308: System ID
            [ self.STATE_IN_308_G, 0x30B,        1, self.handle_sysid ],

            # 308: 320: Net info
            [ self.STATE_IN_308_G, 0x320,        1, self.handle_net_info0 ],
            [ self.STATE_IN_NET_INFO, 0x30B, 1,     self.handle_net_info1 ],

            # 308: Group call grant
            [ self.STATE_IN_308_G, self.CMD_CHANNEL,  1, self.handle_group_call_grant ],



            #####
            # 309: affiliation/deaffiliation
            [ self.STATE_ANY,           0x309,        0, self.handle309i ],
            [ self.STATE_ANY,           0x308,        0, self.handle309i ],
            # 309 310: affiliation of radio to talkgroup
            [ self.STATE_IN_309_I,      0x310,        0, self.handle_affiliation ],
            [ self.STATE_IN_309_I,      0x30b,        0, self.handle_affiliation ],

            # 308: Private call grant
            [ self.STATE_IN_309_I, self.CMD_CHANNEL,  0, self.handle_private_call ],

            # 308: 319: Page signal sent
            [ self.STATE_IN_309_I, 0x319, 0, self.handle_page_sent ],
            [ self.STATE_IN_309_I, 0x31a, 0, self.handle_page_ack ],


            #####
            # System status announcements
            [ self.STATE_ANY,           0x3BF,        1, self.handle3BFx ],
            [ self.STATE_ANY,           0x3BF,        0, self.handle3BFx ],

            [ self.STATE_ANY,           0x3C0,        1, self.handle3C0g ],


            # Random group calls
            [ self.STATE_IDLE, self.CMD_CHANNEL,      1, self.handle_channel ],
            [ self.STATE_IDLE, self.CMD_CHANNEL,      0, self.handle_type2_interconnect ],
        ]


        self._idle()

    def __str__(self):
        return "state=%d, stack=%s" % (self.state, str(self.stack))

    def handle_packet(self, pkt):
        for initial_state, command, groupmask, handler in self._handlers:
            if self.STATE_ANY != initial_state and self.state != initial_state:
                continue

            if pkt["group"] != groupmask:
                continue

            if pkt["cmd"] == command or self.CMD_ANY == command:
                return handler(pkt)

            if self.CMD_SITE_ID == command:
                if pkt["cmd"] >= 0x360 and pkt["cmd"] <= 0x39F:
                    return handler(pkt)

            if self.CMD_CHANNEL == command:
                if self._is_channel(pkt["cmd"]):
                    return handler(pkt)

        self._idle()
        return "Unhandled!"


    def handle_skip(self, n):
        self._idle()

    def handle_cksum_err(self, bogon_pkt):
        self._idle()

    def register_cb(self, name, func):
        self.callbacks[name] = func


    ####################
    # Internal methods
    #

    def _idle(self):
        self.state = self.STATE_IDLE
        self.stack = []

    def _do_cb(self, cbname, *args):
        if cbname in self.callbacks:
            self.callbacks[cbname](*args)
        elif "*" in self.callbacks:
            self.callbacks["*"](cbname, args)


    def _is_channel(self, cmd):
        if cmd < 0x2F8:
            return True
        if cmd < 0x32F:
            return False
        if cmd < 0x340:
            return True
        if cmd == 0x3BE:
            return True
        if cmd > 0x3C0 and cmd <= 0x3FE:
            return True
        return False


    def handle_site_id(self, pkt):
        site_id = pkt["cmd"] - 0x360
        idno = pkt["idno"]
        self._do_cb("site_id", site_id, idno)
        # no idle: this can interrupt other stuff

    def handle_diagnostic(self, pkt):
        diagnostic_code = pkt["idno"]
        self._do_cb("diagnostic", diagnostic_code)


    def handle2F8i(self, pkt):
        self._do_cb("idle")
        # no idle: this can interrupt other stuff

    def handle308g0(self, pkt):
        self.stack = [pkt]
        self.state = self.STATE_IN_308_G
            
    def handle_patch(self, pkt):
        tg_to_include = (self.stack[0]["idno"] >> 4)
        patch_number = pkt["idno"]

        self._do_cb("patch_include", patch_number, tg_to_include)
        self._idle()


    def handle_sysid(self, pkt):
        sysid = self.stack[0]["idno"]
        control_chan = pkt["idno"] & 0xFF;

        self._do_cb("sysid", sysid, control_chan)
        self._idle()


    def handle_net_info0(self, pkt):
        self.stack.append(pkt)
        self.state = self.STATE_IN_NET_INFO

    def handle_net_info1(self, pkt):
        sysid = self.stack[0]["idno"]
        features = self.stack[1]["idno"]
        pcc = pkt["idno"] & 0xFFF
        cellno = pkt["idno"] >> 24

        self._do_cb("net_info", sysid, features, cellno, pcc)
        self._idle()


    def handle_group_call_grant(self, pkt):
        radio_id = self.stack[0]["idno"]
        channel = pkt["cmd"]
        tg = pkt["idno"]

        self._do_cb("group_call_grant", radio_id, channel, tg)
        self._idle()



    def handle309i(self, pkt):
        self.stack = [pkt]
        self.state = self.STATE_IN_309_I

    def handle_affiliation(self, pkt):
        radio_id = self.stack[0]["idno"]
        tg = pkt["idno"] >> 4

        if self.stack[0]["cmd"] == 0x309:
            self._do_cb("affiliation_request", radio_id, tg)
        elif self.stack[0]["cmd"] == 0x308:
            self._do_cb("deaffiliation_request", radio_id, tg)
        self._idle()

    def handle_private_call(self, pkt):
        dest_radio_id = self.stack[0]["idno"]
        channel = pkt["cmd"]
        src_radio_id = pkt["idno"]

        self._do_cb("private_call", src_radio_id, dest_radio_id, channel)
        self._idle()


    def handle_page_sent(self, pkt):
        dest_radio_id = self.stack[0]["idno"]
        src_radio_id = pkt["idno"]

        self._do_cb("page_sent", src_radio_id, dest_radio_id)
        self._idle()


    def handle_page_ack(self, pkt):
        dest_radio_id = self.stack[0]["idno"]
        src_radio_id = pkt["idno"]

        self._do_cb("page_ack", src_radio_id, dest_radio_id)
        self._idle()

    def handle3BFx(self, pkt):
        opcode = pkt["idno"] >> 13
        value = pkt["idno"] & 0x1FFF;
        self._do_cb("net_status", pkt["group"], opcode, value)
        self._idle()

    def handle3C0g(self, pkt):
        opcode = pkt["idno"] >> 13
        value = pkt["idno"] & 0x1FFF;
        self._do_cb("system_status", pkt["group"], opcode, value)

        self._idle()


    def handle_channel(self, pkt):
        tg = pkt["idno"]
        chan = pkt["cmd"]
        self._do_cb("group_call", chan, tg)


    def handle_type2_interconnect(self, pkt):
        radio_id = pkt["idno"]
        chan = pkt["cmd"]
        self._do_cb("type2_interconnect", chan, radio_id)
