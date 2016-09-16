class CPUMeter:
    def __init__(self):
        self.last_readings = self.get_cpu_counts()

    def get_idle_percs(self):
        readings = self.get_cpu_counts()
    
        diff = self.diff_readings(self.last_readings, readings)
        self.last_readings = readings

        retval = {}
        for cpuid in diff:
            retval[cpuid] = float(diff[cpuid]["idle"])/(1+diff[cpuid]["total"])

        return retval

    def diff_readings(self, r0, r1):
        diff = {}
        for cpuid in r1:
            diff[cpuid] = {}
            for f in r1[cpuid]:
                diff[cpuid][f] = r1[cpuid][f] - r0[cpuid][f]

        return diff

    def get_cpu_counts(self):
        f = file("/proc/stat")
        lines = f.readlines()
        f.close()

        retval = {}

        for l in lines:
            if not l.startswith("cpu"):
                continue

            fields = l.split()
            cpuid = fields[0]

            numbers = map(int, fields[1:])
            retval[cpuid] = {"total": sum(numbers)}

            fields = "user nice system idle iowait irq softirq steal guest guest_nice".split()

            for f,n in zip(fields, numbers):
                retval[cpuid][f] = n

        return retval

if __name__ == "__main__":
    import time
    m = CPUMeter()

    try:
        while True:
            print m.get_idle_percs()
            time.sleep(1)
    except KeyboardInterrupt:
        pass
        
