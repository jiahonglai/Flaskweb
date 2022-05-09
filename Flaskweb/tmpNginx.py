from multiprocessing import Process, cpu_count
import sqlite3
from gevent import monkey

monkey.patch_all()
from flask import Flask, request, jsonify, json
from flask import render_template
from gevent import pywsgi
import shelve
import os
import urllib3

urllib3.disable_warnings()
import requests
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime, date
import re
from ShowBGPAnalyzer import BGPpathAnalyzer
from TracerouteParser import TracerouteParser

app = Flask(__name__)


@app.route("/")
def getLGpage():
    return render_template("LG.html")


@app.route("/result/<date>/<time>")
def getHtmlResult(date, time):
    return render_template("/result/" + date + "/" + time + ".html")


pageSize = 30  # 一页显示30条记录


@app.route("/page_num", methods=["POST"])
def getPageNum():
    data = json.loads(request.form.get('data'))
    conditions = ['cmdValue', 'area', 'country']
    recordNum = 0
    with shelve.open("LGData", "r") as db:  #必须以只读方式，否则多用户会报错
        for index in db:
            record = db[index]
            satisfaction = True
            for condition in conditions:
                if (condition == "cmdValue"):
                    if (data[condition] != "All") and (
                            data[condition] not in record[condition]):
                        satisfaction = False
                        break
                else:
                    if (data[condition] != "All") and (data[condition] !=
                                                       record.get(condition)):
                        satisfaction = False
                        break

            if (satisfaction):
                recordNum += 1
        pageNum = recordNum // pageSize
        if (recordNum % pageSize != 0):
            pageNum += 1
        return str(pageNum)


@app.route("/page", methods=["POST"])
def getPage():
    data = json.loads(request.form.get('data'))
    conditions = ['cmdValue', 'area', 'country']
    recordNum = 0
    recordList = []
    startIndex = (data['page'] - 1) * pageSize
    endIndex = data['page'] * pageSize
    with shelve.open("LGData", "r") as db:  #必须以只读方式，否则多用户会报错
        for index in db:
            record = db[index]
            satisfaction = True
            for condition in conditions:
                if (condition == "cmdValue"):
                    if (data[condition] != "All") and (
                            data[condition] not in record[condition]):
                        satisfaction = False
                        break
                else:
                    if (data[condition] != "All") and (data[condition] !=
                                                       record.get(condition)):
                        satisfaction = False
                        break

            if (satisfaction):
                recordNum += 1
                if (recordNum > startIndex):
                    info = {}
                    info['URL'], info['routerValue'] = index.split('|')
                    info['AS'] = record.get("AS")
                    info['latitude'] = record.get("latitude")
                    info['longitude'] = record.get("longitude")
                    info['city'] = record.get("city")
                    for condition in conditions:
                        if (condition == "cmdValue"):
                            info["cmdValue"] = []
                            for cmdValue in record["cmdValue"]:
                                info["cmdValue"].append(cmdValue)
                        else:
                            info[condition] = record.get(condition)

                    recordList.append(info)
                    if (recordNum == endIndex):
                        break

        return jsonify(recordList)


@app.route("/country", methods=["GET"])
def getCountry():
    area = request.args.get("area")
    countryList = []
    with shelve.open("LGData", "r") as db:  #必须以只读方式，否则多用户会报错
        for key in db:
            if (area != "All" and area != db[key].get("area")):
                continue
            country = db[key].get("country")
            if (country != None and country not in countryList):
                countryList.append(country)

        countryList.sort()
        return jsonify(countryList)


