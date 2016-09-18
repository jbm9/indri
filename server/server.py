import os
import sys

import os.path
sys.path.append(os.path.dirname(__file__) + "/../lib") # TODO

from indri_config import IndriConfig

from optparse import OptionParser

import json
import logging

from tornado import ioloop, web, websocket
import tornado.escape

import datetime
import time

Gconfig = None
Gconfigpath = None

class ChannelStates:
    def __init__(self):
        self.channels = {} # freq => [open/closed, TG]

    def lookup(self, freq):
        if not freq in self.channels:
            self.channels[freq] = ["unk", 0]

    def open(self, freq):
        self.lookup(freq)
        self.channels[freq][0] = "open"

    def close(self, freq):
        self.lookup(freq)
        self.channels[freq][0] = "closed"
        self.channels[freq][1] = 0


    def tag(self, freq, tg):
        self.lookup(freq)
        old_tg = self.channels[freq][1]
        self.channels[freq][1] = tg

        if self.channels[freq][0] == "open" and tg == old_tg:
            return False
        return True

    def get_states(self):
        retval = []
        for freq in self.channels:
            d = { "freq": freq, "state": self.channels[freq][0], "tg": self.channels[freq][1] }
            retval.append(d)

        return retval

g_channel_states = ChannelStates()

class PostHandler(web.RequestHandler):
    def get(self, args):
        print "%d: get(%s)" % (time.time(), args)

        args = args.strip("/")
        arglist = args.split("/")
        msgtype = arglist[0]
        msgargs = arglist[1:]


        msg = None

        if msgtype == "reload":
            Gconfig = IndriConfig(Gconfigpath).config
            msg = { "type": "config", "config": Gconfig }

        elif msgtype != "json":
            print "bogon packet: %s" % msgtype
            return
        else:
            msg_body = "/".join(msgargs)
            msg = json.loads(msg_body)

            if msg["type"] == "start":
                g_channel_states.open(msg["freq"])
            elif msg["type"] == "stop":
                g_channel_states.close(msg["freq"])
            elif msg["type"] == "tune":
                if not g_channel_states.tag(msg["freq"], msg["tg"]):
                    msg = None # scrub dupes


        self.write( str(args) )
        self.write( str(msg) )

        if msg:
            self.__send_to_connections(msg)




    def __send_to_connections(self, msg):
        for each_connection in self.application.connections.itervalues():
            each_connection.write_message(json.dumps(msg))



class WebSocketServer(websocket.WebSocketHandler):
    KA = json.dumps({"type": "ka"})
    def check_origin(self, origin):
        return True

    def open(self):
        self.application.i += 1
        self.connection_id = self.application.i
        self.application.connections[self.connection_id] = self


        self.write_message(json.dumps({ 'type': "config", "config": Gconfig }))
        self.write_message(json.dumps({ 'type': 'connected',
                                        'states': g_channel_states.get_states() }))

        tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=2), self.ka)


    def ka(self):
        # print "%d: Keepalive: %s" % (time.time(), str(self))
        try:
            self.write_message(self.KA)
            tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=2), self.ka)
        except websocket.WebSocketClosedError:
            pass

    def on_message(self, message):
        try:
            msg = json.loads(message)
            msg['sender'] = self.connection_id

            if msg["type"] == "config":
                self.write_message(json.dumps({"type":"config", "config":Gconfig}))

            # self.__send_to_connections(msg)

        except Exception, e:
            self.write_message(json.dumps({
                'type': 'error',
                'error': str(e),
                'received': message,
                }))

    def on_close(self):
        self.application.log.debug('deleting %d', self.connection_id)

        del self.application.connections[self.connection_id]

        if False:
            self.__send_to_connections({
                'type': 'closed',
                'id': self.connection_id,
                'clients': len(self.application.connections),
            })


    def __send_to_connections(self, msg):
        if 'target' in msg:
            self.application.log.debug('sending from %s to %s: %s',
                    msg.get('sender', None), msg['target'], msg)

            self.application.connections[msg['target']].write_message(
                    json.dumps(msg))

        else:
            self.application.log.debug('sending from %s to everyone: %s',
                    msg.get('sender', None), msg)

            for each_connection in self.application.connections.itervalues():
                each_connection.write_message(json.dumps(msg))


if __name__ == '__main__':
    parser = OptionParser(usage="%prog: [options]")
    parser.add_option("-c", "--config", help="File containing config file")

    (options, args) = parser.parse_args()

    if not options.config:
        print "Need a config file, -c indri.json"
        sys.exit(1)


    Gconfigpath = options.config
    Gconfig = IndriConfig(Gconfigpath).config

    application = web.Application([
            (r'/post/(?P<args>.*)', PostHandler),
            (r'/', WebSocketServer),
            ])

    application.i = 0
    application.connections = {}

    # Set up logging
    handler = logging.StreamHandler()
    handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    application.log = logging.getLogger('websockets-demo')
    application.log.setLevel(logging.DEBUG)
    application.log.addHandler(handler)

    application.listen(8081)
    main_loop = ioloop.IOLoop.instance()
    main_loop.start()
