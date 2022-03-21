import re
from flask import jsonify
import pandas as pd
import os
import json
import math


class BGPpathAnalyzer:
    def __init__(self, info):
        self.key = {}
        self.key[info['Key']] = {'as': '', 'aspath': [], 'bestaspath': []}
        if (pd.isnull(info['Responsecontent'])):
            self.key = "Analyze Errro!"
            return
        if ('{"result":' == str(info['Responsecontent'])[:10]):
            doc = str(json.loads(info['Responsecontent'])['result']).lower()
        elif ('https://lg.lasagna.dev' in info['Key']):
            doc = str(','.join(
                json.loads(
                    info['Responsecontent'])['data']['output'])).lower()
        elif ('http://ip6.ch/' in info['Key']):
            doc = str((json.loads(
                info['Responsecontent'][41:-2])['result'])).lower()
        elif ('https://lookingglass.pnw-gigapop.net/lookingglass/embedded'
              in info['Key'] or ('.teraswitch.com' in info['Key']
                                 and 'fremont_ca_edge-1' in info['Key'])
              or 'http://lg.sentrian.net.au/' in info['Key']
              or 'https://lg.atman.pl' in info['Key']
              or 'https://lg.skyline.net.id' in info['Key']
              or 'https://lg.itandtel.at/' in info['Key']):
            doc = str((json.loads(info['Responsecontent'])['output'])).lower()
        else:
            doc = str(info['Responsecontent']).lower()

        ##有些URL没有返回正确结果
        if (info['Status_code'] != 200
                or ('0.0.0.0/0' in doc and ':0.0.0.0/0' not in doc)
                or 'name="captcha"' in doc or 'bgp not active' in doc
                or 'placeholder="security code"' in doc
                or "filehandle isn't open" in doc
                or 'unrecognized command found at \^ position' in doc
                or 'error: wrong parameter found at' in doc
                or 'network not in table' in doc
                or 'https://www.google.com/recaptcha/api.js' in doc
                or "filehandle isn't open error" in doc
                or 'are you a robot?' in doc or 'forgot password?' in doc
                or 'password incorrect' in doc
                or 'records for 8.8.8.8 is not found' in doc
                or 'access denied' in doc or 'connection refused' in doc
                or 'bgp routing table information for vrf default' in doc
                or 'error:problem connecting to' in doc
                or 'command failed' in doc or 'telnet error' in doc
                or 'cannot connect to router' in doc
                or '>get another captcha <' in doc
                or 'network does not exist' in doc
                or 'network not found' in doc or 'invalid router' in doc
                or 'spam detected' in doc or '{"html":"\n"}' in doc
                or 'https://lg.polsri.ac.id' in info['Key']
                or 'rate limit exceeded' in doc
                or 'please enter the ip in a cidr format' in doc
                or 'you have too many active queries' in doc):
            self.key = "Analyze Errro!"
            return

        ##剔除掉一些无关的网页元素
        doc = doc.replace('<font color="#ff0000">', ' ').replace(
            '</font>', ' ').replace('<font color=red>', ' ').replace(
                ', (received & used)',
                ' ').replace(', (received from a rr-client)', ' ').replace(
                    ', (received-only)',
                    ' ').replace('<font color="#4e7fb6">', ' ').replace(
                        '<font size="3">', ' ').replace(
                            ', (received from <b>a</b></a> rr-client)', ' ')
        doc = doc.replace('<span style=""color:#ff0000"">', ' ').replace(
            '<span style="color:#ff0000">',
            ' ').replace('</span>',
                         ' ').replace(', (received &amp; used)', ' ').replace(
                             '<span style=color:#ff0000>', ' ').replace(
                                 '<font color="#554640">',
                                 ' ').replace('&nbsp;', ' ').replace(
                                     ', (received from a rr-client)',
                                     ' ').replace(', imported path from', ' ')
        doc = re.sub(', \(received from <a (.*?)</a> (rr-client|rs-client)\)',
                     ' ', doc)
        doc = re.sub(', \(aggregated by \d+ (?:[0-9]{1,3}\.){3}[0-9]{1,3}\)',
                     ' ', doc)

        if ('https://customer.vpls.net/' in info['Key']):
            aspath = []
            for dictinfo in json.loads(info['Responsecontent'])["result"]:
                aspath.append(dictinfo['aspath'])
        elif ('https://alice.ja.net/' in info['Key']
              or 'https://lg.edgeuno.com' in info['Key']
              or ('teraswitch.com' in info['Key']
                  and 'fremont_ca_edge-1' not in info['Key'])
              or 'https://lg.softdados.net' in info['Key']
              or 'https://lg.ateltelecom.com.br' in info['Key']):
            aspath = []
            for dictinfo in json.loads(
                    info['Responsecontent'])["output"]['routes']:
                if (dictinfo['as_path'] != []):
                    aspath.append(dictinfo['as_path'])
        elif ('http://98.126.24.5' in info['Key']
              or 'http://lg.as35908.net' in info['Key']
              or 'http://hk.krypt.testip.xyz' in info['Key']):
            for dictinfo in json.loads(info['Responsecontent']):
                aspath.append(dictinfo['aspath'])
        elif (re.compile(
                r'<pre class="pre-scrollable">bird (?:[0-9]{1}\.){2}[0-9]{1} ready.'
        ).search(doc)):
            aspath = self.specialbirdready(doc)
        elif ('https://lg.cdt.cz' in info['Key']
              or 'https://lg.milecom.ru' in info['Key']
              or 'https://lg.goetel.net' in info['Key']):
            aspath = self.specialcdtcase(doc)
        elif ('https://lg.conectrj.com.br' in info['Key']):
            aspath = self.specialconectrj(doc)
        elif ('https://lg.nmmn.com' in info['Key']):
            aspath = self.specialnmmn(doc)
        else:
            aspath = self.parseaspath(doc)

        if (aspath != []):
            self.key[info['Key']]['aspath'] = aspath
            try:
                if ('https://customer.vpls.net/' in info['Key']):
                    for dictinfo in json.loads(
                            info['Responsecontent'])["result"]:
                        if (dictinfo['best'] == True):
                            bestpath = dictinfo['aspath']
                elif ('http://98.126.24.5' in info['Key']
                      or 'http://lg.as35908.net' in info['Key']
                      or 'http://hk.krypt.testip.xyz' in info['Key']):
                    for dictinfo in json.loads(info['Responsecontent']):
                        if (dictinfo['best'] == True):
                            bestpath = dictinfo['aspath']
                else:
                    bestpath = self.parsebestpath(doc, aspath)
                self.key[info['Key']]['bestaspath'] = bestpath
            except IndexError as e:
                print(e)
                print(print(info['Key']))

        else:
            if ('8.8.8.0/24' in doc):
                print(info['Key'])

    def specialbirdready(self, doc):
        listaspath = []
        pattern = re.compile(r'\[(as\d+ )*as\d+i\]')
        aspath = pattern.search(doc)
        doc1 = doc
        while (aspath):
            list1 = aspath.group()
            left = re.findall('as(\d+) ', list1, re.S | re.M)
            right = re.findall('as(\d+)i', list1, re.S | re.M)
            listaspath.append(list(filter(None, left + right)))
            doc1 = doc1[aspath.end():]
            aspath = pattern.search(doc1)
        return listaspath

    def specialnmmn(self, doc):
        listaspath = []
        pattern = re.compile(
            r'(<span (.(?!<span))*?>(\d+)\s*)+\n\s*(?:[0-9]{1,3}\.){3}[0-9]{1,3}'
        )
        aspath = pattern.search(doc)
        doc1 = doc
        while (aspath):
            list1 = aspath.group()
            list1 = re.sub(
                '\s+', ' ',
                re.sub('<span (.(?!<span))*?>', ' ',
                       list1.replace('\n', ' '))).strip()
            listaspath.append(list1.split(' ')[:-1])
            doc1 = doc1[aspath.end():]
            aspath = pattern.search(doc1)
        return listaspath

    def specialcdtcase(self, doc):
        listaspath = []

        pattern = re.compile(r'none\s+(0|-)(\n)*\s+(\d+ )+\s*(-|\n)')
        aspath = pattern.search(doc)
        doc1 = doc
        while (aspath):
            list1 = aspath.group()
            list1 = re.sub('\s+', ' ', list1[:-1]).strip()
            if ('none 0' in list1):
                listaspath.append(list1.split('none 0')[1].strip().split(' '))
            elif ('none -' in list1):
                listaspath.append(list1.split('none -')[1].strip().split(' '))
            doc1 = doc1[aspath.end():]
            aspath = pattern.search(doc1)
        return listaspath

    def specialconectrj(self, doc):
        listaspath = []
        pattern = re.compile(r'(\d+ )+\s*\d+d')
        aspath = pattern.search(doc)
        doc1 = doc
        while (aspath):
            list1 = aspath.group()
            listaspath.append(
                re.sub('\s+', ' ', list1).strip().split(' ')[:-1])
            doc1 = doc1[aspath.end():]
            aspath = pattern.search(doc1)
        return listaspath

    def parseaspath(self, doc):
        listaspath = []
        #最长匹配
        patternlist = [
            re.compile(
                r'<b>bgp :: as path</b>\s*</td>\s*<td>\s*(\d+ )*(\d+)+\s*</td>'
            ),
            re.compile(
                r'(as-path|as_path)\s*(:)*\s*(\d+ )*(\d+)+\s*\n*\s*(</b>|,|bgp|</code>|communities)'
            ),  #as-path 1221 15169,  AS_PATH: 15169              COMMUNITIES
            re.compile(
                r'bgp.as_path:\s*(\d+ )*(\d+)+\s*(<br|,\s*bgp.large_community)'
            ),  #bgp.as_path: 15169 <br
            re.compile(
                r'bgp.as_path:\s*(\d+\s*)*(<a (.(?!<a))*?>\s*(\d+)\s*</a>\s*)*(\d+\s*)*bgp.next_hop'
            ),  #BGP.as_path: <a href=""/whois?q=15169"" class=""whois"">15169</a>
            re.compile(
                r'refresh epoch \d+\s*\n*\s*(\d+\s*)*(<a (.(?!<a))*?>\s*(\d+)\s*</a>\s*)*(\d+\s*)*\n*\s*(?:[0-9]{1,3}\.){3}[0-9]{1,3}'
            ),  #refresh epoch 11  202032 <A onMouseOver=""window.status='InternetONE (RIPE)'; return true"" HREF=""https://stat.ripe.net/44160"" TARGET=_lookup>44160</A> <A onMouseOver=""window.status='GOOGLE (ARIN)'; return true"" HREF=""http://www.sixxs.net/tools/whois/?AS15169"" TARGET=_lookup>15169</A>     77.220.74.101
            re.compile(
                r'as path:\s+(\d+\s*)*(<a (.(?!<a))*?>\s*(\d+)\s*</a>\s*)*(\d+\s*)*[ie](,)* '
            ),  #AS path: 1221 <A title=""GOOGLE (ARIN)"" HREF=""http://whois.arin.net/rest/asn/AS15169/pft"" TARGET=_lookup>15169</A> I,
            re.compile(
                r'bgp-as-path="\s*(\d+\s*)*(<a (.(?!<a))*?>\s*(\d+)\s*</a>\s*(,)*\s*)*(\d+\s*)*"'
            ),  #bgp-as-path="<a href="http://noc.hsdn.org/aswhois/as15169" target="_blank">15169</a>"
            re.compile(
                r'(<a (.(?!<a))*?>\s*(\d+)\s*</a>\s*)+(\d+\s*)*(<br>)*\n*\s*(?:[0-9]{1,3}\.){3}[0-9]{1,3}'
            ),  # <a href=""https://bgp.he.net/AS57695"" target=""_blank"">57695</a> <a href=""https://bgp.he.net/AS15169"" target=""_blank"">15169</a> 2110 166.1.1.1,
            re.compile(
                r'(<a (.(?!<a))*?>\s*(\d+)\s*</a>\s*)+(\d+\s*)*\n*\s*(i|e|origin igp)(,)* '
            ),  # <a href=""https://bgp.he.net/AS57695"" target=""_blank"">57695</a> <a href=""https://bgp.he.net/AS15169"" target=""_blank"">15169</a> 2110 i,
            re.compile(
                r'(<a (.(?!<a))*?>\s*(\d+)\s*\([A-Za-z]+\)</a>\s*)+(\d+\s*)*\n*\s*(community|origin-as)'
            ),  # <a onmouseover="window.status='google (arin)'; return true">15169(google)</a>    community:
            re.compile(
                r'\s+(\d+ )*(\d+)+\s*(<br>)*\n*\s+(?:[0-9]{1,3}\.){3}[0-9]{1,3}'
            ),  #15169\n 201.1.1.1
            re.compile(r'(\d+ )+[ie](,)*\s+'),  #15169 i,
            re.compile(
                r'(\s+[A-Za-z0-9_-]+\s\[\d+\])+\s*(?:[0-9]{1,3}\.){3}[0-9]{1,3}'
            ),  # google [15169] 111.22.2.2
            re.compile(
                r'\s+(\d+ )*(\d+)+\s*<br />\s+(?:[0-9]{1,3}\.){3}[0-9]{1,3}'
            ),  # 1221 15269 <br /> 1.1.1.1
            re.compile(r'\s+(\d+ )*(\d+)+\s*<br>\s+origin igp'
                       ),  # <p>  15169<br>        origin igp,
        ]

        if (not re.compile(
                r'\(aggregated by\s+(\d+ )*(\d+)+\s*\n*\s+(?:[0-9]{1,3}\.){3}[0-9]{1,3}\)'
        ).search(doc)):
            for i in range(0, len(patternlist)):
                pattern = patternlist[i]
                aspath = pattern.search(doc)
                doc1 = doc

                while (aspath):
                    list1 = aspath.group()
                    doc = doc.replace(list1, ' ')
                    if i == 0:
                        listaspath.append(
                            re.sub('\s+', ' ',
                                   list1.split('<td>')[1].split('</td>')
                                   [0]).strip().split(' '))
                    elif i == 1:
                        listaspath.append(
                            re.sub(
                                '\s+', ' ',
                                re.sub(
                                    '(as-path|as_path)\s*(:)*', ' ',
                                    re.sub('(</b>|,|bgp|</code>|communities)',
                                           ' ', list1.replace(
                                               '\n',
                                               ' ')))).strip().split(' '))
                    elif i == 2:
                        listaspath.append(
                            re.sub(
                                '\s+', ' ',
                                re.sub('(<br|,\s*bgp.large_community)', ' ',
                                       list1.split('bgp.as_path:')
                                       [1])).strip().split(' '))
                    elif i == 3:
                        list1 = re.sub(
                            '\s+', ' ',
                            re.sub('bgp.as_path:', ' ',
                                   re.sub('bgp.next_hop', ' ',
                                          list1))).strip()
                        if ('<a' in list1 and '</a' in list1):
                            left = list1.split('<a')[0].strip().split(' ')
                            right = list1.split(
                                '</a>')[len(list1.split('</a>')) -
                                        1].strip().split(' ')
                            middle = re.findall(r'>\s*(\d+)\s*</a>', list1,
                                                re.S | re.M)
                            listaspath.append(
                                list(filter(None, left + middle + right)))
                        else:
                            listaspath.append(
                                list(filter(None, list1.split(' '))))
                    elif i == 4:
                        list1 = re.sub(
                            '\s+', ' ',
                            re.sub(
                                'refresh epoch \d+\s*\n*\s*', ' ',
                                re.sub('(?:[0-9]{1,3}\.){3}[0-9]{1,3}', ' ',
                                       list1.replace('\n', ' ')))).strip()
                        if ('<a' in list1 and '</a' in list1):
                            left = list1.split('<a')[0].strip().split(' ')
                            right = list1.split(
                                '</a>')[len(list1.split('</a>')) -
                                        1].strip().split(' ')
                            middle = re.findall(r'>\s*(\d+)\s*</a>', list1,
                                                re.S | re.M)
                            listaspath.append(
                                list(filter(None, left + middle + right)))
                        else:
                            listaspath.append(
                                list(filter(None, list1.split(' '))))
                    elif i == 5:
                        list1 = re.sub(
                            '\s+', ' ',
                            re.sub('[ie](,)* ', ' ',
                                   re.sub('as path:', ' ', list1))).strip()
                        if ('<a' in list1 and '</a' in list1):
                            left = list1.split('<a')[0].strip().split(' ')
                            right = list1.split(
                                '</a>')[len(list1.split('</a>')) -
                                        1].strip().split(' ')
                            middle = re.findall(r'>\s*(\d+)\s*</a>', list1,
                                                re.S | re.M)
                            listaspath.append(
                                list(filter(None, left + middle + right)))
                        else:
                            listaspath.append(
                                list(filter(None, list1.split(' '))))
                    elif i == 6:
                        list1 = re.sub(
                            '\s+', ' ', re.sub('bgp-as-path="', ' ',
                                               list1[:-1])).strip()
                        if ('<a' in list1 and '</a' in list1):
                            left = list1.split('<a')[0].strip().split(' ')
                            right = list1.split(
                                '</a>')[len(list1.split('</a>')) -
                                        1].strip().split(' ')
                            middle = re.findall(r'>\s*(\d+)\s*</a>', list1,
                                                re.S | re.M)
                            listaspath.append(
                                list(filter(None, left + middle + right)))
                        else:
                            listaspath.append(
                                list(filter(None, list1.split(' '))))
                    elif i == 7:
                        list1 = re.sub(
                            '\s+', ' ',
                            re.sub(
                                '(?:[0-9]{1,3}\.){3}[0-9]{1,3}', ' ',
                                list1.replace('\n',
                                              ' ').replace('<br>',
                                                           ' '))).strip()
                        left = re.findall(r'>\s*(\d+)\s*</a>', list1,
                                          re.S | re.M)
                        right = list1.split('</a>')[len(list1.split('</a>')) -
                                                    1].strip().split(' ')
                        listaspath.append(list(filter(None, left + right)))
                    elif i == 8:
                        list1 = re.sub(
                            '\s+', ' ',
                            re.sub('(i|e|origin igp)(,)* ', ' ',
                                   list1.replace('\n', ' '))).strip()
                        left = re.findall(r'>\s*(\d+)\s*</a>', list1,
                                          re.S | re.M)
                        right = list1.split('</a>')[len(list1.split('</a>')) -
                                                    1].strip().split(' ')
                        listaspath.append(list(filter(None, left + right)))
                    elif i == 9:
                        listaspath.append(
                            re.findall(r'>\s*(\d+)\s*\([A-Za-z]+\)<', list1,
                                       re.S | re.M))
                    elif i == 10:
                        listaspath.append(
                            re.sub(
                                '\s+', ' ',
                                list1.replace('\n', ' ').replace(
                                    '<br>', ' ')).strip().split(' ')[:-1])
                    elif i == 11:
                        if ('0 ' in list1):
                            list1 = list1.split('0 ')[1]
                        listaspath.append(
                            re.sub('[ie](,)*\s+', ' ',
                                   list1).strip().split(' '))
                    elif i == 12:
                        listaspath.append(
                            re.findall(r'\[(\d+)\]', list1, re.S | re.M))
                    elif i == 13:
                        listaspath.append(
                            re.sub(
                                '\s+', ' ',
                                list1.split('<br />')[0]).strip().split(' '))
                    elif i == 14:
                        listaspath.append(
                            re.sub('\s+', ' ',
                                   list1.split('<br>')[0]).strip().split(' '))

                    doc1 = doc1[aspath.end():]
                    aspath = pattern.search(doc1)

        if ('aggregated by ' in doc):
            patternlist1 = [
                re.compile(
                    r'(\s+[A-Za-z0-9_-]+\s\[\d+\])+\s*, \(aggregated by (.*?)\)\s+(?:[0-9]{1,3}\.){3}[0-9]{1,3}'
                )
            ]
            for i in range(0, len(patternlist1)):
                pattern = patternlist1[i]
                aspath = pattern.search(doc)
                doc1 = doc
                while (aspath):
                    list1 = aspath.group()
                    if i == 0:
                        listaspath.append(
                            re.findall(r'\[(\d+)\]', list1, re.S | re.M))
                    doc1 = doc1[aspath.end():]
                    aspath = pattern.search(doc1)
        return listaspath

    def parsebestpath(self, doc, listpath):
        listbestpath = []
        num = -1
        bstpath = [
            re.findall(r'available,\s*best #(\d+)\s*\)', doc, re.S | re.M),
            re.findall(r'available,\s*best #(\d+)\s*,(.*?)\)', doc,
                       re.S | re.M),
            re.findall(r'available,\s*best #(\d+)\s*<(.*?)\)', doc,
                       re.S | re.M),
            re.findall(r'available,\s*<b>best #(\d+)\s*<(.*?)\)', doc,
                       re.S | re.M)
        ]

        for i in range(0, len(bstpath)):
            path = bstpath[i]
            if (path):
                if (i == 2):
                    num = int(path[0][0])
                else:
                    num = int(path[0][0])

        if (num != -1):
            listbestpath.append(listpath[num - 1])
        elif ('* = both' in doc):
            listbestpath.append(listpath[0])
        return listbestpath

    def getJsonData(self):
        return str(self.key)
