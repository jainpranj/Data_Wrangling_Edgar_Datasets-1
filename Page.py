from bs4 import BeautifulSoup
from collections import namedtuple
import urllib as ur # urllib2 is latest?
from collections import namedtuple
import pprint
import csv
import re
import pandas as pd
import os
import logging
import zipfile
import sys
import tinys3
import configparser
Config = configparser.ConfigParser()
Config.read('config.ini')
Config.sections()
def ConfigSectionMap(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1
class Page:
    
    def __init__(self, url):
        """
        Retrieves and stores the urllib.urlopen object for a given url
        """
        try:
            self.link = ur.request.urlopen(url)
            self.fileName="EdgarFiles"
        except Exception:
            print("INVALID URL. Please check CIK or Accession number")
            sys.exit()
        
    def get_hyperlink(self):
        
        raw_html = self.link.read()
        soup = BeautifulSoup(raw_html, "html.parser")
        path = 'https://www.sec.gov'

        for row in soup.findAll('tr')[1:2]:
            
            for td in row.findAll('a'):
                if "10" in td.text:
#                     print("gsHA ",td.get('href'))
                    path += td.get('href')
                   
  
        return path     
              
            
    def get_tables(self):
        """
        Extracts each table on the page and places it in a dictionary.
        Converts each dictionary to a Table object. Returns a list of
        pointers to the respective Table object(s).
        """

        raw_html = self.link.read()
        soup = BeautifulSoup(raw_html, "html.parser")
        tables = soup.findAll("table")

        actual =  len(tables)       
        print("Actual ",len(tables))

        ##### Test: one table
        tables = soup.findAll("Nehal")
        #  tables = soup.findAll("table")[5] expl: is a tag, not resultset, cant loop over it to find tables,
        # hence the errors in catching table 5. 
        
        # Creating dummy list of tables with one table so that looping can be simulated
        for i in range(0,actual):
            table = soup.findAll("table")[i] # todo align with alt row color changes later
            tables.append(table)
            
        print("Testing ",len(tables)) 
        
        
        
        ## Looping through all tables in soup fetched page 
        table_list = []
        tableCount = 0
        for table in tables:
            coloredTD = table.findAll('td', attrs={'style':re.compile(r'background')})
#             print("no of colord tds ",len(coloredTD))
            if(len(coloredTD) >0):
                dataTable = DataFrame()
                df = dataTable.parse_html_table(table)
                #print("Data Frame : ",df)
                self.fileName = ""
                tableRows = table.findAll("tr")
                rowCount = 0
                for row in tableRows:
                    entries = row.findAll("td")
                    tdCount = 0
                    for entry in entries:

                        x = self.encode_text(entry) ## function not working


                        #print(str(x).startswith("$")," >>>> $")    

                        if( rowCount < 3 ):
                            df.set_value(rowCount,tdCount,x)
                        elif( rowCount >= 3):

                            if(tdCount == 0):

                                if(str(entry.text.strip())):
                                #if re.compile('^[a-z0-9\.]+$').match(str(x)):
                                    #print(x ," is string")
                                    df.set_value(rowCount,tdCount,x) 
                                else:
                                    tdCount = tdCount -1

                                #print(" entry lengths ", rowCount)
                            else:
                                df.set_value(rowCount,tdCount,x)

                        else :
                            df.set_value(rowCount,tdCount,x)

                        if str(x).find("$") != -1: 
                            df.set_value(rowCount,tdCount,"") 

                        # looking for meaningful data
                        #for i in entry.findAll('font',attrs={'style':'font-size:10.0pt;'}):
                        tdCount+=1 
                    rowCount+=1
                tableCount+=1
                table_list.append(df)
        print("tableCount with colored td ",tableCount)    
        return table_list
    
    def encode_text_not_working(self,x):
        try:
            x = x.text.encode("utf-8")
            strip_unicode = re.compile("([^-_a-zA-Z0-9!@#%&=,/'\";:~`\$\^\*\(\)\+\[\]\.\{\}\|\?\<\>\\]+|[^\s]+)")
            x = strip_unicode.sub("", x.decode("utf-8"))
            
            
        except Exception:
            #print 'encoding error: {0} {1}'.format(rowCount, tdCount)
            x = ""
            
        return x  
    
    def encode_text(self,x):
        try:
            x = x.text.strip().encode("utf-8")
            x = x.decode("utf-8")
            special_chars = ["[!@#$]", "%",":"]
            x=self.string_cleanup(x,special_chars)
        except Exception:
            #print 'encoding error: {0} {1}'.format(rowCount, tdCount)
            x = ""
            
        return x
    
    def string_cleanup(self,x, notwanted):
        for item in notwanted:
            x = re.sub(item, '', x)
        return x

    def save_tables(self, tables, CIK,ignore_small=False):
        """
        Takes an input a list of table objects and saves each
        table to csv format. If ignore_small is True,
        we ignore any tables with 5 entries or fewer. 
        """
        
        counter = 1
        for table in tables:
           
            
            if ignore_small:
                if table.get_metadata().num_entries > 5:
                    #print(" big > 5 ",table.get_value(3, 0)," and ",table.get_value(0, 4))
                    x = table.get_value(0, 0)       
                    self.fileName=x.replace("\n", "_and_").replace(" ","_").replace("/","_or_")
                    name = "EdgarFiles/"+CIK+"/"+ str(counter)+"_" +self.fileName+".csv"
                    try:
                        table.to_csv(name)
                        print("printing if it gets table"+table.to_csv(name))
                    except Exception:
                        
                        print("exception in creating files is",Exception)
                        print("exception in creating files"+table.to_csv(name))
                    counter += 1
            else:
                try:
                    x = table.get_value(3, 0) ## to name the file with first meaningful variable found at 0,3      
                except Exception:                        
                    x = table.get_value(0, 0)  ## for small files with no 3rd row

                self.fileName=str(x).replace("\n", "_and_").replace(" ","_").replace("/","_or_").replace("*","")

                name = "EdgarFiles/"+CIK+"/" + str(counter)+"_"+self.fileName +".csv" ## todo remove trialcsv
                table.to_csv(name)
                #print(os.getcwd())
                counter += 1


    def create_directory(self,path):
        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise
    
    def create_zip_folder(self,path):
        zipfolder_name=path+'.zip'
        zf = zipfile.ZipFile(zipfolder_name, "w")
        for dirname, subdirs, files in os.walk(path):
            zf.write(dirname)
            for filename in files:
                zf.write(os.path.join(dirname, filename))
        zf.close()
    
    def upload_zip_to_s3(self,path):
        S3_ACCESS_KEY = ConfigSectionMap("Part_1")['s3_access_key']#'AKIAICSMTFLAR54DYMQQ'
        S3_SECRET_KEY = ConfigSectionMap("Part_1")['s3_secret_key']#'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'
        host='edgardatasets.s3-website-us-west-2.amazonaws.com'
        # Creating a simple connection
        conn = tinys3.Connection(S3_ACCESS_KEY,S3_SECRET_KEY)

        # Uploading a single file
        f = open('EdgarFiles.zip','rb')
        conn.upload('EdgarFiles.zip',f,path)
                
                
Metadata = namedtuple("Metadata", "num_cols num_entries")

class DataFrame:
    
     def __init__(self):
        """
        Constructor ??? ## todo
        """

       
    
     def parse_html_table(self,table):
            n_columns = 0
            n_rows=0
            column_names = []
#             hasColoredTD = false
            # Find number of rows and columns
            # we also find the column titles if we can
            for row in table.find_all('tr'):
                
                # Determine the number of rows in the table
                td_tags = row.find_all('td')
 
                if len(td_tags) > 0:
                    n_rows+=1
                    if n_columns == 0 or n_columns < len(td_tags):
                        # Set the number of columns for our table
                        n_columns = len(td_tags)
                        
                # Test : Handle column names if we find them
                th_tags = row.find_all('th') 
                if len(th_tags) > 0 and len(column_names) == 0:
                    for th in th_tags:
                        column_names.append(th.get_text())
            
            #print("cols/rows frame 1 >>>> ",n_columns," ",n_rows)
            
            # Safeguard on Column Titles
            if len(column_names) > 0 and len(column_names) != n_columns:
                raise Exception("Column titles do not match the number of columns")
    
            columns = column_names if len(column_names) > 0 else range(0,n_columns)
            df = pd.DataFrame(columns = columns,
                              index= range(0,n_rows))
            
            #print("data frame first time >>>> "+df)
            
            """"
            row_marker = 0
            for row in table.find_all('tr'):
                column_marker = 0
                columns = row.find_all('td')
                for column in columns:
                    df.iat[row_marker,column_marker] = column.get_text()
                    column_marker += 1
                if len(columns) > 0:
                    row_marker += 1
                    
            # Convert to float if possible
            for col in df:
                try:
                    df[col] = df[col].astype(float)
                except ValueError:
                    pass
            print("weird frame >>>> "+df)
            """
            return df
        
############ Do we need main here >>??? ###
