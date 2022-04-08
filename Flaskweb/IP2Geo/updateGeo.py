import shelve
import pandas as pd


def IPAddr2IPNum(IPAddr):
    IPAddr = IPAddr.split('.')
    IPNum = 0
    for i in range(4):
        IPNum = IPNum * 256 + int(IPAddr[i])
    return IPNum


def updateGeo():
    columns = [
        'ip_from', 'ip_to', 'country_code', 'country_name', 'region', 'city',
        'latitude', 'longitude', 'zipcode'
    ]
    useCols = [
        'ip_from', 'ip_to', 'country_name', 'city', 'latitude', 'longitude'
    ]
    chunkSize = int(1e6)
    geoDataReader = pd.read_csv("IP2Geo.csv",
                                header=None,
                                names=columns,
                                usecols=useCols,
                                iterator=True)
    chunks = []
    while (True):
        try:
            chunk = geoDataReader.get_chunk(chunkSize)
            chunks.append([chunk, len(chunk)])

        except StopIteration:
            break

    with shelve.open("../LGData") as db:
        for key in db:
            IPAddr = db[key]['IP']
            IPNum = IPAddr2IPNum(IPAddr)
            for geoData, geoDataLen in chunks:
                left = 0
                right = geoDataLen - 1
                while (left <= right):  #二分查找
                    mid = (left + right) // 2
                    if (IPNum >= geoData['ip_from'].iloc[mid]):
                        left = mid + 1
                    else:
                        right = mid - 1

                left -= 1
                if (geoData['ip_from'].iloc[left] <= IPNum
                        and IPNum <= geoData['ip_to'].iloc[left]
                        and geoData['country_name'].iloc[left] != '-'):
                    tmp = db[key]
                    tmp['latitude'] = geoData['latitude'].iloc[left]
                    tmp['longitude'] = geoData['longitude'].iloc[left]
                    tmp['country'] = geoData['country_name'].iloc[left]
                    tmp['city'] = geoData['city'].iloc[left]
                    db[key] = tmp
                    break


def updateContinent():
    with shelve.open("../LGData") as db:
        continentsData = pd.read_csv("continents.csv")
        continent = {}
        for index, item in continentsData.iterrows():
            continent[item['country']] = item['continent']

        for key in db:
            tmp = db[key]
            if (tmp.get('country') == None):
                continue
            if (continent.get(tmp['country']) == None):
                print(tmp['country'])
            else:
                tmp['area'] = continent.get(tmp['country'])
                db[key] = tmp


if __name__ == "__main__":
    updateGeo()
    updateContinent()
