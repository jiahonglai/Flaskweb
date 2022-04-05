import shelve


def txt2db():
    with shelve.open("./ip2as") as db:
        with open("./bdrmapit-ip2as.txt") as f:
            for line in f:
                line = line.split()
                if (int(line[2]) > 0):
                    if (line[0] not in db):
                        db[line[0]] = line[2]
                    elif (line[2] != line[3]):
                        db[line[0]] = line[2]


def updateAS():
    with shelve.open("../LGData") as db:
        with shelve.open("./ip2as") as AS:
            for key in db:
                tmp = db[key]
                IP = tmp['IP']
                if (IP in AS):
                    tmp['AS'] = AS[IP]
                    db[key] = tmp


if __name__ == "__main__":
    updateAS()