import struct
import sys
import glob
import argparse





class packet(object):
    def __init__(self,start, pbuf):

        # length of data fields (uint16_t), not counting zero pads and timestamp
        self.dlen = 106

        # extract timestamp
        self.parse_timestamp(pbuf)

        # extract data fields
        self.parse_data(pbuf)

        # interpretation of data
        self.setup_fields()


    def setup_fields(self):

        # set up data structure for field labels
        self.timestamp_fields = ["year","month","day","hour","minute","second","?"]
        self.data_fields = ["?" for i in range(self.dlen)]
        
        for i in range(25):
            self.data_fields[4 + i   ] = "resA".format(i)
            self.data_fields[4 + i + 25] = "resB".format(i)
            self.data_fields[4 + i + 50] = "resC".format(i)
            if i < 10:
                self.data_fields[4 + i + 75] = "pulse".format(i)

        self.known_fields = {
            "Reslex":1,
            "IPAP":2,
            "EPAP":3,
            "tidal_vol":99,
            "spO2_pct":102,
            "HR_BPM":103,
            "rep_rate":104}
        
        for key, val in self.known_fields.items():
            self.data_fields[val] = key

    
    def parse_timestamp(self,pbuf):

        self.timestamp = struct.unpack("HBBBBBB",pbuf[256-8:256])

        self.year = self.timestamp[0]
        self.month = self.timestamp[1]
        self.day = self.timestamp[2]
        self.hours = self.timestamp[3]
        self.minutes = self.timestamp[4]
        self.seconds = self.timestamp[5]
        

    def get_raw_secs(self):
        # seconds ignoring year and month
        hrs = self.timestamp[2]*24 + self.timestamp[3]
        secs = 3600*hrs +  self.timestamp[4]*60 + self.timestamp[5]
        return secs

    def parse_data(self, pbuf):
        # extract all 16-bit data (dlen words) from the packet
        self.data = []
        assert 2*self.dlen < len(pbuf)
        for i in range(self.dlen):
            ptr = 2*i # uint16_t, 2-byte unsigned integers
            val = struct.unpack("H",pbuf[ptr:ptr+2])
            self.data.append(val[0])

    def get_known_header_csv(self):
        # text descriptions of known values
        outstr = ""
        for key, val in self.known_fields.items():
            outstr += "{}, ".format(key)
        return outstr

    def get_known_values_csv(self):
        # print only understood values
        outstr = ""
        for key, val in self.known_fields.items():
            outstr += "{}, ".format(self.data[val])
        return outstr

    def get_all_values_csv(self):
        # print all data values whether we know what they are or not
        outstr = ""
        for i in range(1,3):
            outstr += "{}, ".format(self.data[i])
        for i in range(89,self.dlen):
            outstr += "{}, ".format(self.data[i])
        return outstr

    def get_all_values_header_csv(self):
        # print all data values whether we know what they are or not
        outstr = ""
        for i in range(1,3):
            outstr += "{}, ".format(self.data_fields[i])
        for i in range(89,self.dlen):
            outstr += "{}, ".format(self.data_fields[i])
        return outstr

    def fix_csv(self, csv_str):
        """ remove trailing spaces & comma, add newline """
        csv_str = csv_str.strip()
        if csv_str[-1] == ',':
            csv_str = csv_str[0:-1]
        return csv_str 

    def describe(self):
        #print("packet start {0:04x} dlen {1:d}".format(self.start, self.dlen))
        print("packet dlen {} flags:{} {}".format(self.dlen, 
                                                  self.get_header_csv(),
                                                  self.get_timestr_csv()))
        #print("header     {:04x}:{:04x}:{:04x}".format(self.header[1],
        #                                           self.header[2],
        #                                           self.header[3]))
        print("data:")
        print(" ".join([" {:4x}".format(x) for x in self.data[0:25]]))
        print(" ".join([" {:4x}".format(x) for x in self.data[25:50]]))
        print(" ".join([" {:4x}".format(x) for x in self.data[50:75]]))
        print(" ".join([" {:4x}".format(x) for x in self.data[75:-1]]))
        print("timestamp: {}".format(self.get_timestr()))


    def get_time_ymd_header_csv(self):
        # return time string in year, month, day format
        return ",".join(self.timestamp_fields)

    def get_time_ymd_csv(self):
        # return time string in year, month, day format
        outstr = ""
        for i in self.timestamp:
            outstr += "{:d}, ".format(i)
            
        return outstr
            
    def get_time_seconds(self):
        return self.seconds + 60*self.minutes + 3600*(self.hours + 24*(self.day -1))


    def get_10hz_csv(self, i):
        return "{}, ".format(self.data[4 + 75+i])

    def get_25hz_csv(self, i):
        outstr = "{:d}, {:d}, {:d}, ".format(self.data[4 +i],
                                             self.data[4 + 25 + i],
                                             self.data[4 + 50 + i])
        return outstr


    def csv_data_header_secs(self):
        outstr = ""
        outstr += "Time (s)"

    def csv_data_sec(self):
        # priont out csv data per packet (1hz rate)
        outstr = "{:d}, {:d}, {:d}, {:d}, {:d}, {:d}, {:d}\n".format(
            self.get_raw_secs(),
            self.IPAP,
            self.EPAP,
            self.tidal_vol,
            self.spO2_pct,
            self.HR_BPM,
            self.rep_rate)
        return outstr

    def csv_data_end(self):
        # print data in csv format
        outstr = ""
        for i in range(17): 
            outstr += "{:d}, ".format(self.data[85+i])
        outstr += "{:d} ".format(self.data[85+17])


            ## these last two are spo2 and HR?
            #for i in range(2): 
            #    outstr += ", {:d}".format(self.data[98+i])
        outstr += "\n"
        return outstr 

    def csv_data10(self):
        # print data in csv format
        outstr = ""
        for i in range(10):
            outstr += "{:d}\n".format(self.data[75+i])
        return outstr

