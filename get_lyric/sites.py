# -*- coding: utf-8 -*-

import io
import logging
import re
import urllib

from bs4 import element,Comment
from requests import Session
from robobrowser import RoboBrowser
from get_lyric.common import is_all_ascii,remove_unwanted_chars

def list_scrapers():
    scrapers = [
            lyrics_az,
            j_lyric_net,
            petitlyrics_com,
            www_lyricsfreak_com,
            #letssingit_com,
            #genius_com,
            www_azlyrics_com
            ]
    return scrapers

def get_scraper_from_name(name):
    scrapers=list_scrapers()
    for scraper in scrapers:
        if scraper.site == name:
            return scraper
    return None


def choose_scrapers(sites,artist,song):
    """
    :param sites: name of sites,splitted by ','
    :returns: array of scraper classes
    """

    if sites is not None:
        scrapers=[]
        for site in sites.split(','):
            scraper = get_scraper_from_name(site)
            if scraper:
                scrapers.append(scraper)
    else:
        scrapers = list_scrapers()
    
    if not is_all_ascii(artist) or not is_all_ascii(song):
        scrapers = [s for s in scrapers if not s.ascii_only]
    
    if len(scrapers)==0:
        logging.warn("no scrapers")
    
    return scrapers


class scraper_base:
    '''
    base class for scraping
    '''
    def __init__(self,artist,song,p_proxy):
        self.artist = self.remove_unwanted_chars(artist)
        self.song = self.remove_unwanted_chars(song)
        
        session = None
        
        #setting proxy
        if p_proxy is not None:
            arr = p_proxy.split(',')
            for ent in arr:
                m= re.match('(.+)=([\d\.\:]+)',ent)
                if m:
                    site = m.group(1)
                    proxy = m.group(2)
                    if site==self.site:
                        logging.info(self.log_msg("use proxy:"+proxy))
                        session = Session()
                        session.proxies = {'http': proxy,'https':proxy}
                        break
        
        self.browser = RoboBrowser(parser="html.parser",
                                   session=session,
                                   user_agent='Mozilla Firefox',
                                   tries=5)
        
    def log_msg(self,msg):
        #msg = "%s:site:[%s]artist:[%s]song:[%s]" % (msg,self.site,self.artist,self.song)
        msg = "%s:site:[%s]" % (msg,self.site)
        return msg
            

    def get_text(self,node,buf,remove_cr=True):
        '''
        retreive texts under node of beautifulsoup
        
        :param buf: StringIO buffer to output text
        '''    
        if isinstance(node,Comment):
            return  #ignore comment
        if isinstance(node,element.Tag):
            if node.name == "br":
                buf.write("\n")
            for e in node.contents:
                self.get_text(e,buf,remove_cr)
        if isinstance(node,element.NavigableString):
            t = node.string
            if (remove_cr):
                t = re.sub(r'[\r\n]','',t)
            buf.write(t)
            
    def remove_unwanted_chars(self,s):
        s=re.sub('\(.*\)','',s) #(・・・)
        s=re.sub('\[.*\]','',s) #[・・・]
        s=s.strip() #remove white character at head and tail
        return s
    
    #compare str,in lowercase,and after removing space
    def compare_str(self,s1,s2,exact =True):
        s1=re.sub('[ \xa0]','',s1).lower()  #\xa0=&nbsp;
        s2=re.sub('[ \xa0]','',s2).lower()
        if exact:
            return s1 == s2
        else:
            return s1 in s2
    
    def test_link(self,tag,p_text,exact=True):
        if tag.name != 'a':
            return False
        if not 'href' in tag.attrs:
            return False
        buf = io.StringIO()
        self.get_text(tag, buf)
        text = buf.getvalue()
        return self.compare_str(p_text,text,exact)

