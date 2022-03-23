import json
import re
from urllib import response

ipv4Regex = '\\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\b'


def is_num(str):
    p = re.compile('[0-9][0-9]*$')
    if p.match(str):
        return True
    return False


def isPrivate(ip):
    segs = ip.split('.')
    if segs[0] == '10':
        return True
    if segs[0] + '.' + segs[1] == '172.16' or segs[0] + '.' + segs[
            1] == '192.168':
        return True
    return False


def is_ipv4(str):
    p = re.compile(ipv4Regex + '$')
    if p.match(str):
        return True
    return False


def contain_ipv4(seg):
    p = re.compile(ipv4Regex)
    if p.search(seg):
        return True
    return False


def is_float(str):
    return re.match('[0-9]+\.[0-9]+$', str)


class TracerouteHTMLParser:

    def __init__(self):
        pass

    @staticmethod
    def filter(doc):
        if '<body>' in doc and '<head>' in doc:
            doc = re.sub('\{.*?\}', ' ', doc)  # 是HTML页面的话就消除style系列
        doc = re.sub('<head>[\s\S]*</head>', ' ', doc)  # 消除head
        doc = re.sub('<footer>[\s\S]*</footer>', ' ', doc)  # 消除footer
        doc = re.sub('<[^<>]*>', ' ', doc)  # 消除 html label
        doc = re.sub(
            '[a-zA-Z\-][0-9a-zA-Z\-]*(\.[a-zA-Z0-9\-][a-zA-Z0-9\-]*)+', ' ',
            doc)  #消除主机名
        doc = re.sub(r'[^a-zA-Z0-9.*]', ' ', doc)  # 替换非法字符
        doc = re.sub(r'([0-9])([a-z])', r"\1 \2", doc)  # 拆开数字与字母
        doc = re.sub(r'([a-z])([0-9])', r"\1 \2", doc)
        doc = re.sub(r'  +', ' ', doc)  # 把多余空格合成1个，加速匹配4
        doc = re.sub(' ([0-9]+) ([Mm][Ss])', r" \1.0 \2", doc)  # 把整数时延转化成浮点数
        segs = [seg for seg in doc.split()
                if TracerouteHTMLParser.legal(seg)]  # 筛除不合法的字符串

        # speedup：以最后一个ms位置作尾巴
        doc = ''
        tail = 0
        for index in range(len(segs) - 1, -1, -1):
            if re.match('ms', segs[index], re.IGNORECASE):
                tail = index
                break
        doc = ' '.join(segs[:tail + 1])
        doc = re.sub('(?<= )[0-9]+\.[0-9](?= [0-9])', '', doc)
        doc = re.sub(r'  +', ' ', doc)
        return doc

    @staticmethod
    def legal(seg):
        if '*' == seg or (seg.isdigit() and int(seg) > 0 and int(seg) < 20
                          ) or is_float(seg) or is_ipv4(seg) or re.search(
                              r"^(ms|msec)$", seg, re.IGNORECASE):
            return True
        return False

    @staticmethod
    def middleResult(doc):
        return TracerouteHTMLParser.filter(doc)

    @staticmethod
    def parse(doc):
        doc = TracerouteHTMLParser.middleResult(doc)
        # speed up by replace IP
        originalIPs = re.findall(ipv4Regex, doc)
        originalRtts = re.findall('[0-9]+\.[0-9]+(?= ms)', doc)
        doc = re.sub(ipv4Regex, 'IP', doc)
        doc = re.sub('[0-9]+\.[0-9]+(?= ms)', 'rtt', doc)
        doc = ' ' + doc + ' '  # append last hop blank
        regex_unit = " (?:ms|msec|IP|rtt| |(?<= )[0-9]+(?= )|\*)+"
        regex = ""
        hops = []

        for i in range(1, 30):  # get max hopnum, 限制到30跳
            regex += '((?<= )' + str(
                i) + '(?= )' + regex_unit + ') '  # tail is a blank
            result = re.findall(regex, doc, re.IGNORECASE)
            if not result:
                break
            else:
                hops = result[0]

        matchPart = ' '.join(hops)
        forwardLength = doc.find(matchPart)
        forwardContent = doc[:forwardLength]
        IPIndex = forwardContent.count('IP')
        rttIndex = forwardContent.count('rtt')
        result = {"hops": []}

        for hop in hops:
            replacedSegs = hop.split()
            lastSegIsIP = False
            IP = ""
            record = {"hop": "", "response": []}
            resp = {}
            for seg in replacedSegs:
                if 'IP' == seg:
                    if (lastSegIsIP):
                        IPIndex += 1
                        continue
                    IP = originalIPs[IPIndex]
                    IPIndex += 1
                    lastSegIsIP = True
                elif 'rtt' == seg:
                    resp['from'] = IP
                    resp['rtt'] = originalRtts[rttIndex]
                    rttIndex += 1
                    lastSegIsIP = False
                elif '*' == seg:
                    resp['from'] = '*'
                    record['response'].append(resp)
                    resp = {}
                elif 'ms' == seg:
                    resp['rtt'] += ' ms'
                    record['response'].append(resp)
                    resp = {}
                else:
                    record['hop'] = seg

            result['hops'].append(record)
        return result

    @staticmethod
    def postClean(ret):
        ret = re.sub('(?<= )[0-9]+(?= )', ' ', ret)
        ret = re.sub('(?<= )[0-9]+(?=\|)', ' ', ret)
        ret = re.sub(' +', ' ', ret)
        return ret

    @staticmethod
    def hops2json(hops):
        ret = ""
        for hop in hops:
            ret += hop + '|'
        return TracerouteHTMLParser.postClean(ret)


