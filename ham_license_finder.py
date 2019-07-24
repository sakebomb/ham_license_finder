#!/usr/bin/python3

import os
import csv
import json
import time
import shutil
import logging
import hashlib


def unzip(filename):
    import zipfile
    
    with zipfile.ZipFile(filename, 'r') as zip_ref:
        zip_ref.extractall('tmp')
    dir_path = os.path.dirname(os.path.realpath(filename))

    return dir_path


def download_file(filename):
    import urllib.request

    logging.info("Downloading l_amat File")

    # Clean up old l_amat file in case it was not removed
    if os.path.exists(filename):
        logging.info("Removing old l_amat File")
        os.remove(filename)

    #url = "ftp://wirelessftp.fcc.gov/pub/uls/complete/"
    url = "ftp://wirelessftp.fcc.gov/pub/uls/daily/"

    try:
        with urllib.request.urlopen(url + filename) as \
            response, open(filename, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)

    except:
        error = "Connection to FCC Server failed"
        logging.error(error)
        raise ValueError(error)

    return


def parse_file(filename):
    new_hams = list()

    epoch = int(os.path.getmtime(filename))
    ts = time.strftime('%Y-%m-%d', time.localtime(epoch))

    with open(filename) as f:
        hamreader = csv.reader(f, delimiter='|')
        for row in hamreader:
            ham = {
                'callsign':  row[4],
                'fullname':  row[7],
                'firstname': row[8],
                'lastname':  row[10],
                'address':   row[15],
                'city':      row[16],
                'state':     row[17],
                'zipcode':   row[18]
            }

            new_hams.append(ham)

    return new_hams, ts


def match_zipcodes(new_hams):
    # Using Fremaptools to find Zipcodes within 40km / 25mi 
    # https://www.freemaptools.com/find-zip-codes-inside-radius.htm

    matches = list()
    with open('zipcodes_25mi.txt', 'r') as f:
        zipcodes = f.read().splitlines()
        
        for ham in new_hams:
            if ham['zipcode'] in zipcodes:
                matches.append(ham)

    return matches


def save_data(matches):
    with open('matches.json','w') as f:
        json.dump(matches, f)


def main():
    days = ['mon','tue','wed','thu','fri','sat']

    hams = list()
    for day in days:
        filename = 'l_am_{}.zip'.format(day)
        
        download_file(filename)
        tmp_dir = unzip(filename)
        md5hash = hashlib.md5(open(filename,'rb').read()).hexdigest()

        new_ham_file = '/tmp/EN.dat'
        new_hams, ts = parse_file(tmp_dir + new_ham_file)
        shutil.rmtree(tmp_dir + '/tmp')

        matches = match_zipcodes(new_hams)

        hams.extend(matches)

        rename = "archive/{name}_{ts}.zip".format(name=filename.split(".")[0],ts=ts)
        os.rename(filename, rename) 

        with open('last_check.txt', 'a') as f:
            last_check = csv.writer(f)
            last_check.writerow([ts, filename, md5hash])

    logging.info("Total New Hams within 25 miles of Vienna: {}".format(len(hams)))
    print("Total New Hams within 25 miles of Vienna: {}".format(len(hams)))
    save_data(hams)
    print(json.dumps(hams,indent=4))


if __name__ == "__main__":
    main()
