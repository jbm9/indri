import os
import mutex
import time

class ControlLog:
    def __init__(self, tmp_dir, final_dir):
        self.tmp_dir = tmp_dir
        self.final_dir = final_dir

        self.filename = None
        self.fh = None

        self.mutex = mutex.mutex()

        self.roll()

    def _write(self, l):
        self.fh.write(l)
        self.mutex.unlock()
            
    def write(self, l):
        if l[-1] != "\n":
            l += "\n"
        self.mutex.lock(self._write, l)

    def _doroll(self, _):
        if self.fh:
            self.fh.close()
            cur_path = os.path.join(self.tmp_dir, 
                                    self.filename)

            new_path = os.path.join(self.final_dir, 
                                    self.filename)
            
            os.rename(cur_path, new_path)

        self.filename = "control_log_%d.log" % time.time()
        cl_path = os.path.join(self.tmp_dir,
                               self.filename)
        self.fh = file(cl_path, "a")
        self.mutex.unlock()

    def roll(self):
        self.mutex.lock(self._doroll, None)
