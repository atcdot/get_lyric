# -*- coding: utf-8 -*-
from bs4 import element
import re
import io

'''
base class for scraping
'''
class scraper_base:

    '''
    retreive texts under node of beautifulsoup
    buf    StringIO:buffer to output text
    '''
    def get_text(self,node,buf):
        if isinstance(node,element.Tag):
            if node.name == "br":
                buf.write("\n")
            for e in node.contents:
                self.get_text(e,buf)
        if isinstance(node,element.NavigableString):
            t = re.sub(r'[\n\xa0]','',node.string)
            buf.write(t)
            
    def remove_unwanted_chars(self,s):
        s=re.sub('\(.*\)','',s) #(・・・)
        s=re.sub('\[.*\]','',s) #[・・・]
        s=s.strip() #remove white character at head and tail
        return s
    
    def test_tag(self,tag,name,p_text):
        if tag.name !=name:
            return False
        buf = io.StringIO()
        self.get_text(tag, buf)
        text = buf.getvalue()
        if p_text.lower() in text.lower():  #compare in lower case
            return True
        return False