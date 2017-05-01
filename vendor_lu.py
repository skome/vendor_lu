#!/usr/bin/python
# coding: utf-8
""" 
Accept a list of Vendor IDs numbers, use them to search OCLC's Vendor ID API.
The file content should be csv: Vendor name, vendor ID 
Please also provide a filename to accept the Vendor Match Codes
Usage: %prog [inputfile] [outputfile]]
"""
import csv
from authliboclc import wskey, user
import BaseHTTPServer, cgi, codecs, datetime, os, socket, StringIO, \
string, sys, time, urllib, urlparse, xml.dom.pulldom, xml.dom.minidom, \
xml.sax.saxutils
from urllib import urlencode
import httplib, urllib2
from urllib2 import URLError
import yaml

#Configuration values
cfgFileName = 'vendor_lu.cfg' #OCLC keys and some settings live here

class MyHTTPSConnection(httplib.HTTPSConnection):
    """ Helper class used to create an HTTP Connection """
    def send(self, s):
        #print s
        httplib.HTTPSConnection.send(self, s)

class MyHTTPSHandler(urllib2.HTTPSHandler):
    """ Helper class used to display the result headers """
    def https_open(self, req):
        request = self.do_open(MyHTTPSConnection, req)
        #print request.info()
        return request

def print_status(num, total_num, msg): 
    """ Print status messages at the bottom of the screen """
    print ('Record: {} / {} {:<80}\r').format(num, total_num, msg),
    sys.stdout.flush() 
        
def setWSKey():
    my_wskey = wskey.Wskey(
        key=key,
        secret=secret,
        options=None)
    return my_wskey
    
def setUser():
    my_user = user.User(
        authenticating_institution_id=authenticating_institution_id,
        principal_id=principal_id,
        principal_idns=principal_idns
    )
    return my_user
    
def setAuthHeader(my_wskey, my_user, base_URL):
    authorization_header = my_wskey.get_hmac_signature(
        method='GET',
        request_url=base_URL,
        options={
            'user': my_user,
            'auth_params': None}
    )
    return authorization_header

def get_req_obj(auth_hdr):
    """ 
    Create an opener that accesses our helper classes, to 
    display the headers that are returned.
    """
    opener = urllib2.build_opener(MyHTTPSHandler)
    opener.addheaders = [('Authorization', auth_hdr)]
    return opener
    
def get_vendor_data(opener, request_url, vendor_id, no_value):
    """
    Get the vendor code given an open, authorized HTTP connection, 
    vendor id and the DOM tag that contains the code value.
    """
    try:
        response = opener.open(request_url)
        response_body = response.read()
        xdoc = xml.dom.minidom.parseString(response_body)
        return xdoc
    except URLError as e:
        response_body = e.read()
        print response_body
        if key == '{clientID}':
            print('\n** Note: Edit the script and supply valid authentication parameters. **\n')
        return no_value
    except:
        e = sys.exc_info()[0]
        print('Error:{}').format(e)
        return no_value

def get_vendor_matchcode(xmldata, tag_name):
    try:
        match_codes = xmldata.getElementsByTagName(tag_name)[0]
        return match_codes.firstChild.data.encode('utf-8')
    except URLError as e:
        response_body = e.read()
        print response_body
        if key == '{clientID}':
            print('\n** Note: Edit the script and supply valid authentication parameters. **\n')
        return no_value
    except IndexError as e:
        return no_value        
    except:
        e = sys.exc_info()[0]
        print('Error:{}').format(e)
        return no_value
        
def get_vendor_account_number(xmldata, tag_name, attr):
    try:
        accountsElement = xmldata.getElementsByTagName(tag_name)[0]
        return accountsElement.attributes[attr].value.encode('utf-8')
    except URLError as e:
        response_body = e.read()
        print response_body
        if key == '{clientID}':
            print('\n** Note: Edit the script and supply valid authentication parameters. **\n')
        return no_value
    except IndexError as e:
        return no_value
    except:
        e = sys.exc_info()[0]
        print('Error:{}').format(e)
        return no_value
        
def getYAMLConfig(fname): # read the config file values
    """ Read in needed authorization and configuration values """
    try:
        with open(fname,'r') as ymlf:
            config = yaml.load(ymlf)
            return config
    except Exception as e:
        print "Error accessing config: ",e


if __name__ == '__main__':
    vidFile=sys.argv[1] 
    outputfile = sys.argv[2]
    config = getYAMLConfig(cfgFileName) #read in config values
    key = config['Auth']['WSKEY']
    base_URL = config['Auth']['BASE_URL']
    secret = config['Auth']['SECRET']
    principal_id = config['Auth']['PRINCIPAL_ID']
    principal_idns = config['Auth']['PRINCIPAL_IDNS']
    authenticating_institution_id = config['Auth']['AUTHENTICATING_INSTITUTION_ID']
    no_value = config['Config']['NO_VALUE']
    target_tag = config['Config']['TARGET_TAG']
    target_tag2 = config['Config']['TARGET_WRAPPED_TAG']
    with open(vidFile,'r') as vidsf, open(outputfile, 'w') as matchesf:
        csvOutf = csv.writer(matchesf,delimiter=',', quoting=csv.QUOTE_MINIMAL)
        csvOutf.writerow(['VendorName','VendorID',target_tag, target_tag2])
        csvInf = csv.reader(vidsf,delimiter=',')
        my_wskey = setWSKey()
        my_user = setUser()
        for line_num, line in enumerate(csvInf):
            #Build a request object (every time, right?)
            request_url = '/'.join([base_URL,line[1]])
            auth_hdr = setAuthHeader(my_wskey, my_user, request_url)
            opener = get_req_obj(auth_hdr)
            #Get the data and write it to a file
            xmldoc = get_vendor_data(opener,request_url, line[1], no_value)
            mc = get_vendor_matchcode(xmldoc,target_tag)
            acct_num = get_vendor_account_number(xmldoc, target_tag2, 'number')
            csvOutf.writerow([line[0], line[1],mc, acct_num])
            print_status(line_num,9999,':'.join([line[0],mc,acct_num]))
    print('\n\nJob complete.')
