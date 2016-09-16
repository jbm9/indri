#!/usr/bin/env python

# Schleps files from the upload/ directory up to a remote fileserver,
# then moves them to the archive/ directory so the archiver can do its
# thing.

import os
import sys

import os.path
sys.path.append(os.path.dirname(__file__) + "/../lib") # TODO

from indri_config import IndriConfig

import errno

import time
import logging
from watchdog.observers import Observer
import watchdog.events

import json
import unirest
import urllib2

from optparse import OptionParser

class BaseUploader(watchdog.events.FileSystemEventHandler):
    TYPENAME="base"

    def __init__(self, config, config_section):
        self.config = config
        self.config_section = config_section

        self.base_url = config["websocket_uri"]


        if self.TYPENAME != config[config_section]["mode"]:
            raise Exception("Config for '%s' wants mode '%s', while uploader is of type '%s'" % (config_section, config[config_section]["mode"], self.TYPENAME))

        self.upstream = config[config_section]["upstream"]

        self.upstream_key = "out_dir"
        if "upstream_key" in config[config_section]:
            self.upstream_key = config[config_section]["upstream_key"]

        self.in_dir = config[self.upstream][self.upstream_key]
        self.tmp_dir = config[config_section]["tmp_dir"]
        self.dest_dir = config[config_section]["out_dir"]
        self.do_remove = config[config_section]["do_remove"]



        for d in self.in_dir, self.tmp_dir, self.dest_dir:
            if not d:
                continue
            try:
                os.makedirs(d)
            except OSError, e:
                if e.errno == errno.EEXIST:
                    pass
                else:
                    raise e

        self.bootstrap()

    def bootstrap(self):
        # Override this to set up your environment as needed
        return


    def handle(self, path, filename):
        # Override this with your actual per-file work
        # NB: This is called with the file in tmp_dir, not out_dir.
        return True

    ##############################
    # Internal methods below

    def start(self):
        self.observer = Observer()
        self.observer.schedule(self,
                               self.in_dir,
                               recursive=False)


        self.observer.start()


    def stop(self):
        self.observer.stop()

    def join(self):
        self.observer.join()


    def run(self):
        self.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
        self.join()




    def send_message(self, msg):
        try:
            unirest.get(self.base_url + "json/%s" % (json.dumps(msg)), callback=lambda x: "Isn't that nice.")
        except urllib2.URLError, e:
            print "URL upload error! %s" % e

        
    def dispatch(self, evt):
        if evt.event_type != "created":
            return

        filename = os.path.basename(evt.src_path)
        print "%s: File created: %s" % (filename, evt.src_path)

        tmp_path = os.path.join(self.tmp_dir, filename)

        try:
            os.rename(evt.src_path, tmp_path)
        except OSError, e:
            if e.errno == errno.ENOENT:
                print "%s: Already handled, skipping" % filename
                return

        try:
            success = self.handle(tmp_path, filename)
            print "%s: %s" % (filename, 
                              "success" if success else "Failed")
        except Exception, e:
            print "%s: Exception: %s" % (filename, str(e))

        if self.do_remove:
            print "%s: removing." % filename
            os.remove(tmp_path)
        elif self.tmp_dir != self.dest_dir:
            print "%s: finishing into %s" % (filename, self.dest_dir)
            final_path = os.path.join(self.dest_dir, filename)
            os.rename(tmp_path, final_path)

        print "%s: completed." % filename


def run_uploader(klass):
    parser = OptionParser(usage="%prog: [options]")
    parser.add_option("-c", "--config", help="File containing config file")
    parser.add_option("-n", "--name", help="Section name of this component", default="upload")

    (options, args) = parser.parse_args()

    if not options.config:
        print "Need a config file, -c indri.json"
        sys.exit(1)


    config = IndriConfig(options.config)

    uploader = klass(config, options.name)
    uploader.run()
