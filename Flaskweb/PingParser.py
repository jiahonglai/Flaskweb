import re
import shelve
import requests
from API import API


class PingParser:

    def __init__(self):
        pass

    @staticmethod
    def filter(doc):
        if '<body>' in doc and '<head>' in doc:
            doc = re.sub('\{.*?\}', ' ', doc)  # 消除style
        doc = re.sub('<head>[\s\S]*</head>', ' ', doc)  # 消除head
        doc = re.sub('<footer>[\s\S]*</footer>', ' ', doc)  # 消除footer
        doc = re.sub('<[^<>]*>', ' ', doc)  # 消除label
        doc = re.sub(r'[^a-zA-Z0-9.*]', ' ', doc)  # 替换非法字符
        doc = re.sub(r'([0-9])([a-z])', r"\1 \2", doc)  # 拆开数字与字母
        doc = re.sub(r'([a-z])([0-9])', r"\1 \2", doc)
        doc = re.sub(r'  +', ' ', doc)  # 把多余空格合成1个
        return doc

    @staticmethod
    def getTotalPacket(doc):
        totalPacket = re.findall("(\d+) packets transmitted", doc,
                                 re.IGNORECASE)
        if (totalPacket == []):
            totalPacket = re.findall("(\d+) packet s transmitted", doc,
                                     re.IGNORECASE)
        if (totalPacket == []):
            totalPacket = re.findall("Sending (\d+)", doc, re.IGNORECASE)
        if (totalPacket == []):
            totalPacket = re.findall("sen[td] (\d+)", doc, re.IGNORECASE)
        if (totalPacket == []):
            totalPacket = re.findall("(\d+) packets", doc, re.IGNORECASE)
        if (totalPacket == []):
            return ""
        return totalPacket[0]

    @staticmethod
    def getSuccessRate(doc, url):
        if ("lookingglass.level3.net" in url
                or "lookingglass.centurylink.com" in url):
            successRate = re.findall("(\d+) (\d+) packets", doc)
            if (successRate == []):
                return ""
            successRate = list(map(int, list(successRate[0])))
            successRate = successRate[1] * 100 // successRate[0]
            return str(successRate) + "%"

        if ("lg.infortek.net.br" in url or "lg.openitgroup.com.br" in url):
            successRate = re.findall("(\d+) packet s transmitted (\d+)", doc)
            if (successRate == []):
                return ""
            successRate = list(map(int, list(successRate[0])))
            successRate = successRate[1] * 100 // successRate[0]
            return str(successRate) + "%"

        if ("as35908.net" in url or "customer.vpls.net" in url):
            successRate = re.findall("send (\d+) recv (\d+)", doc)
            if (successRate == []):
                return ""
            successRate = list(map(int, list(successRate[0])))
            successRate = successRate[1] * 100 // successRate[0]
            return str(successRate) + "%"

        successFlag = True
        successRate = re.findall("Success rate is (\d+)", doc)
        if (successRate == []):
            successRate = re.findall("(\d+) packet loss[^\d]", doc)
            successFlag = False
        if (successRate == []):
            successRate = re.findall("packet loss (\d+) min", doc)
            successFlag = False
        if (successRate == []):
            successRate = re.findall("(\d+) loss", doc)
            successFlag = False
        if (successRate == []):
            return ""
        if (successFlag):
            successRate = successRate[0]
        else:
            successRate = 100 - int(successRate[0])
        return str(successRate) + "%"

    @staticmethod
    def getRTT(doc, url):
        RTT = re.findall(
            "min avg max .*dev ([0-9]+\.?[0-9]*) ([0-9]+\.?[0-9]*) ([0-9]+\.?[0-9]*) ([0-9]+\.?[0-9]*) ms",
            doc)
        if (RTT == []):
            RTT = re.findall(
                "min avg max ([0-9]+\.?[0-9]*) ([0-9]+\.?[0-9]*) ([0-9]+\.?[0-9]*) ms",
                doc)
        if (RTT == []):
            RTT = re.findall(
                "min avg max ([0-9]+\.?[0-9]*) ms ([0-9]+\.?[0-9]*) ms ([0-9]+\.?[0-9]*) ms",
                doc)
        if (RTT == []):
            RTT = re.findall(
                "min rtt ([0-9]+\.?[0-9]*) ms avg rtt ([0-9]+\.?[0-9]*) ms max rtt ([0-9]+\.?[0-9]*) ms",
                doc)
        if (RTT == []):
            RTT = re.findall(
                "min ([0-9]+\.?[0-9]*) avg ([0-9]+\.?[0-9]*) max ([0-9]+\.?[0-9]*) [a-z]*dev ([0-9]+\.?[0-9]*)",
                doc)
        if (RTT == []):
            RTT = re.findall(
                "Minimum ([0-9]+\.?[0-9]*) ms Maximum ([0-9]+\.?[0-9]*) ms Average ([0-9]+\.?[0-9]*) ms",
                doc)
            if (RTT != []):
                RTT = list(RTT[0])
                tmp = RTT[1]
                RTT[1] = RTT[2]
                RTT[2] = tmp
                tmp = list()
                tmp.append(tuple(RTT))
                RTT = tmp

        if (RTT == []):
            return ""

        RTT = list(RTT[0])
        for index, value in enumerate(RTT):
            RTT[index] += ' ms'
        tmp = RTT
        RTT = {'min': tmp[0], 'avg': tmp[1], 'max': tmp[2]}
        if (len(tmp) == 4):
            RTT.update({'stddev': tmp[3]})
        return RTT

    @staticmethod
    def parse(info):
        if (info['status_code'] != 200):
            return "Request Failure"
        doc = PingParser.filter(info['resp'])
        print(doc)

        totalPacket = PingParser.getTotalPacket(doc)

        successRate = PingParser.getSuccessRate(doc, info['url'])

        RTT = PingParser.getRTT(doc, info['url'])

        result = {}
        result['total packets'] = totalPacket
        result['success rate'] = successRate
        result['RTT'] = RTT

        return str(result)


if __name__ == "__main__":
    '''pingParser = PingParser()
    with open("./test.html", "r") as f:
        s = ""
        f = f.readlines()
        for i in f:
            s += i
        info = {'url': "https:/run/", 'resp': s, 'status_code': 200}
        print(pingParser.parse(info))
    exit()
    k = 0
    f = 0
    with shelve.open("LGData", "r") as db:  #必须以只读方式，否则多用户会报错
        for key in db:
            f += 1
            record = db[key]
            info = {}
            info['site'], info['routerValue'] = key.split("|")
            if ("lg.k2telecom.net.br" in info['site']):
                print(key)
                k = 1
            else:
                k = 0

            if (k == 0): continue
            if ("looking.house" in info['site']): continue
            info['routerKey'] = record['routerKey']
            info['method'] = record['method']
            info['hostKey'] = record['hostKey']
            info['cmdKey'] = record['cmdKey']
            info['data'] = record['data']
            info['requestPath'] = record['requestPath']
            info['cmdValue'] = record['cmdValue']['ping']
            api = API(info)
            try:
                api.run("47.93.47.75")
            except Exception as e:
                print(e)
            info = {
                'url': api.url,
                'resp': api.resp,
                'status_code': api.reqstatus_code
            }
            print(api.resp)

            print(pingParser.parse(info))'''