class API:

    def __init__(self, info):
        self.url = info['site']
        self.headers = {
            'user-agent':
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36',
            'accept-language':
            'zh-CN,zh;q=0.9',
            'cache-control':
            'max-age=0',
            'accept':
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
        }
        if 'lg.he.net' in self.url:
            self.headers = {
                'user-agent':
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36',
                'accept-language': 'zh-CN,zh;q=0.9',
                'cache-control': 'max-age=0',
                'accept':
                'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Referer': 'https://lg.he.net/'
            }
        self.routerKey = info['routerKey']
        ##打补丁，有些路由器多种编码
        self.routerValue = self.debugroutervalue(info['routerValue'])
        self.method = info['method']
        self.hostKey = info['hostKey']
        self.cmdKey = info['cmdKey']
        self.cmdValue = info['cmdValue']
        self.reqPath = info['requestPath']
        self.data = json.loads(info['data'].replace("'", '"'))
        self.fullpath = ''
        self.resp = ''
        self.reqstatus_code = ''
        self.begintime = ''
        self.endtime = ''

    def debugroutervalue(self, info):
        dictreplace = {
            'SÃ£o Paulo (EDGE-B.SP4.SPO) IX': 'São Paulo (EDGE-B.SP4.SPO) IX',
            'Dç«¯sseldorf - DE': 'Düsseldorf - DE',
            'Sé\x81\x94o Paulo - BR': 'São Paulo - BR',
            'PoznaÅ': 'Poznań',
            'WrocÅaw': 'Wrocław',
            'GdaÅsk': 'Gdańsk',
            'Sé\x81\x94o Paulo - Core 2': 'Séo Paulo - Core 2',
            'AraÃ§atuba (EDGE-A.ARC)': 'Araçatuba (EDGE-A.ARC)',
            'IX.br SÃÂ£o Paulo': 'IX.br São Paulo',
            'SÃ£o Paulo (EDGE-A.SP2.SPO) IX': 'São Paulo (EDGE-A.SP2.SPO) IX',
            'Equinix â AS14609': 'Equinix – AS14609',
            'Telefonica Brasil â AS1888': 'Telefonica Brasil – AS18881',
            'Sé\x81\x94o Paulo - Core 1': 'São Paulo - Core 1',
            'KrakÃ³w': 'Kraków',
            'Séo Paulo - Core 2': 'São Paulo - Core 2'
        }
        if (info in dictreplace):
            return dictreplace[info]
        else:
            return info

    def keyWordsMatch(self, content, keyWords: List[str]):
        content = str(content)
        result = [wd for wd in keyWords if wd.lower() in content.lower()]
        return result != []

    def isForm(self, form):
        formKeyWords = [
            self.routerKey, 'bgp', 'route', self.cmdKey, self.hostKey
        ]
        return self.keyWordsMatch(form, formKeyWords)

    def extractForm(self, soup):
        fs = [f for f in soup.find_all('form') if self.isForm(f)]
        return fs[0] if fs else None

    def needToken(self):
        return [key for key in self.data.keys() if 'token' in key.lower()]

    @staticmethod
    def scanInput(form):
        data = {}
        for einput in form.find_all('input'):
            if 'name' in einput.attrs.keys():
                data[einput.attrs['name']] = einput.attrs.get('value', '')

        for select in form.find_all('select'):
            if 'name' in select.attrs.keys():
                select_name = select.attrs['name']
                options = select.find_all('option')
                if len(options) > 0:
                    data[select_name] = options[0].attrs.get('value', '')
                else:
                    data[select_name] = ''
        return data

    def refreshToken(self):
        tokenKeys = self.needToken()
        if tokenKeys:
            tokenKey = tokenKeys[0]
            html_doc = requests.get(self.url).text
            soup = BeautifulSoup(html_doc, 'html.parser')
            form = self.extractForm(soup)
            if form:
                newData = self.scanInput(form)
                self.data[tokenKey] = newData.get(tokenKey,
                                                  self.data[tokenKey])

    def run(self, target):
        self.refreshToken()
        requests.adapters.DEFAULT_RETRIES = 3
        s = requests.session()
        s.keep_alive = False
        # package data
        self.data[self.cmdKey] = self.cmdValue
        self.data[self.hostKey] = target
        if type(self.routerKey) != '':
            self.data[self.routerKey] = self.routerValue

        if re.search('get', self.method, re.IGNORECASE):
            if (self.url == 'https://lg.lasagna.dev'):
                fullReqPath = 'https://lg.lasagna.dev/.well-known/looking-glass/v1/ping/' + str(
                    target)
            elif (self.url == 'https://customer.vpls.net/'):
                fullReqPath = "https://customer.vpls.net/run/" + str(
                    self.routerValue) + "/ipv4/ping/" + str(target)
            elif (self.url == 'http://98.126.24.5/'
                  or self.url == 'http://lg.as35908.net/'
                  or self.url == 'http://hk.krypt.testip.xyz/'):
                fullReqPath = 'https://' + str(
                    self.routerValue) + '-lg.as35908.net/ping/ipv4/' + str(
                        target)
            else:
                fullReqPath = self.reqPath + '?'
                for k, v in self.data.items():
                    if k != '':
                        fullReqPath += str(k) + '=' + str(v) + '&'
                fullReqPath = fullReqPath[:-1]  # remove last &
            self.fullpath = fullReqPath

            self.begintime = str(datetime.now())
            print(self.begintime, " get ", self.fullpath)
            with s.get(fullReqPath,
                       headers=self.headers,
                       verify=False,
                       stream=True,
                       timeout=360) as req:
                self.resp = req.text.replace('\n', ' ').replace('\t',
                                                                ' ').replace(
                                                                    '\r', ' ')
                self.reqstatus_code = req.status_code
                self.endtime = str(datetime.now())
        else:  # post
            if 'sharktech.net' in self.url or 'https://alice.ja.net' in self.url or 'http://lg.sentrian.net.au' in self.url or 'https://lg.launtel.net.au' in self.url:  # 字符串做postData，特殊处理
                self.data = str(self.data).replace("'", '"')
            self.fullpath = self.reqPath + str(self.data)
            self.begintime = str(datetime.now())
            print(self.begintime, " post ", self.fullpath)
            with s.post(self.reqPath,
                        self.data,
                        headers=self.headers,
                        verify=False,
                        stream=True,
                        timeout=360) as req:
                self.resp = req.text.replace('\n', ' ').replace('\t',
                                                                ' ').replace(
                                                                    '\r', ' ')
                self.reqstatus_code = req.status_code
                self.endtime = str(datetime.now())


