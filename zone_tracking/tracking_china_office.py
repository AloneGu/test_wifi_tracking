from wifi_tracking_training import get_model
import glob
import csv
import gzip
import datetime
import numpy
import re

from wifi_util.wifi_vendor import get_vendor_checker

SRC_FOLDER = '../china_office_wifi/2016-01-12'
RESULT_CSV = 'china_office_result_zone.csv'
ROUTERS = ['9c:d9:17:88:77:93', '9c:d9:17:86:63:97', '14:1a:a3:d4:3c:19']
PLC_ROUTER_DICT = {'8600063': '9c:d9:17:88:77:93', '8600068': '9c:d9:17:86:63:97', '8600168': '14:1a:a3:db:32:14',
                   '8600165': '14:1a:a3:d4:3c:19'}
ROUTERS_NUM = len(ROUTERS)


def main_process():
    KNN, zone_int_dict = get_model()
    # no duplicate value, so reverse this dictionary
    int_zone_dict = dict(zip(zone_int_dict.values(), zone_int_dict.keys()))
    file_list = glob.glob(SRC_FOLDER + '/*csv.gz')
    # mac_sn_dict : { (mac_address,time_accurate_to_10_seconds):[signal_strength according to the routers] }
    mac_sn_dict = {}
    for f in file_list:
        placement_name = re.findall("\d{7}", f)[0]
        router_bssid = PLC_ROUTER_DICT[placement_name]
        try:
            with gzip.open(f, 'rb') as fp:
                reader = csv.reader(fp)
                for row in reader:
                    # jump first row
                    if reader.line_num == 1:
                        continue
                    # process each ros
                    mac = str(row[3]).lower()
                    ssid = str(row[7])
                    time = int(row[0]) / 10 * 10
                    sn = int(row[6])
                    if router_bssid in ROUTERS:
                        index = ROUTERS.index(router_bssid)
                        tmp_key = (mac, time)
                        if tmp_key not in mac_sn_dict:
                            mac_sn_dict[tmp_key] = [-100] * ROUTERS_NUM
                        mac_sn_dict[tmp_key][index] = sn

        except Exception as e:
            print e
            print f
    fout = open(RESULT_CSV, 'w')
    writer = csv.writer(fout)
    writer.writerow(['mac', 'time'] + ROUTERS + ['zone'])
    vender_checker = get_vendor_checker()
    data_row_cache = []

    for key in mac_sn_dict:
        mac = key[0]
        if str(mac) in ROUTERS:
            continue
        vender = vender_checker.get_manuf(str(mac))
        time = datetime.datetime.utcfromtimestamp(key[1] + 8 * 60 * 60)  # transfer to local time
        x_data = numpy.array([map(int, mac_sn_dict[key])])
        predict_result = int_zone_dict[int((KNN.predict(x_data)[0]))]
        tmp_probability = max(KNN.predict_proba(x_data)[0])
        data_row_cache.append([mac, time] + mac_sn_dict[key] + [predict_result, vender])

    print 'sort the result'
    data_row_cache = sorted(data_row_cache, key=lambda x: (x[0], x[1]))

    for row in data_row_cache:
        writer.writerow(row)
    print 'finished'


if __name__ == '__main__':
    main_process()