class www_azlyrics_com(scraper_base):
    ascii_only = True
    site = 'www.azlyrics.com'
    
    def get_lyric(self):
        #first,try song url directry
        url = "http://www.azlyrics.com/lyrics/%s/%s.html" % (remove_unwanted_chars(self.artist),remove_unwanted_chars(self.song))
        self.browser.open(url)
        
        if not self.browser.response.ok:
            #query
            query = {'q':"%s %s" % (self.artist,self.song)}
            query = urllib.parse.urlencode(query)
            url = "http://search.azlyrics.com/search.php?" + query
            self.browser.open(url)
            
            #find song link
            node = self.browser.find(lambda tag:self.test_link(tag,self.song))
            if node is None:
                logging.info(self.log_msg("song not found."))
                return False
            self.browser.follow_link(node)
        
        #find lyric
        node = self.browser.find(text=re.compile("Usage"))
        if node is None:
            msg = "lyric not found."
            #msg += "\n" + self.browser.response.text
            logging.info(self.log_msg(msg))
            return False
        
        node = node.parent  #div
        
        logging.info(self.log_msg("lyric *found*"))
        buf = io.StringIO()
        self.get_text(node,buf)
        lyric = buf.getvalue()
        """
        if "Unfortunately we don't have the lyrics for the song" in lyric:
            logging.info(self.log_msg("lyric not found."))
            return False
        """
        self.lyric=lyric
        
        return True
    
class lyrics_az(scraper_base):
    ascii_only = True       #handle artist/song which name contains only ascii letters
    site = 'lyrics.az'  #name used for list sites
   
    def get_lyric(self):
        '''
        :return: True:success False:error
        '''

        #search artist        
        query = {'keyword': self.artist}
        query = urllib.parse.urlencode(query)
        url = "https://lyrics.az/?new_a=mixedsearch2&" +query
        self.browser.open(url)
        
        #click artist
        node = self.browser.find(lambda tag:self.test_link(tag,self.artist))
        if node is None:
            logging.info(self.log_msg("artist not found."))
            return False
        self.browser.follow_link(node)
        
        #click "View All Songs"
        node = self.browser.find('a',text='View All songs')
        if node is None:
            logging.info(self.log_msg("[View All Songs]link not found"))
            return False
        self.browser.follow_link(node)
        
        #find song link
        node = self.browser.find(lambda tag:self.test_link(tag,self.song))
        if node is None:
            logging.info(self.log_msg("song not found."))
            return False
        self.browser.follow_link(node)
        
        #find lyric
        node = self.browser.find('p',id="lyrics")
        if node is None:
            logging.info(self.log_msg("lyric not found."))
            return False
        
        buf = io.StringIO()
        self.get_text(node,buf)
        lyric = buf.getvalue()
        if "We haven't lyrics of this song." in lyric or \
            "At the moment nobody has submitted lyrics for this song to our archive." in lyric:
            logging.info(self.log_msg("lyric not found."))
            return False
        
        logging.info(self.log_msg("lyric *found*"))
        lyric=lyric.replace("´", "'")   #remove character that can't be passed to dll
        self.lyric=lyric
        
        return True

class petitlyrics_com(scraper_base):
    ascii_only = False
    site = 'petitlyrics.com'
    
    def get_lyric(self):
        self.browser.open('http://petitlyrics.com/search_lyrics')
        
        #search artist
        form = self.browser.get_form(action='/search_lyrics')
        form['title'].value = self.song
        form['artist'].value = self.artist
        self.browser.submit_form(form)
        
        #find song link
        node = self.browser.find(lambda tag:self.test_link(tag,self.song,False))
        if node is None:
            logging.info(self.log_msg("song not found."))
            return False
        self.browser.follow_link(node)
        
        #find lyric
        node = self.browser.find('canvas',id="lyrics")
        if node is None:
            logging.info(self.log_msg("lyric not found."))
            return False
        
        logging.info(self.log_msg("lyric *found*"))
        buf = io.StringIO()
        self.get_text(node,buf,remove_cr=False)
        lyric = buf.getvalue()
        
        self.lyric=lyric
        
        return True

