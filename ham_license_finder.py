#!/usr/bin/python3

import os
import csv
import json
import time
import shutil
import logging
import hashlib

__author__ = "Jonathan Tomek"
__version__ = "1.1"
__status__ = "Production"
__description__ = "Checks FCC website for new Amateur radio operators"


def unzip(filename):
    import zipfile

    with zipfile.ZipFile(filename, "r") as zip_ref:
        zip_ref.extractall("tmp")
    dir_path = os.path.dirname(os.path.realpath(filename))

    return dir_path


def download_file(filename):
    import urllib.request

    logging.info("Downloading l_amat file")

    # Clean up old l_amat file in case it was not removed
    if os.path.exists(filename):
        logging.info("Removing old l_amat file")
        os.remove(filename)

    url = "ftp://wirelessftp.fcc.gov/pub/uls/daily/"

    try:
        with urllib.request.urlopen(url + filename) as \
                response, open(filename, "wb") as out_file:
            shutil.copyfileobj(response, out_file)

    except Exception:
        error = "Connection to FCC Server failed"
        logging.error(error)
        raise ValueError(error)


def parse_file():

    filename = "tmp/EN.dat"
    new_hams = list()

    epoch = int(os.path.getmtime(filename))
    ts = time.strftime("%Y-%m-%d", time.localtime(epoch))

    with open(filename) as f:
        hamreader = csv.reader(f, delimiter="|")
        for row in hamreader:
            ham = {
                "callsign": row[4],
                "fullname": row[7].title(),
                "firstname": row[8].capitalize(),
                "lastname": row[10].capitalize(),
                "address": row[15].title(),
                "city": row[16].capitalize(),
                "state": row[17],
                "zipcode": row[18],
                "date": ts
            }
            # Removes Clubs
            if not ham["firstname"] and not ham["lastname"]:
                continue

            new_hams.append(ham)

    return new_hams, ts


def match_zipcodes(new_hams):
    # Using Fremaptools to find Zipcodes within 40km / 25mi
    # https://www.freemaptools.com/find-zip-codes-inside-radius.htm

    matches = list()
    with open("zipcodes_25mi.txt", "r") as f:
        zipcodes = f.read().splitlines()

        for ham in new_hams:
            if ham["zipcode"] in zipcodes:
                matches.append(ham)

    return matches


def save_data(matches, today):
    # Save as JSON
    with open("new_hams_{}.json".format(today), "w") as f:
        json.dump(matches, f)

    # Save as CSV
    with open("new_hams_{}.csv".format(today), "w") as f:
        output = csv.writer(f)
        header = ['callsign', 'fullname', 'firstname', 'lastname',
                  'address', 'city', 'state', 'zipcode']
        output.writerow(header)
        for ham in matches:
            output.writerow([
                ham['callsign'],
                ham['fullname'],
                ham['firstname'],
                ham['lastname'],
                ham['address'],
                ham['city'],
                ham['state'],
                ham['zipcode']])


def valid_newfile(filename, today):
    md5s = list()
    with open("last_check.csv", "r") as check_file:
        last_check = csv.DictReader(check_file)
        for row in last_check:
            md5s.append(row["md5sum"])

    md5hash = hashlib.md5(open(filename, "rb").read()).hexdigest()
    if md5hash in md5s:
        os.remove(filename)
        return False

    with open("last_check.csv", "a") as f:
        last_check = csv.writer(f)
        last_check.writerow([today, filename, md5hash])

    return True


def cleanup(filename, ts):
    rename = "archive/{}_{}.zip".format(filename.split(".")[0], ts)
    os.rename(filename, rename)
    shutil.rmtree("tmp")


def main():
    days = ["mon", "tue", "wed", "thu", "fri", "sat"]

    hams = list()
    today = time.strftime("%Y-%m-%d", time.localtime(time.time()))

    for day in days:
        filename = "l_am_{}.zip".format(day)

        download_file(filename)

        if not valid_newfile(filename, today):
            continue

        unzip(filename)
        new_hams, ts = parse_file()
        hams.extend(match_zipcodes(new_hams))
        cleanup(filename, ts)

    logging.info("Total New Hams within 25 miles: {}".format(len(hams)))
    print("Total New Hams within 25 miles: {}".format(len(hams)))
    if hams:
        save_data(hams, today)
    print(json.dumps(hams, indent=4))


if __name__ == "__main__":
    main()
