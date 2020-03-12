#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib.request
import re
import os
import csv
import os.path
import socket

saved_main_page = 'mainpage.txt'
search_list = []


def get_main_page():
    global saved_main_page
    mainpage = urllib.request.urlopen('https://www.lego.com/zh-cn/service/buildinginstructions')
    html_code = mainpage.read().decode('utf-8')
    with open(saved_main_page, 'w') as f:
        f.write(html_code)


def decode_main_page():
    global saved_main_page
    with open(saved_main_page, 'r') as f:
        current_line = f.readline()
        while current_line:
            if current_line.find('data-search-themes=') != -1:
                fill_search_list(current_line)
                break
            else:
                current_line = f.readline()


def fill_search_list(mapinfo):
    titielist = re.split(r'"},{"', mapinfo)
    for title in titielist:
        m = re.search(r'Label":"((?<=").*?(?="))","Key":"(\d{3,5}-\d{3,5})', title)
        if m is not None:
            url_key = str(m.group(2))
            theme = re.sub('[\W_]+', '', m.group(1))
            search_list.append((theme, url_key))
        else:
            print(title, "not match")
    print('searching...', search_list)


def put_page_to_file(url, filename, first_page):
    subpage = urllib.request.urlopen(url)
    html_code = subpage.read().decode('utf-8')
    open_type = 'a'
    if first_page:
        open_type = 'w'
    header = ''
    with open(filename, open_type, encoding='utf-8') as f:
        m = re.search(r'"moreData":(true|false),"products":\[((?<="products":\[).*?(?=totalCount))', html_code)
        # body start after "products":\[, end before "totalCount"'
        if m is not None:
            header = m.group(1)
            body = m.group(2)
            f.write(body)
            if header == 'true':
                return False
            else:
                return True
        else:
            print('not match')


def get_all_lego_instructions():
    global search_list
    get_main_page()
    decode_main_page()
    for info in search_list:
        decode(info[0], info[1])
        print('decode', info[0])


def decode(theme, key):
    finished = False
    page = 0
    if not os.path.exists(theme):
        os.mkdir(theme)
    filename = './' + theme + '/' + theme + '.txt'
    first_page = True
    while not finished:
        url = 'https://www.lego.com//service/biservice/searchbytheme?fromIndex=' \
              + str(page) + '&onlyAlternatives=false&theme=' + key
        finished = put_page_to_file(url, filename, first_page)
        page += 10
        first_page = False
    get_jpg_and_pdf_list(filename)


def get_png_file(product):
    pic = re.findall(r'((?<="frontpageInfo":").*?(?="))', product)
    pic = list(set(pic))
    return pic


def get_jpg_and_pdf_list(file_name):
    csv_rows = []
    with open(file_name, 'r', encoding='utf-8') as f:
        products_info = f.read()
        product_info_list = re.split(r'productId":', products_info)
        for product in product_info_list:
            m = re.match(r'"(\d+)"', product)
            if m is not None:
                key = m.group(1)
                name = re.sub('[\W_]+', '', re.search(r'((?<="productName":").*?(?="))', product).group(1))
                pic = re.search(r'((?<="productImage":").*?(?="))', product).group(1)
                if re.match(r'.*?jpg$', pic) is None:
                    print("no valid jpg file get all .png file for", key)
                    pic = get_png_file(product)
                    print(pic)

                pdf_str = re.findall(r'((?<=V29).*?(?=.pdf"))', product)
                pdf_str += re.findall(r'((?<=V. 29).*?(?=.pdf"))', product)
                pdf_str += re.findall(r'((?<=V.29).*?(?=.pdf"))', product)
                pdf = [re.search(r'(.*)pdfLocation":"(.*)', x).group(2) + '.pdf' for x in pdf_str]
                if not pdf:
                    pdf_str = re.findall(r'((?<=pdfLocation":").*?(?=.pdf"))', product)
                    pdf = [x + '.pdf' for x in pdf_str]
                if not pdf:
                    pdf = re.findall(r'((?<=pdfLocation":").*?(?="))', product)
                    print("try get lost pdf for", key)
                pdf = list(set(pdf))
                year = re.search(r'((?<="launchYear":).*?(?=}))', product).group(1)
                saved_file_name = year + '_' + name + '_' + key
                csv_rows.append([saved_file_name, pic, pdf])
    csv_file = file_name[:-4] + '.csv'
    with open(csv_file, 'w', encoding='utf-8', newline='') as f2:
        csv_writer = csv.writer(f2)
        csv_writer.writerows(csv_rows)


def safeurlretrive(url, name):
    try:
        urllib.request.urlretrieve(url, name)
    except socket.timeout as e1:
        count = 1
        while count <= 5:
            try:
                urllib.request.urlretrieve(url, name)
                break
            except socket.timeout:
                print('Reloading for %d time' % count)
                count += 1
        if count > 5:
            print("downloading ", url, "failed!")
    except urllib.error.HTTPError as e2:
        print(e2)


def download_lego_instructions(csv_file, dirname):
    with open(csv_file, 'r') as f:
        row = csv.reader(f, delimiter=',')
        for info in row:
            saved_pic_name = dirname + info[0] + '.jpg'
            target_pic = info[1]
            # for some jpg file not exist in v1.0 so put before file exist check
            if re.match(r'.*?jpg$', target_pic) is None:
                print(saved_pic_name, "not valid, get png")
                k = 1
                target_png_list = re.sub(r'\[|\]|\'', '', target_pic).split(',')
                for png in target_png_list:
                    print(png)
                    if png == '':
                        print("no png file")
                        break
                    saved_png_name = dirname + info[0] + '_' + str(k) + '.png'
                    if not os.path.isfile(saved_png_name):
                        print("file ", saved_png_name, 'finished!')
                        safeurlretrive(png, saved_png_name)
                    else:
                        print("file ", saved_png_name, 'already exist!')
                    k += 1
            elif not os.path.isfile(saved_pic_name):
                safeurlretrive(target_pic, saved_pic_name)

            i = 1
            target_pdf_list = re.sub(r'\[|\]|\'', '', info[2]).split(',')

            for pdf in target_pdf_list:
                if pdf == '':
                    print("no pdf file")
                    break
                saved_pdf_name = dirname + info[0] + '_' + str(i) + '.pdf'
                if not os.path.isfile(saved_pdf_name):
                    safeurlretrive(pdf, saved_pdf_name)
                    print("file ", saved_pdf_name, 'finished!')
                else:
                    print("file ", saved_pdf_name, 'already exist!')
                i += 1


def test():
    get_all_lego_instructions()
    for info in search_list:
        theme = info[0]
        dirname = './' + theme + '/'
        file = dirname + theme + '.csv'
        print('downloading', file, '...')
        download_lego_instructions(file, dirname)
