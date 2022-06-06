import json
import random
import shelve
from time import sleep
import datetime
import os
import sys

sys.path.append("../")
from API import API
from PingParser import PingParser

suffixList = {}


def dfsSuffix(x, y, n):
    if (x == n):
        return
    suffixList[x].append(y + '0')
    suffixList[x].append(y + '1')
    dfsSuffix(x + 1, y + '0', n)
    dfsSuffix(x + 1, y + '1', n)


def IP2Bin(IP):
    binIP = ""
    for i in IP.split('.'):
        binIP += (bin(int(i))[2:]).rjust(8, '0')  #rjust 左侧补0对齐
    return binIP


def IP2Oct(IP):
    octIP = ""
    for i in range(0, 24, 8):
        octIP += str(int(IP[i:i + 8], 2)) + '.'
    octIP += str(int(IP[24:32], 2))
    return octIP


def getIP():
    with open("rdns_decided.json", "r") as f:
        data = json.load(f)
        maxSufLen = 0
        for i in data:
            IP, prefixLen = i.split('/')
            maxSufLen = max(maxSufLen, 32 - int(prefixLen))

        suffixList[0] = ['']
        for i in range(1, maxSufLen + 1):
            suffixList[i] = []

        dfsSuffix(1, "", maxSufLen + 1)

        IPList = []
        for i in data:
            IP, prefixLen = i.split('/')
            prefixLen = int(prefixLen)
            binIP = IP2Bin(IP)[:prefixLen]
            for suffix in suffixList[32 - prefixLen]:
                octIP = IP2Oct(binIP + suffix)
                IPList.append(octIP)

        random.shuffle(IPList)
        with open("IPList.txt", "w") as l:
            l.write('\n'.join(IPList))


def pingData():
    pingParser = PingParser()
    with shelve.open("../LGData", "r") as db:
        with open("IPList.txt", "r") as f:
            totalData = {}
            for IP in f:
                IP = IP.replace('\n', '')
                for key in db:
                    record = db[key]
                    info = {}
                    info['site'], info['routerValue'] = key.split("|")
                    info['routerKey'] = record['routerKey']
                    info['method'] = record['method']
                    info['hostKey'] = record['hostKey']
                    info['cmdKey'] = record['cmdKey']
                    info['data'] = record['data']
                    info['requestPath'] = record['requestPath']
                    info['cmdValue'] = record['cmdValue']['ping']
                    api = API(info)
                    try:
                        api.run(IP)
                    except Exception as e:
                        print(e)
                    data = {}
                    data['site'] = info['site']
                    data['router'] = info['routerValue']
                    data['router IP'] = record['IP']
                    data['begin time'] = api.begintime
                    data['end time'] = api.endtime
                    info = {
                        'url': api.url,
                        'resp': api.resp,
                        'status_code': api.reqstatus_code
                    }
                    data['result'] = pingParser.parse(info)
                    if (totalData.get(IP)):
                        print(totalData[IP])
                        totalData[IP].append(data)
                        print(totalData[IP])
                    else:
                        totalData[IP] = [data]
                    nowDate = datetime.date.today()
                    filePath = "../datasets/ping-data/" + str(
                        nowDate.year) + "/" + str(nowDate.month)
                    if (not os.path.exists(filePath)):
                        totalData.clear()
                        os.makedirs(filePath)

                    with open(filePath + "/" + str(nowDate) + ".json",
                              "w") as w:
                        json.dump(totalData, w)

                    sleep(5)


if __name__ == "__main__":
    pingData()