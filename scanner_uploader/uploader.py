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

import json
import unirest
import urllib2

from optparse import OptionParser


bucket='indri-testbed'

class UploaderEventHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, bucketname, base_url, dest_path, no_upload, do_remove):

        self.bucketname = bucketname

        self.dest_path = dest_path
        self.base_url = base_url

        self.no_upload = no_upload
        self.do_remove = do_remove

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
    parser.add_option("-s", "--source-path", help="(required) Source path")
    parser.add_option("-b", "--bucket", help="S3 bucket to upload to")
    parser.add_option("-u", "--url", help="(required) URL of the API to notify clients")
    parser.add_option("-d", "--dest-path", help="Destination path; if unused, doesn't move files")
    parser.add_option("-n", "--no-upload", help="Don't actually upload", action="store_true", default=False)
    parser.add_option("-r", "--remove", help="If no destination is provided, delete files instead of leaving in-situe", action="store_true", default=False)
    (options, args) = parser.parse_args()

    for o in [options.source_path, options.url]:
        if not o:
            print "All arguments except --dry-run are required, see --help for the list."
            sys.exit(1)


    observer = Observer()
    handler = UploaderEventHandler(options.bucket, options.url, options.dest_path, options.no_upload, options.remove)
    observer.schedule(handler, options.source_path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
