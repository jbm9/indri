import sys
import json

class IndriConfig:
    def __init__(self, path=None, blank=True):
        self.config = {}

        if path:
            self.load(path)
            return
        
        if blank:
            self.config = {}
        else:
            self.config = {
                "sitename": "-Unconfigured-",
                "channels": [ {"freq": 851400000,
                               "is_control": True,
                               "name": "Control 1"}
                          ],
                "talkgroups": [ { "tg": 12912, 
                                  "category": "Law Dispatch", 
                                  "short": "SPFD A", 
                                  "long": "Dispatch C D Mission Bayview" }
                            ],

                "mode": "smartnet",

                "websocket_uri": "http://localhost:8081/post/",
                "wav_base_uri": "http://localhost:9000/scanner/scanner/archived/", # note the slash at the end

                "scanner": {
                    "tmp_dir": "/tmp/incoming",
                    "out_dir": "/tmp/upload",
                    "chan_rate": 12500,

                    "Fc": 851600000,
                    "Fs": 1000000,

                    "self_upload": True, # if you're not using uploaders and have out_dir available on a webserver


                    "receiver": { 
                        "type": "rtl-sdr",
                        "freq_corr": 0,
                        "gain": 0,
                        "gain_mode": True,
                    },
                    "threshold": -42,
                    "min_burst": 3.0,
                },


                "upload": {
                    "mode": "S3",  # or "move"
                    "upstream": "scanner",
                    "tmp_dir": "/tmp/upload_working",
                    "out_dir": "/tmp/uploaded",
                    "bucket": "indri-testbed",
                    "no_message": False,
                    "do_remove": False
                },

                "archive": {
                    "mode": "move",
                    "upstream": "upload",
                    "tmp_dir": "/tmp/archived",
                    "out_dir": "/tmp/archived",
                    "no_message": True,
                    "do_remove": False
                },

            }

    def __getitem__(self, k):
        return self.config[k]

    def load(self, path):
        f = file(path)
        self.config = json.load(f)
        f.close()

    def to_json(self):
        return json.dumps(self.config, indent=4)

    def validate(self):
        # XXX TODO yes.
        return True

if "__main__" == __name__:
    from optparse import OptionParser

    parser = OptionParser()

    parser.add_option("-t", "--template", help="Print a JSON template to stdout", default=False, action="store_true")

    parser.add_option("-c", "--config", help="Path to config file")
    parser.add_option("-v", "--verify", help="Verify config parse", default=False, action="store_true")
    parser.add_option("-d", "--dump", help="Show config file contents", default=False, action="store_true")

    (options, args) = parser.parse_args()

    if options.template:
        c = IndriConfig(blank=False)
        print c.to_json()
        sys.exit(0)

    if options.verify:
        if not options.config:
            print "Need a config file to verify!"

        c = IndriConfig()
        try:
            c.load(options.config)

            c.validate()
        except Exception, e:
            print "Failed: %s" % str(e)
            sys.exit(1)
        