visitorNum = 0


def initialize():
    global visitorNum
    if (os.path.exists("VisitorNumber.txt")):
        with open("VisitorNumber.txt") as f:
            visitorNum = int(f.readline())

    with sqlite3.connect("Web.db") as con:
        con.execute('''CREATE TABLE IF NOT EXISTS visitor
                    (IP char(40) NOT NULL,
                    last_query_time date DEFAULT 0,
                    query_number int default 0,
                    last_visit_time date NOT NULL,
                    PRIMARY KEY (IP))''')


@app.before_request
def countVisitor():
    print(request.headers.get('X-Forwarded-For'))
    global visitorNum
    with sqlite3.connect("Web.db") as con:
        IP = request.headers.get('X-Forwarded-For')
        record = con.execute("SELECT * FROM visitor WHERE IP=?",
                             (IP, )).fetchone()
        nowTime = datetime.now().replace(microsecond=0)
        if (record != None):
            lastVisitTime = datetime.strptime(record[3], "%Y-%m-%d %H:%M:%S")
            dayDelta = nowTime.date() - lastVisitTime.date()
            if (dayDelta.days > 0):
                visitorNum += 1
        else:
            con.execute("INSERT INTO visitor(IP,last_visit_time) VALUES (?,?)",
                        (
                            IP,
                            datetime.now().replace(microsecond=0),
                        ))
            visitorNum += 1

        con.execute("UPDATE visitor SET last_visit_time=? WHERE IP=?",
                    (nowTime, IP))
        con.commit()

        with open("VisitorNumber.txt", "w") as f:
            f.write(str(visitorNum))

