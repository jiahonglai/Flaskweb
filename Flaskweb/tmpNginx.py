import sqlite3
from gevent import monkey
from gevent import pywsgi

monkey.patch_all()
from flask import Flask, request, jsonify
from flask import render_template
import shelve
import os
import urllib3

urllib3.disable_warnings()
from datetime import datetime, date
from API import API
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
    data = request.get_json()
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
    data = request.get_json()
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
        record = con.execute("SELECT last_visit_time FROM visitor WHERE IP=?",
                             (IP, )).fetchone()
        nowTime = datetime.now().replace(microsecond=0)
        if (record != None):
            lastVisitTime = datetime.strptime(record[0], "%Y-%m-%d %H:%M:%S")
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
    data = request.get_json()
    keys = data['keys']
    with sqlite3.connect("Web.db") as con:
        IP = request.headers.get('X-Forwarded-For')
        record = con.execute("SELECT last_query_time, query_number FROM visitor WHERE IP=?",
                             (IP, )).fetchone()
        nowTime = datetime.now().replace(microsecond=0)
        queryNum = record[1]
        if (queryNum != 0):
            lastQueryTime = datetime.strptime(record[0], "%Y-%m-%d %H:%M:%S")
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
