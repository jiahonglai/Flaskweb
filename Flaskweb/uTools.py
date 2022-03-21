def readLines(filename):
    with open(filename, mode='r', encoding='utf-8') as f:
        lines = f.readlines()
    return list(map(lambda x: x.replace('\n', ''), lines))


import random


def generateRandomTarget():
    a, b, c, d = random.randint(1,
                                254), random.randint(0, 254), random.randint(
                                    0, 254), random.randint(1, 254)
    return str(a) + '.' + str(b) + '.' + str(c) + '.' + str(d)


import json


def appendToFile(line, filename):
    line = json.dumps(line)
    with open(filename, mode='a', encoding='utf-8') as output:
        output.write(line + '\n')
