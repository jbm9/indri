import json
import unirest

class ServerAPI:
    def __init__(self, config):
        self.config = config
        self.base_url = config["websocket_uri"]

    def submit(self, type, msg):
        event_body = { "type": type }
        for k,v in msg.iteritems():
            event_body[k] = v

        sub_json = json.dumps(event_body)
        unirest.get("%s/%s/%s" % (self.base_url,
                                  "json",
                                  sub_json), callback=lambda s: "Isn't that nice.")


 
