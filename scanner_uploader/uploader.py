#!/usr/bin/env python

# Schleps files from the upload/ directory up to a remote fileserver,
# then moves them to the archive/ directory so the archiver can do its
# thing.

import os
import sys

import os.path
sys.path.append(os.path.dirname(__file__) + "/../lib") # TODO

from indri_config import IndriConfig

import time
import logging
from watchdog.observers import Observer
import watchdog.events

import boto
from boto.s3.key import Key

import json
import unirest
import urllib2

from optparse import OptionParser


bucket='indri-testbed'

class UploaderEventHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, config):
        self.base_url = config["websocket_uri"]

        self.no_upload = config["upload"]["no_upload"]
        self.dest_path = config["upload"]["out_path"]
        self.bucketname = config["upload"]["bucket"]
        self.do_remove = config["upload"]["do_remove"]
        self.bootstrap()


    def bootstrap(self):
        if not self.no_upload:
            self.c = boto.connect_s3()
            self.b = self.c.get_bucket(self.bucketname)
            bucket_location = self.b.get_location()
            if bucket_location:
                self.c = boto.s3.connect_to_region(bucket_location)
                self.b = self.c.get_bucket(self.bucketname)
        
    def dispatch(self, evt):
        try:
            if evt.event_type == "created":
                print "File created: %s" % evt.src_path
                path_components = evt.src_path.split("/")
                filename = path_components[-1]

                try:
                    if self.dest_path != None:
                        new_path = self.dest_path + "/" + filename
                        os.rename(evt.src_path, new_path)
                    elif self.do_remove:
                        os.remove(evt.src_path)
                except Exception, e:
                    print e
                    return

                if self.no_upload:
                    print "no upload: beep boop pretend to upload to S3, success!"
                else:
                    k = Key(self.b)
                    k.key = filename
                    k.set_contents_from_filename(new_path)
                    k.set_acl("public-read")

                try:
                    msg = { "type": "fileup", "bucket": self.bucketname, "path": filename }
                    unirest.get(self.base_url + "json/%s" % (json.dumps(msg)), callback=lambda x: "Isn't that nice.")
                except urllib2.URLError, e:
                    print "URL upload error! %s" % e

                except Exception, e:
                    print e

                print "Uploaded"
        except Exception, e:
            print "Exception: %s" % str(e)

if __name__ == "__main__":
    parser = OptionParser(usage="%prog: [options]")
    parser.add_option("-c", "--config", help="File containing config file")

    (options, args) = parser.parse_args()

    if not options.config:
        print "Need a config file, -c indri.json"
        sys.exit(1)


    config = IndriConfig(options.config)
    try:
        os.makedirs(config["scanner"]["out_path"])
    except:
        pass

    try:
        os.makedirs(config["upload"]["out_path"])
    except:
        pass


    observer = Observer()
    handler = UploaderEventHandler(config)
    observer.schedule(handler, config["scanner"]["out_path"], recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