if sys.version_info.major < 3:
    print("sorry, requires Python 3.")
    exit(1)


# default is to print out all known data at 1 hz. 

parser = argparse.ArgumentParser(
    description='Extract data from BMC RESmart raw data files')

parser.add_argument('--list_dates','-l',
                    action='store_true',
                    help='Print dates found in stored data. Suppresses other output' )

parser.add_argument('--f25_hz','-2',
                    action='store_true',
                    help='Print out all 25 Hz (flow) data. this will make output files 25x as big.' )

parser.add_argument('--f10_hz','-1',
                    action='store_true',
                    help='Print out all 10 Hz (pulse) data. this will make output files 10x as big.' )

parser.add_argument('--all_data','-a',
                    action='store_true',
                    help='Print out all 1Hz data fields known or unknown' )

parser.add_argument('--time_ymd','-y',
                    action='store_true',
                    help='Print timestamp in Y, M, D, H, M, S format')

parser.add_argument('--time_seconds','-s',
                    action='store_true',
                    help='Print timestamp in seconds since beginning of month')

parser.add_argument('--quiet','-q',
                    action='store_true',
                    help='Do not print progress and info to stderr')
parser.add_argument('output_file', nargs = '?', 
                    help='Output data CSV file',
                    default="RESmart_data.csv")
args = parser.parse_args()

# first find root

filesNNN = glob.glob('*.[0-9][0-9][0-9]')
filesNNN.sort()

packets = []
thispacket = None
packetsize = 256

for datafile in filesNNN:
    with  open(datafile, "rb") as f:
        databuff = f.read()


    state = "OUTSIDE"
    pcount = 0 # count inside packet
    int_iter = struct.iter_unpack("H", databuff) 

    p = 0 # pointer into databuff
    oldday = -1
    while p < (len(databuff) - packetsize):
        #print(i)

        val = int(struct.unpack("H",databuff[p:p+2])[0])
        thispacket = packet(p, databuff[p:p+packetsize])
        p += packetsize
        #thispacket.describe()
        packets.append(thispacket)
        #thispacket.describe()
        day = thispacket.timestamp[2]
        if day != oldday:
            oldday = day
            year = thispacket.timestamp[0]
            month = thispacket.timestamp[1]
            day = thispacket.timestamp[2]
            print("processed {:d} {:d}/{:d}".format(year, month, day))

if not args.quiet:
    print("{:d} packets found in {} files".format(len(packets), len(filesNNN)))
 

with open("foo.csv", 'w') as outf:
    last_day = -1


    for i, p in enumerate(packets):
        if args.list_dates:
            if p.day != last_day:
                print("{} {}/{}".format(p.year, p.month, p.day))
                last_day = p.day
            exit(0)

        outstr = ""

        if args.time_seconds:
            outstr += "{}, ".format(p.get_time_seconds())

        if args.time_ymd:
            outstr += p.get_time_ymd_csv()

        if args.all_data:
            outstr += p.get_all_values_csv() 
        else: 
            outstr += p.get_known_values_csv()

        if args.f10_hz:
            for i in range(10):
                frac_sec = float(p.get_time_seconds()) + float(i)/10.
                tstr = "{:.2f}, ".format(frac_sec)
                tstr += p.get_10hz_csv(i)
                outf.write(p.fix_csv(outstr + tstr) + "\n")      

        elif args.f25_hz:
            for i in range(25):
                frac_sec = float(p.get_time_seconds()) + float(i)/25.
                tstr = "{:.2f}, ".format(frac_sec)
                tstr += p.get_25hz_csv(i)
                outf.write(p.fix_csv(outstr + tstr) + "\n")      
        else:
            outf.write(p.fix_csv(outstr) + "\n")            






