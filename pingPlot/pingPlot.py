import platform
import subprocess
import re
from multiprocessing import Process, Value, Array
from concurrent.futures import ThreadPoolExecutor, Future
import time
import os
from functools import partial

if platform.system()=='Windows':
    rePingPattern = re.compile('.*[0-9]*\.[0-9]*\.[0-9]*.[0-9]*:.*[0-9]*.*TTL=[0-9]*')
else:
    print('TODO: implement  RegEx for ping utility for OS: {}'.format(platform.system()))
    exit()
DEBUG = False

class PingPlot:
    def __init__(self, settingsFile='settings.txt'):
        self.numOfValues = 60
        self.pingTimeout = 5 # sec
        self.pingFrequency = 2 # times per second
        self.addresses = list()
        self.loadSettings(settingsFile)
        self.currentValueIndex = Value('i', 0)
        self.requestorProcess = None
        self.initData()
        self.initRequestor()

    def initData(self):
        self.addressesSize = len(self.addresses)
        self.dataArraySize = self.addressesSize * self.numOfValues
        self.dataArray = Array('i', self.dataArraySize)

    def initRequestor(self):
        requestorAlive = False
        if self.requestorProcess and self.requestorProcess.is_alive(): 
            requestorAlive = True
            self.stopRequestor()
        self.requestorProcess = Process(target=self.requestorFunc)
        if requestorAlive: self.startRequestor()

    def startRequestor(self):
        self.requestorProcess.start()

    def stopRequestor(self):
        self.requestorProcess.kill()

    def requestorFunc(self):
        try:
            if len(self.addresses) == 0: return
            threadsGroupNum = int((self.pingTimeout / self.pingFrequency) * 3) # X3 because tRust nbody
            threadsNum = int(self.addressesSize * threadsGroupNum)
            futures = [None] * threadsNum
            threadGroupIndex = 0
            startTime = time.time()
            with ThreadPoolExecutor(threadsNum) as executor:
                while True:
                    while abs(startTime-time.time()) < (1/self.pingFrequency):
                        time.sleep(0.05)
                    startTime += (1/self.pingFrequency)
                    self.currentValueIndex.value = int(startTime * self.pingFrequency) % self.numOfValues
                    threadGroupIndex = (threadGroupIndex + 1) % threadsGroupNum
                    # set data to zero before run
                    for addressIndex in range(self.addressesSize):
                        self.setDataValue(0, addressIndex)
                    for addressIndex in range(self.addressesSize):
                        dataIndex=self.currentValueIndex.value
                        addData = partial(self.addPingDataCallback, addressIndex=addressIndex, dataIndex=dataIndex)
                        future = executor.submit(self.ping, addressIndex)
                        future.add_done_callback(addData)
                        futures[threadGroupIndex + addressIndex] = future
                    for addressIndex in range(self.addressesSize):
                        if len(futures) < addressIndex or futures[addressIndex] == None: continue
                        executor.submit(self.catchException, futures[threadGroupIndex + addressIndex])
        except Exception as e:
            print(e)

    def appendAddress(self, address: str) -> str:
        self.addresses.append(address)
        self.initData()
        self.initRequestor()
        return self.addresses[-1]

    def removeAddressIndex(self, index) -> str:
        address = self.addresses.pop(index)
        self.initData()
        self.initRequestor()
        return address

    def removeAddress(self, address: str) -> str:
        self.addresses.remove(address)
        self.initData()
        self.initRequestor()

    def filterNonDigits(string: str) -> str:
        result = ''
        for char in string:
            if char in '1234567890':
                result += char
        return result

    def catchException(self, future: Future):
        exception = future.exception()
        if exception: print('exception:', exception)

    def pingDumb(self, addressIndex) -> int:
        dataIndex = self.currentValueIndex.value
        time.sleep(0.1*addressIndex)
        if addressIndex == 0: return 0
        return int(time.time()*10)%1000

    def ping(self, addressIndex) -> int:
        numOption = '-n' if platform.system()=='Linux' else '-n'
        command = ['ping', numOption, '1', self.addresses[addressIndex]]
        pingVal = -1
        try:
            commandOutput = subprocess.check_output(command).decode('cp1251')
            for row in commandOutput.split('\n'):
                if not rePingPattern.match(row): continue
                srow = re.split(' |<|>|=', row)
                pingVal = int(PingPlot.filterNonDigits(srow[-3]))
        except Exception as e:
            if DEBUG : print(e)
            pingVal =5000
        return pingVal

    def addPingDataCallback(self, future: Future, addressIndex: int, dataIndex: int):
        value = future.result(timeout=self.pingTimeout)
        self.setDataValue(value, addressIndex, dataIndex)

    def getDataArray(self, startEntry=None, numEntries=None) -> list:
        if startEntry == None: startEntry = self.currentValueIndex.value
        # startEntry = 0
        if numEntries == None: numEntries = self.numOfValues
        data = list()
        for addressIndex in range(self.addressesSize):
            values = list()
            for dataIndexRaw in range(min(self.numOfValues, numEntries)):
                dataIndex = (-dataIndexRaw + startEntry) % self.numOfValues
                values.append(self.getDataValue(addressIndex, dataIndex))
            data.append(values)
        return data

    def getDataValue(self, addressIndex, dataIndex=None) -> int:
        if dataIndex == None:
            dataIndex = self.currentValueIndex.value
        return int(self.dataArray[self.numOfValues*addressIndex+dataIndex])

    def setDataValue(self, value, addressIndex, dataIndex=None):
        if dataIndex == None:
            dataIndex = self.currentValueIndex.value
        self.dataArray[self.numOfValues*addressIndex+dataIndex] = value

    def incrementDataIndex(self):
        self.currentValueIndex.value += 1
        self.currentValueIndex.value %= self.numOfValues

    def loadSettings(self, fileName):
        self.addresses = list()
        if os.path.isfile(fileName):
            with open(fileName, 'r') as f:
                for row in f.readlines():
                    if row.startswith('address:'):
                        address = str(row.split(':')[1].replace(' ', '').replace('\n',''))
                        self.addresses.append(address)
                    elif row.startswith('numOfValues:'):
                        numOfValues = int(row.split(':')[1].replace(' ', '').replace('\n',''))
                        self.numOfValues = numOfValues
                    elif row.startswith('pingTimeout:'):
                        pingTimeout = int(row.split(':')[1].replace(' ', '').replace('\n',''))
                        self.pingTimeout = pingTimeout
                    elif row.startswith('pingFrequency:'):
                        pingFrequency = int(row.split(':')[1].replace(' ', '').replace('\n',''))
                        self.pingFrequency = pingFrequency
                    else:
                        print('Settings not recognized: \"{}\"'.format(row))
        else:
            print('Settings cannot be loaded: file not found: \"{}\"'.format(fileName))

    def storeSetings(self):
        with open('settings.txt', 'w') as f:
            for address in self.addresses:
                f.write('address:{}\n'.format(address))
            f.write('numOfValues:{}\n'.format(self.numOfValues))
            f.write('pingTimeout:{}\n'.format(self.pingTimeout))
            f.write('pingFrequency:{}\n'.format(self.pingFrequency))

