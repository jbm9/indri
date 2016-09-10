#!/usr/bin/env python

# Schleps files from the upload/ directory up to a remote fileserver,
# then moves them to the archive/ directory so the archiver can do its
# thing.

import os
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
    def __init__(self, bucketname, base_url, dest_path):

        self.bucketname = bucketname
        self.bootstrap()

        self.dest_path = dest_path
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

                try:
                    new_path = self.dest_path + "/" + filename
                    os.rename(evt.src_path, new_path)
                except Exception, e:
                    print e
                    return

                k = Key(self.b)
                k.key = filename
                k.set_contents_from_filename(new_path)
                k.set_acl("public-read")
                unirest.get(self.base_url + "fileup/%s/%s" % (self.bucketname, filename))

                print "Uploaded"
        except Exception, e:
            print "Exception: %s" % str(e)

if __name__ == "__main__":

    srcpath = sys.argv[1] if len(sys.argv) > 1 else '.'
    destpath = sys.argv[2] if len(sys.argv) > 1 else None
    observer = Observer()
    handler = UploaderEventHandler(bucket, 'http://52.43.230.29:8081/post/', destpath)
    observer.schedule(handler, srcpath, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
