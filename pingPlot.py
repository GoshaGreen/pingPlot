from asyncio import as_completed
from audioop import add
import platform
import subprocess
import re
from multiprocessing import Process, Value, Array
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
import time
import os
from functools import partial

if platform.system()=='Windows':
    rePingPattern = re.compile('.*[0-9]*\.[0-9]*\.[0-9]*.[0-9]*:.*[0-9]*.*TTL=[0-9]*')
else:
    print('TODO: implement  RegEx for ping utility for OS: {}'.format(platform.system()))
    exit()
DEBUG = True

class PingPlot:
    def __init__(self):
        self.numOfValues = 15
        self.pingTimeout = 5 # sec
        self.pingFrequency = 2 # times per second
        self.addresses = []
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
            # print('before threading', time.time())
            threadsGroupNum = int((self.pingTimeout / self.pingFrequency) * 3) # X3 because trust nbody
            threadsNum = int(self.addressesSize * threadsGroupNum)
            futures = [None] * threadsNum
            threadGroupIndex = 0
            startTime = time.time()
            with ThreadPoolExecutor(threadsNum) as executor:
                while True:
                    while abs(startTime-time.time()) < (1/self.pingFrequency):
                        time.sleep(0.05)
                    startTime += (1/self.pingFrequency)
                    # print('-'*80+'{:16} {:15}, {:5}'.format('\nlets finish', time.time(), self.currentValueIndex.value))
                    self.currentValueIndex.value = int(startTime * self.pingFrequency) % self.numOfValues
                    # print('='*80+'{:16} {:15}, {:5}'.format('\nlets start', time.time(), self.currentValueIndex.value))
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
                    # print('{:16} {:15}, {:5}'.format('after submit', time.time(), self.currentValueIndex.value))
                    for addressIndex in range(self.addressesSize):
                        if len(futures) < addressIndex or futures[addressIndex] == None: continue
                        executor.submit(self.catchException, futures[threadGroupIndex + addressIndex])
                    # print('{:16} {:15}, {:5}'.format('after exception', time.time(), self.currentValueIndex.value))
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
        return pingVal

    def addPingDataCallback(self, future: Future, addressIndex: int, dataIndex: int):
        value = future.result(timeout=self.pingTimeout)
        self.setDataValue(value, addressIndex, dataIndex)
        # print('{:16} {:15}, {:5}'.format('after callback', time.time(), self.currentValueIndex.value))

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


def main():

    ## run requestor
    pp = PingPlot()
    pp.appendAddress('ya.ru')
    pp.appendAddress('google.com')
    pp.appendAddress('fe')
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

    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    import numpy as npy

    fig, ax = plt.subplots()
    xdata, ydata = [0, 1, 2], [ [0], [0], [0] ]
    ln, = plt.plot(xdata, ydata)
    ln.set_xdata(xdata)
    ln.set_ydata(ydata)
    # exit()

    def init():
        ax.set_xlim(0, pp.numOfValues)
        ax.set_ylim(-1, 150)
        return ln,

    def update(frame):
        data = pp.getDataArray(numEntries=pp.numOfValues)
        xdata = npy.array(range(len(data[0])))
        ydata = (data[0], data[1]) #data[0] # 
        ax.set_ylim(-1, max(data[0]))

        datanpy = npy.array(data).transpose()
        print(xdata.shape, datanpy.shape)
        ln.set_xdata(xdata)
        ln.set_ydata(datanpy)
        # ln.set_data(xdata, data[0])
        return ln,

    ani = FuncAnimation(fig, update, frames=range(0, pp.numOfValues),
                        init_func=init, blit=False, repeat=True)
    plt.show()

    pp.stopRequestor()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
