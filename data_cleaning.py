# This Python 3 environment comes with many helpful analytics libraries installed
# It is defined by the kaggle/python Docker image: https://github.com/kaggle/docker-python
# For example, here's several helpful packages to load

import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)

# Input data files are available in the read-only "../input/" directory
# For example, running this (by clicking run or pressing Shift+Enter) will list all files under the input directory

import os

# You can write up to 20GB to the current directory (/kaggle/working/) that gets preserved as output when you create a version using "Save & Run All" 
# You can also write temporary files to /kaggle/temp/, but they won't be saved outside of the current session

'''
This code is used to create article and summary files from the csv file.
The output of the file will be a directory of text files representing seoarate articles and their summaries.
Each summary line starts with tag "@summary" and the article is followed by "@article".
'''
import pandas as pd
import os
import re

# read data from the csv file (from the location it is stored)
Data = pd.read_csv(r'wikihowAll.csv')
Data = Data.astype(str)
rows, columns = Data.shape

# create a file to record the file names. This can be later used to divide the dataset in train/dev/test sets
title_file = open('titles.txt', 'wb')

# The path where the articles are to be saved
path = "articles"
if not os.path.exists(path): os.makedirs(path)
path_abs = "abstracts"
if not os.path.exists(path_abs): os.makedirs(path_abs)  

# go over the all the articles in the data file
for row in range(rows):
    abstract = Data.loc[row,'headline']      # headline is the column representing the summary sentences
    article = Data.loc[row,'text']           # text is the column representing the article

    #  a threshold is used to remove short articles with long summaries as well as articles with no summary
    if len(abstract) < (0.75*len(article)):
        # remove extra commas in abstracts
        abstract = abstract.replace(".,",".")
        abstract = abstract.encode('utf-8')
        # remove extra commas in articles
        article = re.sub(r'[.]+[\n]+[,]',".\n", article)
        article = article.encode('utf-8')
        
        # file names are created using the alphanumeric charachters from the article titles.
        # they are stored in a separate text file.
        filename = Data.loc[row,'title']
        filename = "".join(x for x in filename if x.isalnum())
        filename1 = filename + '.txt'
        filename = filename.encode('utf-8')
        title_file.write(filename+b'\n')
        
        with open(path_abs+'/'+filename1,'wb') as f:
            f.write(abstract)
            # with open(path_abs+filename1,'r') as t:
            #   for line in t:
            #        line=line.lower()
            #        if line != "\n" and line != "\t" and line != " ":
                        # f.write(b'@summary'+b'\n')
            #            f.write(line.encode('utf-8'))
                        # f.write(b'\n')
                        
        with open(path+'/'+filename1,'wb') as t:
            t.write(article)
        
title_file.close()