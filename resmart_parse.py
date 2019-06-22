import struct
import sys
import glob
import argparse
import datetime


class packet(object):
    """ Holds data for one 256-byte packet from the raw (numerical
    extension) RESmart data files. Also methods for parsing the data """

    def __init__(self,start, pbuf):
        """ given pbuf list of bytes, parse out the data"""

        assert len(pbuf) >= 256

        # length of data fields (uint16_t), not counting zero pads and timestamp
        self.dlen = 106

        # extract timestamp
        self.parse_timestamp(pbuf)

        # extract data fields
        self.parse_data(pbuf)

        # generate human-readable labels
        self.setup_labels()

        if self.data[self.known_fields["spO2_pct"]] > 0:
            self.has_pulse = True
        else:
            self.has_pulse = False
        

    def setup_labels(self):
        """ These are human-readable labels for the headers of .csv files"""
        # set up data structure for field labels
        self.timestamp_fields = ["year","month","day","hour","minute","second","?"]
        # default label is "?" for unknown data field
        self.data_fields = ["?" for i in range(self.dlen)]
        
        # first 85 fields are 25 Hz and 10 Hz measurements of pressure/flow
        for i in range(25):
            self.data_fields[4 + i   ] = "resA".format(i)
            self.data_fields[4 + i + 25] = "resB".format(i)
            self.data_fields[4 + i + 50] = "resC".format(i)
            if i < 10:
                self.data_fields[4 + i + 75] = "pulse".format(i)
                
        # some data fields are known, label them
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
        """ the timestamp is the last 8 bytes of every packet"""
        self.timestamp = struct.unpack("HBBBBBB",pbuf[256-8:256])

        # for readability and convenience, parse out individual fields.
        self.year = self.timestamp[0]
        self.month = self.timestamp[1]
        self.day = self.timestamp[2]
        self.hour = int(self.timestamp[3])
        self.minute = self.timestamp[4]
        self.second = self.timestamp[5]
        
        self.date = datetime.date(self.year,self.month,self.day)
        self.ordinal = self.date.toordinal()
        self.datestr = self.date.isoformat()

    def parse_data(self, pbuf):
        """  extract all 16-bit uint16_t data (dlen words) from the packet"""
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
        # remove trailing spaces & comma, add newline 
        csv_str = csv_str.strip()
        if csv_str[-1] == ',':
            csv_str = csv_str[0:-1]
        return csv_str 

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
        return self.second + 60*self.minute + 3600*(self.hour + 24*(self.ordinal))
    def get_10hz_csv(self, i):
        return "{}, ".format(self.data[4 + 75 + i])

    def get_25hz_csv(self, i):
        #These fields are arrays of 25 values/second, something to do with
        # respiration. Last one is cleanest -- filtered?
        outstr = "{:d}, {:d}, {:d}, ".format(self.data[4 + i],
                                             self.data[4 + 25 + i],
                                             self.data[4 + 50 + i])
        return outstr

   

#### methods for a collection of packets
def s2HMS(seconds):
    # should refactor this with datetime
    #return a string giving hours minutes seconds from seconds
    hours = int(seconds/3600.)
    minutes = int((seconds%3600)/60.)
    return"{:02d}:{:02d}".format(hours,minutes)

def get_day_info(packets):
    # given a list of packets, return a symbolic string of contents
    # one char per hour, '.' if no data, '+' if flow data, '0' if heartrate
    # should refactor this by date
    hstr = ""
    pptr = 0

    datestr = packets[0].datestr
    hour = -1
    # 24 chars, one for each hour, for graphical representation of data
    hstr = ["." for i in range(24)]
    infostr = ""
    daysecs = 0
    has_pulse = False
    for p in packets:

        daysecs += 1
        if p.has_pulse:
            has_pulse = True

        if p.hour > hour:
            hour = p.hour
            if has_pulse:
                hstr[hour] = 'O'
                has_pulse = False
            else: 
                hstr[hour] = '+'

        if p.datestr != datestr:
            infostr += (datestr + " " + "".join(hstr) +  \
                        " {}\n".format(s2HMS(daysecs)))
            hstr = ["." for i in range(24)]
            daysecs = 0
            hour = -1
            datestr = p.datestr

    infostr += (datestr + " " + "".join(hstr) +  \
                " {}\n".format(s2HMS(daysecs)))
    return infostr

######################## main program starts here

if sys.version_info.major < 3:
    print("sorry, requires Python 3.")
    exit(1)


parser = argparse.ArgumentParser(
    description='Extract data from BMC RESmart raw data files')

parser.add_argument('--info','-i',
                    action='store_true',
                    help='Prints readable summary of data and dates to stdout.' )

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
                    help='Print timestamp in seconds since beginning of year')

parser.add_argument('--quiet','-q',
                    action='store_true',
                    help='Do not print progress and info to stderr')

parser.add_argument('output_file', nargs = '?', 
                    help='Output data CSV file, careful will overwrite existing data.',
                    default="RESmart_data.csv")

parser.add_argument('--dates', '-d',  nargs = '+', 
                    help='select date range in YYYY-MM-DD format. Single date is one day, two dates are start and end of time range.',
                    default=[])

args = parser.parse_args()



start_date = None
end_date = None
if len(args.dates) > 0:
    try:
        start_date = datetime.datetime.strptime(args.dates[0], '%Y-%m-%d').date()
    except ValueError:
        raise ValueError("Incorrect -d date format, should be YYYY-MM-DD")
        exit()

if len(args.dates) > 1:
    try:
        end_date = datetime.datetime.strptime(args.dates[1], '%Y-%m-%d').date()
    except ValueError:
        raise ValueError("Incorrect -d date format, should be YYYY-MM-DD")
        exit()


# Should probably ensure these files all have the same root...
filesNNN = glob.glob('*.[0-9][0-9][0-9]')
filesNNN.sort()

packets = []
thispacket = None
packetsize = 256


for datafile in filesNNN:
    with  open(datafile, "rb") as f:
        databuff = f.read()

    oldday = -1
    p = 0 # pointer into byte array
    while p < (len(databuff) - packetsize):
        #print(i)

        val = int(struct.unpack("H",databuff[p:p+2])[0])
        thispacket = packet(p, databuff[p:p+packetsize])
        p += packetsize
        packets.append(thispacket)

        if thispacket.day != oldday and not args.quiet:
            if thispacket.date == start_date:
                print("Found start date {}.".format(start_date.isoformat()))
            oldday = thispacket.day
            print("reading data from {}".format(thispacket.datestr))

if not args.quiet:
    print("{:d} packets found in {} files".format(len(packets), len(filesNNN)))
 

if args.info:
    print(get_day_info(packets))


if start_date is None:
    #default to beginning of data
    start_date = packets[0].date
else:
    if end_date is None:
        # if only start date is specified, use only that date
        end_date = start_date

if end_date is None:
    #default to end of data
    end_date = packets[-1].date 

#print(start_date)
#print(end_date)

with open(args.output_file, 'w') as outf:
    # read data 
    
    day = -1
    for i, p in enumerate(packets):

        if p.date >= start_date and p.date <= end_date:


            if p.ordinal != day and not args.quiet:
                day = p.ordinal
                print("Writing {} data to {}".format(p.datestr,
                                                     args.output_file))

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






