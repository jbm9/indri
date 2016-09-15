#!/usr/bin/env python

import boto

from base_uploader import BaseUploader, run_uploader


class S3Uploader(BaseUploader):
    TYPENAME = "S3"

    def bootstrap(self):
        self.bucketname = self.config[self.config_section]["bucket"]

        self.c = boto.connect_s3()
        self.b = self.c.get_bucket(self.bucketname)
        bucket_location = self.b.get_location()
        if bucket_location:
            self.c = boto.s3.connect_to_region(bucket_location)
            self.b = self.c.get_bucket(self.bucketname)


    def handle(self, path, filename):
        k = boto.s3.key.Key(self.b)
        k.key = filename
        k.set_contents_from_filename(path)
        k.set_acl("public-read")

        self.send_message({"type": "fileup", "bucket": self.bucketname, "path": filename})

        return True

if __name__ == "__main__":
    run_uploader(S3Uploader)