class TracerouteJsonParser:

    def __init__(self):
        pass

    @staticmethod
    def legal(seg):
        if '*' == seg or seg.isdigit() or is_float(seg) or is_ipv4(
                seg) or re.search(r"^(ms|msec)$", seg, re.IGNORECASE):
            return True
        return False

    @staticmethod
    def filter(line):
        line = re.sub(
            '[a-zA-Z\-][0-9a-zA-Z\-]*(\.[a-zA-Z0-9\-][a-zA-Z0-9\-]*)+', ' ',
            line)  #消除主机名
        line = re.sub(r'[^a-zA-Z0-9.*]', ' ', line)  # 替换非法字符
        line = re.sub(r'([0-9])([a-z])', r"\1 \2", line)  # 拆开数字与字母
        line = re.sub(r'([a-z])([0-9])', r"\1 \2", line)
        line = re.sub(r'  +', ' ', line)  # 把多余空格合成1个，加速匹配4
        line = re.sub(' ([0-9]+) ([Mm][Ss])', r" \1.0 \2", line)  # 把整数时延转化成浮点数
        segs = [
            seg for seg in line.split() if TracerouteJsonParser.legal(seg)
        ]  # 筛除不合法的字符串
        line = ' '.join(segs)
        return line

    @staticmethod
    def splitDoc(doc):
        sepers = [
            '\\r\\n', '\\n\\r', '\\n', '\\r', '\r\n', '\n\r', '\r', '\n', '<br'
        ]
        superSeper = 'thujn'
        for seper in sepers:
            # tempSegs = re.split(seper,doc)
            tempSegs = doc.split(seper)
            doc = ''
            for tempSeg in tempSegs:
                doc += tempSeg + superSeper
        lines = doc.split(superSeper)
        ret = []
        for line in lines:
            ret.append(TracerouteJsonParser.filter(line).strip())
        return ret

    @staticmethod
    def parse(doc):
        lines = TracerouteJsonParser.splitDoc(doc)
        linesNum = len(lines)
        for i in range(linesNum):
            if (len(lines[i]) >= 2 and lines[i].split()[0] == '1'):
                if (i == linesNum - 1 or (len(lines[i + 1]) >= 2
                                          and lines[i + 1].split()[0] == '2')):
                    lines = lines[i:]
                    break

        result = {"hops": []}
        for line in lines:
            if (line == ''):
                continue
            replacedSegs = line.split()
            lastSegIsIP = False
            IP = ""
            record = {"hop": "", "response": []}
            record['hop'] = replacedSegs[0]
            replacedSegs = replacedSegs[1:]
            resp = {}
            for seg in replacedSegs:
                if (len(seg) > 6): #认为是IP
                    if (lastSegIsIP):
                        continue
                    IP = seg
                    lastSegIsIP = True
                elif '*' == seg:
                    resp['from'] = '*'
                    record['response'].append(resp)
                    resp = {}
                elif 'ms' == seg:
                    resp['rtt'] += ' ms'
                    record['response'].append(resp)
                    resp = {}
                else:
                    resp['from'] = IP
                    resp['rtt'] = seg
                    lastSegIsIP = False

            result['hops'].append(record)
        return result


class TracerouteParser:

    def __init__(self) -> None:
        self.jsonParser = TracerouteJsonParser()
        self.htmlParser = TracerouteHTMLParser()

    def selectParser(self, doc):
        if 'html' in doc:
            return self.htmlParser
        else:
            return self.jsonParser

    def parse(self, doc):
        parser = self.selectParser(doc)
        return parser.parse(doc)


if __name__ == "__main__":
    with open("./templates/result/2022-03-23 15:21:44.803865.html") as f:
        f = f.readlines()
        s = ""
        for i in f:
            s += i
        parser = TracerouteParser()
        print(parser.parse(s))