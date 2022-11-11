import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import datetime
from scipy.interpolate import interp1d
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

# Set plot style
def setStyle():
    plt.style.use('seaborn-talk')
    plt.rcParams['lines.linewidth'] = 1
    plt.rcParams['figure.figsize'] = [10, 5]
    plt.rc('font',**{'family':'sans-serif','sans-serif':['Liberation Sans']})

class GaugeList():
    def __init__(self, filename:str):
        self.names = readGaugeList(filename)
        self.namesDict = {idx: el for idx, el in enumerate(self.names)}

    def gaugeName(self, i:int) -> str:
        return self.names[i-1]

    def searchGauge(self, name:str) -> int:
        match = process.extractOne(name, self.namesDict)
        return match[-1]+1

# Assume that each line has the format
# 1   - 94.985000 29.681667 ! 8770613  ! NOAA_NOS ! Morgans Point
def readGaugeList(filename:str) -> [str]:
    names = []
    with open(filename) as f:
        l = f.readline()
        nstae = int(l.split()[1])
        for i in range(nstae):
            l = f.readline()
            stationName = l.split('!')[-1].strip()
            names.append(stationName)
    return names

def convertGaugeName(name:str) -> str:
    # Use all lowercase and replace space with underscore
    s = name.lower()
    s = s.replace(" ", "_")
    return s


def getStation(file1:str, st:int) -> ([float],[float]):
    elev1 = []

    with open(file1) as f1:
        l1 = f1.readline()
        l1 = f1.readline()

        # Get timestep info
        info = l1.split()
        skip = float(info[3])
        dt = float(info[2]) / skip

        l1 = f1.readline()

        for lineno, line in enumerate(f1):
            lines = line.split()
            if lines[0] == str(st):
                x = float(lines[1])

                # If dry, set to zero
                if x < -1000:
                    x = 0.

                elev1.append(x)

    time = np.arange(len(elev1))*dt*skip/86400.

    return time, np.array(elev1)

'''Reads a CSV gauge file in NOAA format and returns
a time array and an array of water level
'''
def getGauge(filename, offset=12):
    elev = []
    #file = root + '/' + gauges[gauge][0] + ".csv"

    with open(filename) as f1:
        l1 = f1.readline()
        i = 0
        for lineno, line in enumerate(f1):
            lines = line.split(',')
            #print(lines[-1])
            if lines[-1].rstrip() == '\"-\"':
                #break
                #if '-' not in lines[-2]:
                if lines[-2] == '\"-\"':
                    elev.append(np.nan)
                else:
                    l = lines[-2].strip('\"')
                #print(l)
                    elev.append(float(l))
            else:
                elev.append(float(lines[-1].rstrip().strip('\"')))

            # Get the time increment from the first 2 rows of data
            if i == 0:
                t1 = datetime.datetime.strptime(lines[1].strip('\"'),'%H:%M')
            if i == 1:
                t2 = datetime.datetime.strptime(lines[1].strip('\"'),'%H:%M')

            i = i + 1

    # time increment in seconds
    dt = (t2 - t1).total_seconds()
    of = int(offset*60*60/dt)
    elev = elev[of:]
    # time axis in days
    time = np.arange(len(elev))*dt/86400.
    return time, np.array(elev)


class Storm():
    def __init__(self, root:str, files:dict, gauges:GaugeList):
        self.root = root.rstrip("/")
        self.files = files
        self.gauges = gauges


    def plot(self, station, *args, plot_gauge=True, adjustMean=False, shift=0, offset=12, timeframe=[]):
        self.f = plt.figure()

        # Get gauge name
        stationName = self.gauges.gaugeName(station)
        plt.title(stationName)

        # If we have gauge data, plot it too
        # Assume the file is named gaugeN.csv
        #filename = self.root + '/' + self.gauges[station][0] + ".csv"
        gaugeFile = self.root + '/gauge_' + str(station) + ".csv"
        if plot_gauge:
            try:
                gtime, gelev = getGauge(gaugeFile, offset=offset)
            except Exception as e:
                hasGauge = False
                print(e)
            else:
                hasGauge = True
                if timeframe:
                    id1 = (np.abs(time - timeframe[0])).argmin()
                    id2 = (np.abs(time - timeframe[1])).argmin()
                else:
                    id1 = 0
                    id2 = None
                plt.plot(gtime[id1:id2:3], gelev[id1:id2:3], '--', markersize=7, label='Gauge data')
                # Interpolate whichever has fewer data and calculate RMSE

        # If time series specified, only plot those
        if args:
            keys = args
        else:
            keys = self.files.keys()

        # Loop over the avaialble time series and plot each one
        for key in keys:
            time, elev = getStation(self.root + '/' + key, station)
            label = self.files[key]

            # Calculate RMSE compared to gauge data
            if hasGauge and adjustMean:
                # First truncate the gauge data
                gtime_t = gtime[gtime < np.max(time)]
                gelev_t = gelev[gtime < np.max(time)]

                interp = interp1d(time, elev)
                newDatum = interp(gtime_t)

                diff = gelev_t - newDatum
                # Remove NaNs
                diff = diff[~np.isnan(diff)]
                meanErr = np.mean(diff)
                # adjust the time series
                elev = elev + meanErr
                print("Adjustment: %.3f m" % meanErr)
                label = self.files[key]+ ", adjustment: %.3f m" % meanErr

            if timeframe:
                id1 = (np.abs(time - timeframe[0])).argmin()
                id2 = (np.abs(time - timeframe[1])).argmin()
            else:
                id1 = 0
                id2 = None


            # Specified shift in elevation
            elev = elev + shift
            if abs(shift) > 0:
                label = label + ", adjustment: %.3f m" % shift

            plt.plot(time[id1:id2], elev[id1:id2], label=label)


        # Plot appearance configuration
        plt.legend(loc='best', framealpha=0.0)
        plt.xlabel('Time (days)', fontsize=15)
        plt.ylabel('Surface elevation (m)', fontsize=15)
        plt.xticks(fontsize=13)
        plt.yticks(fontsize=13)
        plt.show()

    def plotFuzzy(self, name, *args):
        index = self.gauges.searchGauge(name)
        self.plot(index, *args)

    def save(self, name):
        self.f.savefig(self.root + '/' + name, bbox_inches="tight", dpi=300)

    # Deprecated
    # def export(self, station):
    #     for key in self.files.keys():
    #         time, elev = getStation(self.root + '/' + key, station)
    #         np.savetxt('%s/%s_%s.csv' % (self.root, key, self.gauges[station][0]), np.vstack((time,elev)).T)
