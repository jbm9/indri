#!/usr/bin/env python

# Schleps files from the upload/ directory up to a remote fileserver,
# then moves them to the archive/ directory so the archiver can do its
# thing.

import sys
import time
import logging
from watchdog.observers import Observer
import watchdog.events

import boto
from boto.s3.key import Key

import unirest

bucket='indri-testbed'

class UploaderEventHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, bucketname, base_url):

        self.bucketname = bucketname
        self.bootstrap()

        self.base_url = base_url

    def bootstrap(self):
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
                k = Key(self.b)
                k.key = filename
                k.set_contents_from_filename(evt.src_path)
                k.set_acl("public-read")
                unirest.get(self.base_url + "fileup/%s/%s" % (self.bucketname, filename))

                print "Uploaded"
        except Exception, e:
            print "Exception: %s" % str(e)

if __name__ == "__main__":

    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    observer = Observer()
    handler = UploaderEventHandler(bucket, 'http://localhost:8081/post/')
    observer.schedule(handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
