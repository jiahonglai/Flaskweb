import urllib3

urllib3.disable_warnings()

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List
import re
import json


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
            'Connection': 'keep-alive',
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
        if (self.routerKey != ""):
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