@app.route("/visitor_num", methods=["GET"])
def getVisitorNum():
    return jsonify(visitorNum)


deltaTime = 60  #两次查询的间隔(s)
totalQueryNum = 100  #一天最多查询测量点个数


@app.route("/api/query", methods=["POST"])
def query():
    queryDate = str(date.today())
    queryTime = str(datetime.now())[11:]
    data = json.loads(request.form.get('data'))
    keys = data['keys']
    with sqlite3.connect("Web.db") as con:
        IP = request.headers.get('X-Forwarded-For')
        record = con.execute("SELECT * FROM visitor WHERE IP=?",
                             (IP, )).fetchone()
        nowTime = datetime.now().replace(microsecond=0)
        queryNum = record[2]
        if (queryNum != 0):
            lastQueryTime = datetime.strptime(record[1], "%Y-%m-%d %H:%M:%S")
            secondDelta = nowTime - lastQueryTime
            if (secondDelta.seconds < deltaTime):
                return jsonify({'Info': '两次查询间隔应大于60秒'})

            dayDelta = nowTime.date() - lastQueryTime.date()
            if (dayDelta.days > 0):
                queryNum = 0
            if (totalQueryNum == queryNum):
                return jsonify({'Info': '今天已达到测量上限'})

            leftNum = totalQueryNum - (queryNum + len(keys))
            if (leftNum < 0):
                return jsonify({
                    'Info':
                    '最多还能选择' + str(totalQueryNum - queryNum) + '个测量点，请重新选择'
                })

        con.execute("UPDATE visitor SET query_number=? WHERE IP=?",
                    (queryNum + len(keys), IP))

        con.execute("UPDATE visitor SET last_query_time=? WHERE IP=?",
                    (nowTime, IP))
        con.commit()

    cmdValue = data['cmdValue']
    parameter = data['parameter']
    with shelve.open("LGData", "r") as db:  #必须以只读方式，否则多用户会报错
        content = "<head><title>Result</title></head>"
        for key in keys:
            record = db[key]
            info = {}
            info['site'], info['routerValue'] = key.split("|")
            info['routerKey'] = record['routerKey']
            info['method'] = record['method']
            info['hostKey'] = record['hostKey']
            info['cmdKey'] = record['cmdKey']
            info['data'] = record['data']
            info['requestPath'] = record['requestPath']
            info['cmdValue'] = record['cmdValue'][cmdValue]
            api = API(info)
            api.run(parameter)

            content += "URL: &nbsp" + info['site']
            content += "&nbsp&nbsp&nbsp router: &nbsp" + info[
                'routerValue'] + '<br><br>'
            if (cmdValue == "ping" or data['type'] == "raw"):
                content += api.resp
            else:
                if (cmdValue == "bgp"):
                    bgpInfo = {}
                    bgpInfo['Key'] = info['site']
                    bgpInfo['Status_code'] = api.reqstatus_code
                    bgpInfo['Responsecontent'] = api.resp
                    analyzer = BGPpathAnalyzer(bgpInfo)
                    content += analyzer.getJsonData()
                elif (cmdValue == "traceroute"):
                    tracerouteParser = TracerouteParser()
                    content += tracerouteParser.parse(api.resp)
            content += '<hr>'

        if (data['showHtml'] == "True"):
            filePath = "./templates/result/" + queryDate
            if (not os.path.exists(filePath)):
                os.makedirs(filePath)
            with open(filePath + "/" + queryTime + ".html", "w") as f:
                f.write(str(content))

            return jsonify("/result/" + queryDate + "/" + queryTime)
        else:
            return jsonify(content)


if __name__ == '__main__':
    initialize()
    server = pywsgi.WSGIServer(('127.0.0.1', 8000), app)
    server.serve_forever()