def main():

    ## run requestor
    pp = PingPlot()
    pp.startRequestor()

    ## do cli
    # TO_PRINT=True
    # if TO_PRINT : print('==== GUI')
    # while True:
    #     if TO_PRINT : os.system('cls')
    #     if TO_PRINT : print('print data. currentValueIndex: ', pp.currentValueIndex.value)
    #     # print line
    #     data = pp.getDataArray(numEntries=15)
    #     for addressesData in data:
    #         for value in addressesData:
    #             # print('{:8}'.format(getDataFromArray(addressIndex, dataIndex, dataArray, addressesSize)), end='')
    #             if TO_PRINT : print('{:4}'.format(value), end='')
    #             pass
    #         if TO_PRINT : print()
    #     time.sleep(0.2)

    ## GUI
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import numpy as npy
    import tkinter

    window = tkinter.Tk()
    window.title('PingPlot')
    ws = window.winfo_screenwidth()
    wh = window.winfo_screenheight()
    width = 300
    height = 200
    window.geometry('{}x{}+{}+{}'.format(width, height, ws-width, wh-height-100))
    window.attributes('-topmost', True)
    def clouser():
        plt.close('all')
        pp.stopRequestor()
        window.destroy()
    window.protocol("WM_DELETE_WINDOW", clouser)

    MAX_PING_VALUE_PLOT = 1000
    # def plot():
    fig, ax = plt.subplots()
    xdata, ydata = [], []
    ax.set(xlim=(0, pp.numOfValues), ylim=(0,MAX_PING_VALUE_PLOT))
    plots = [ax.plot(xdata, ydata) for x in pp.addresses]
    ax.legend(pp.addresses)
    def update(frame):
        data = pp.getDataArray(startEntry = pp.currentValueIndex.value-1, numEntries=pp.numOfValues-1)
        maxPingValue = 0
        ax.legend(['{:<16}:{:>4}ms '.format(x, data[i][0]) for i,x in enumerate(pp.addresses)],prop={'size': 6, 'family': 'monospace'})
        for ind, (ln,) in enumerate(plots):
            # assert size of lines, and data dim
            xdata = npy.array(range(len(data[ind])))
            ydata = npy.array(data[ind])
            maxPingValue = min(max([maxPingValue] + ydata), MAX_PING_VALUE_PLOT)
            ln.set_data(xdata, ydata)
        ax.set(ylim=(-1,maxPingValue))
    ani = FuncAnimation(fig, update, frames=range(0, pp.numOfValues), blit=False, repeat=True)
    canvas = FigureCanvasTkAgg(fig, master = window)
    canvas.draw()
    canvas.get_tk_widget().pack()

    window.mainloop()

    pp.stopRequestor()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
