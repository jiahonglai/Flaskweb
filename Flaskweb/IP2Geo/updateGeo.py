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
    geoData = pd.read_csv("IP2Geo.csv", header=None)
    geoData.columns = columns
    geoDataLen = len(geoData)
    with shelve.open("../LGData") as db:
        for key in db:
            IPAddr = db[key]['IP']
            IPNum = IPAddr2IPNum(IPAddr)
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
                    and IPNum <= geoData['ip_to'].iloc[left]):
                tmp = db[key]
                tmp['latitude'] = geoData['latitude'].iloc[left]
                tmp['longitude'] = geoData['longitude'].iloc[left]
                tmp['country'] = geoData['country_name'].iloc[left]
                tmp['city'] = geoData['city'].iloc[left]
                db[key] = tmp


if __name__ == "__main__":
    updateGeo()