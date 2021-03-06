#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Search lyric from the site,and put it to standard output.
'''

import argparse
import logging
import sys,io

# sites classes
from get_lyric.sites import list_scrapers,choose_scrapers
from get_lyric.common import read_config

if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')  #for unicodeerror
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--artist')
    parser.add_argument('--song')
    parser.add_argument('--sites'      
                        ,help="name of sites to search,splitted by ','.site names are displayed py 'get_lyric.py --list'")
    parser.add_argument('--proxy'
                        ,help="format is [site name=proxy url:port],splitted by ','")
    parser.add_argument('--list'        ,action='store_true'
                        ,help="print site names and exit")
    
    args=parser.parse_args()
    if args.list:
        for s in list_scrapers():
            print(s.site)
        sys.exit(0)
        
    read_config(args)
    
    logging.basicConfig(level=logging.INFO,
                        stream = open("get_lyric.log",mode="w",encoding="utf-8"))
    logging.info("argument:" + str(args))
    
    if args.artist is None or args.song is None:
        logging.info("artist and song is required.exit")
        sys.exit(0)
    
    scrapers = choose_scrapers(args.sites, args.artist, args.song)
    ret = False
    for scraper in scrapers:    
        try:
            obj = scraper(args.artist, args.song,args.proxy)
            ret=obj.get_lyric()
        except Exception as e:
            logging.error(obj.log_msg("error:[%s]" % e))
            continue

        if ret == True:
            print(obj.lyric,end="")
            break
    
    if ret==False:
        logging.info("no lyrics at all sites")
