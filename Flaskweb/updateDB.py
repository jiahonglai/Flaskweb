import shelve
import pandas as pd


def updatePingAPI():
    with shelve.open("LGData") as db:
        data = pd.read_csv('PingAPI.csv', encoding="utf-8")
        data[['routerKey', 'routerValue']] = data[['routerKey',
                                                   'routerValue']].fillna('')
        for index, info in data.iterrows():
            key = info['site'] + "|" + info['routerValue']
            if (key in db):
                tmp = db[key]
                tmp['routerKey'] = info['routerKey']
                tmp['method'] = info['method']
                tmp['hostKey'] = info['hostKey']
                tmp['cmdKey'] = info['cmdKey']
                tmp['data'] = info['data']
                tmp['requestPath'] = info['requestPath']
                tmp['cmdValue'] = {'ping': info['cmdValue']}
                if (info['site'] ==
                        "https://looking.house/action.php?mode=looking_glass&action="
                    ):
                    del db[key]
                    key = "https://looking.house/" + "|" + info['routerValue']
                db[key] = tmp


def updateTraceAPI():
    with shelve.open("LGData") as db:
        data = pd.read_csv('TraceAPI.csv', encoding="utf-8")
        data.columns = [
            'site', 'node', 'routerKey', 'routerValue', 'method', 'hostKey',
            'cmdKey', 'ping', 'cmdValue', 'requestPath', 'city', 'data'
        ]
        data[['routerKey', 'routerValue']] = data[['routerKey',
                                                   'routerValue']].fillna('')
        for index, info in data.iterrows():
            key = info['site'] + "|" + info['routerValue']
            if (key in db):
                tmp = db[key]
                tmp['cmdValue'].update({'traceroute': info['cmdValue']})
                db[key] = tmp

        for key in db:
            if ("https://looking.house/" in key):
                tmp = db[key]
                tmp['cmdValue'].update({'traceroute':'traceroute'})
                db[key] = tmp


def updateShowBGPRoutesAPI():
    with shelve.open("LGData") as db:
        data = pd.read_csv('ShowBGPRoutesAPI.csv', encoding="utf-8")
        data[['routerKey', 'routerValue']] = data[['routerKey',
                                                   'routerValue']].fillna('')
        for index, info in data.iterrows():
            key = info['site'] + "|" + info['routerValue']
            if (key in db):
                tmp = db[key]
                tmp['cmdValue'].update({'bgp': info['cmdValue']})
                db[key] = tmp


if __name__ == "__main__":
    updatePingAPI()
    updateTraceAPI()
    updateShowBGPRoutesAPI()