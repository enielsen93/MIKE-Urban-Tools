# -*- coding: utf-8 -*-
"""
Created on Fri Jun 01 13:11:56 2018

@author: HTPC
"""
#def jsonTilGIS():
import numpy as np
import json
from pprint import pprint
import bisect

import re
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

import codecs
import csv
FASs = 32777
vejFAS = np.empty((FASs,1),dtype='U50')
husnrFAS = np.empty((FASs,1),dtype='U10')
postdistriktFAS = np.empty((FASs,1),dtype='U50')
forbrugFAS =   np.empty((FASs,1),dtype=np.float)
takstFAS = np.empty((FASs),dtype='U50')

def csv_unireader(f, encoding="utf-8"):
    for row in csv.reader(codecs.iterencode(codecs.iterdecode(f, encoding), "utf-8"),delimiter=";"):
        yield [e.decode("utf-8") for e in row]
		
with open('FAS-udtraek.csv', 'rb') as csvfile:
	spamreader = csv_unireader(csvfile)
	for i, row in enumerate(spamreader):
		vejFAS[i] = unicode(row[2])
		husnrFAS[i] = row[4] + row[5]
		postdistriktFAS[i] = row[8]
		takstFAS[i] = row[15]
		try:
			forbrugFAS[i] = row[9]
		except:
			forbrugFAS[i] = 0
adresseFAS = np.array([hash("%s,%s,%s" % (a[0][0],a[1][0],a[2][0])) for a in zip(vejFAS,husnrFAS,postdistriktFAS)])
idxsort = np.argsort(adresseFAS)
forbrugFAS = forbrugFAS[idxsort]
husnrFAS = husnrFAS[idxsort]
postdistriktFAS = postdistriktFAS[idxsort]
vejFAS = vejFAS[idxsort]
takstFAS = takstFAS[idxsort]
adresseFAS = adresseFAS[idxsort]
adresseFAS = np.append(adresseFAS,max(adresseFAS)+1)
adresseFASLen = len(adresseFAS)
if not "data" in locals():
	with open("adresserSK.json") as f:
		data = json.load(f)

taksttyper = ['Off. kloak', 'Off. kloak - erhverv', 'Pumpestation- el ref.', 'Trappemodel', 'Trappemodel - samlet over 500 m³', 'Trappemodel %', 'Trappemodel >20.000', 'Trappemodel over 20.000 m³', 'Trappemodel over 20.000 m³ - Fast enhed', 'Trappemodel over 500 m³', 'Trappemodel uden rabat', 'Vandafl.', 'vandafl. bl. bolig & erhverv', 'vandafl. bl. bolig og erhverv', 'Vandafl.bidrag', 'Vandafledning', 'Vandafledning']		

lines = 0
idx = range(adresseFASLen)
adresser = []
xs = []
ys = []
with codecs.open("forbrugXY.txt","w",encoding="utf8") as txtfile:
	for i,ad in enumerate(data[lines+2:-1]):
		if ad["status"] == 1:
			vej = ad["adgangsadresse"]["vejstykke"]["navn"]
			husnr = ad["adgangsadresse"]["husnr"]
			postdistrikt = ad["adgangsadresse"]["postnummer"]["navn"]
			x,y = ad["adgangsadresse"]["adgangspunkt"]["koordinater"]
			xs.append(x)
			ys.append(y)
			FAS = bisect.bisect_left(adresseFAS,hash("%s,%s,%s" % (vej, husnr, postdistrikt)))
			h = hash("%s,%s,%s" % (vej, husnr, postdistrikt))
			adresser.append("%s,%s,%s" % (vej, husnr, postdistrikt))
			while FAS != adresseFASLen-1  and adresseFAS[FAS] == h:
				if forbrugFAS[FAS][0]<>0:
					forbrug = forbrugFAS[FAS][0]
					txtfile.write("%f,%f,%s,%s,%s,%f,%s\n" % (x,y,postdistrikt,vej,husnr,forbrug,takstFAS[FAS]))
					forbrugFAS[FAS] = 0
				FAS = FAS+1
	with codecs.open("nyforbundet.txt","w",encoding="utf8") as nyforbundet:
		with codecs.open("uforbundet.txt","w",encoding="utf8") as uforbundet:
			for i in range(len(forbrugFAS)):
				if forbrugFAS[i] <> 0:
					# txtfile.write("%s %s %s,%f\n" % (postdistriktFAS[i][0],vejFAS[i][0],husnrFAS[i][0],forbrugFAS[i]))
					ads = []
					addiff = []
					for adi in range(len(adresser)):
						if hash(adresser[adi].split(",")[2] + "," + adresser[adi].split(",")[0]) == hash("%s,%s" % (postdistriktFAS[i][0],vejFAS[i][0])):
							ads.append(adi)
							addiff.append(abs(float(re.findall("([\d]+)",adresser[adi].split(",")[1])[0])-float(re.findall("([\d]+)",husnrFAS[i][0])[0])))
					if len(ads)>0:
						nyforbundet.write("%s %s %s -> %s\n" % (postdistriktFAS[i][0],vejFAS[i][0],husnrFAS[i][0],adresser[ads[np.argmin(addiff)]]))
						txtfile.write("%f,%f,%s,%s,%s,%f,%s\n" % (xs[ads[np.argmin(addiff)]],ys[ads[np.argmin(addiff)]],postdistriktFAS[i][0],vejFAS[i][0],husnrFAS[i][0],forbrugFAS[i][0],takstFAS[i]))
					else:
						fuzzratio = []
						for adi in range(len(adresser)):
							fuzzratio.append(fuzz.ratio(adresser[adi].split(",")[2] + "," + adresser[adi].split(",")[0], "%s,%s" % (postdistriktFAS[i][0],vejFAS[i][0])))
						for adi in [idx for idx,b in enumerate(fuzzratio) if b == max(fuzzratio)]:
							ads.append(adi)
							addiff.append(abs(float(re.findall("([\d]+)",adresser[adi].split(",")[1])[0])-float(re.findall("([\d]+)",husnrFAS[i][0])[0])))
						# print [i for i,b in enumerate(fuzzratio) if b == max(fuzzratio)]
						nyforbundet.write("%s %s %s -> %s\n" % (postdistriktFAS[i][0],vejFAS[i][0],husnrFAS[i][0],adresser[ads[np.argmin(addiff)]]))
						txtfile.write("%f,%f,%s,%s,%s,%f,%s\n" % (xs[ads[np.argmin(addiff)]],ys[ads[np.argmin(addiff)]],postdistriktFAS[i][0],vejFAS[i][0],husnrFAS[i][0],forbrugFAS[i][0],takstFAS[i]))
						# uforbundet.write("%s %s %s\n" % (postdistriktFAS[i][0],vejFAS[i][0],husnrFAS[i][0]))
				
			# fuzzratio = np.empty((len(adresser)),dtype="int")
			
			# for adi in range(len(adresser)):
				# fuzzratio[adi] = fuzz.ratio(adresser[adi],"%s,%s,%s" % (vejFAS[i][0], husnrFAS[i][0], postdistriktFAS[i][0]))
			# print "%s,%s,%s" % (vejFAS[i][0], husnrFAS[i][0], postdistriktFAS[i][0])
			# print adresser[np.argmax(fuzzratio)]
		