class j_lyric_net(scraper_base):
    ascii_only = False
    site = 'j-lyric.net'
    
    def get_lyric(self):
        query = {'ka': self.artist,'kt':self.song}
        query = urllib.parse.urlencode(query)
        url = "http://search.j-lyric.net/index.php?" +query
        self.browser.open(url)
        
        #find song link
        node = self.browser.find(lambda tag:self.test_link(tag,self.song))
        if node is None:
            logging.info(self.log_msg("song not found."))
            return False
        self.browser.follow_link(node)
        
        #find lyric
        node = self.browser.find('p',id="Lyric")
        if node is None:
            logging.info(self.log_msg("lyric not found."))
            return False
        
        logging.info(self.log_msg("lyric *found*"))
        buf = io.StringIO()
        self.get_text(node,buf)
        lyric = buf.getvalue()
        
        self.lyric=lyric
        
        return True

class www_lyricsfreak_com(scraper_base):
    ascii_only = True
    site = 'www.lyricsfreak.com'
    
    def get_lyric(self):    
        query = {'q': self.artist}
        query = urllib.parse.urlencode(query)
        url = "http://www.lyricsfreak.com/search.php?a=search&type=band&" +query
        self.browser.open(url)
        
        #find artist link
        node = self.browser.find(lambda tag:self.test_link(tag,self.artist,False))
        if node is None:
            logging.info(self.log_msg("artist not found."))
            return False
        self.browser.follow_link(node)
        
        #find song link
        song_text = "·"+self.song+"lyrics"
        node = self.browser.find(lambda tag:self.test_link(tag,song_text))
        if node is None:
            msg = "song not found."
            #msg += self.browser.response.text
            logging.info(self.log_msg(msg))
            return False
        self.browser.follow_link(node)       
        
        #find lyric
        node = self.browser.find('div',id="content_h")
        if node is None:
            logging.info(self.log_msg("lyric not found."))
            return False
        
        logging.info(self.log_msg("lyric *found*"))
        buf = io.StringIO()
        self.get_text(node,buf)
        lyric = buf.getvalue()
        
        self.lyric=lyric
        
        return True

"""
class letssingit_com(scraper_base):
    ascii_only = True
    site = 'www.letssingit.com'
    
    def get_lyric(self):    
        query = {'s':"%s - %s" % (self.artist,self.song)}
        query = urllib.parse.urlencode(query)
        url = "https://search.letssingit.com/?%s&a=search&l=archive" % query
        self.browser.open(url)
        
        #find song link
        node = self.browser.find(lambda tag:self.test_link(tag,self.song))
        if node is None:
            logging.info(self.log_msg("song not found."))
            return False
        self.browser.follow_link(node)       
        
        #find lyric
        node = self.browser.find('div',id="lyrics")
        if node is None:
            logging.info(self.log_msg("lyric not found."))
            return False
        
        logging.info(self.log_msg("lyric *found*"))
        buf = io.StringIO()
        self.get_text(node,buf)
        lyric = buf.getvalue()
        if "Unfortunately we don't have the lyrics for the song" in lyric:
            logging.info(self.log_msg("lyric not found."))
            return False
        
        self.lyric=lyric
        
        return True
"""
"""
class genius_com(scraper_base):
    ascii_only = True
    site = 'genius.com'
    
    def get_lyric(self):    
        query = {'q':"%s %s" % (self.artist,self.song)}
        query = urllib.parse.urlencode(query)
        url = "http://genius.com/search?" + query
        self.browser.open(url)
        
        #find song link
        node = self.browser.find(lambda tag:self.test_link(tag,self.song,False))
        if node is None:
            logging.info(self.log_msg("song not found."))
            return False
        self.browser.follow_link(node)
        
        #find lyric
        node = self.browser.find('div',attrs={'class':"lyrics"})
        if node is None:
            logging.info(self.log_msg("lyric not found."))
            return False
        
        logging.info(self.log_msg("lyric *found*"))
        buf = io.StringIO()
        self.get_text(node,buf)
        lyric = buf.getvalue()
        #if "Unfortunately we don't have the lyrics for the song" in lyric:
        #    logging.info(self.log_msg("lyric not found."))
        #    return False
        self.lyric=lyric
        
        return True
"""
