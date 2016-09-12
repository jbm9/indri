import json
import logging

from tornado import ioloop, web, websocket
import tornado.escape


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
        print "get(%s)" % args

        args = args.strip("/")
        arglist = args.split("/")
        msgtype = arglist[0]
        msgargs = arglist[1:]

        if msgtype != "json":
            print "bogon packet: %s" % msgtype
            return

        msg = None

        msg_body = "/".join(msgargs)
        msg = json.loads(msg_body)

        self.write( str(args) )
        self.write( str(msg) )

        if msg:
            self.__send_to_connections(msg)




    def __send_to_connections(self, msg):
        for each_connection in self.application.connections.itervalues():
            each_connection.write_message(json.dumps(msg))



class WebSocketServer(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        self.application.i += 1
        self.connection_id = self.application.i
        self.application.connections[self.connection_id] = self

        # Connected event
        self.write_message(json.dumps({
                'type': 'connected',
                'id': self.connection_id,
            'states': g_channel_states.get_states()
                }))


    def on_message(self, message):
        try:
            msg = json.loads(message)
            msg['sender'] = self.connection_id
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
    ioloop.IOLoop.instance().start()
