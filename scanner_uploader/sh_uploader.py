#!/usr/bin/env python


from base_uploader import BaseUploader, run_uploader

import subprocess
import shlex

class ShUploader(BaseUploader):
    TYPENAME = "sh"

    def bootstrap(self):
        self.cmd = self.config[self.config_section]["cmd"]

    def handle(self, path, filename):
        cmd = self.cmd.replace("<PATH>", path).replace("<FILENAME>", filename)

        subprocess.check_call(shlex.split(cmd))

        self.send_message({"type": "fileup", "path": filename})

        return True

if __name__ == "__main__":
    run_uploader(ShUploader)
