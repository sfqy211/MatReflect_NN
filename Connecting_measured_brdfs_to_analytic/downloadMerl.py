import os
import requests
import urllib

url = 'http://people.csail.mit.edu/wojciech/BRDFDatabase/brdfs'
saveDir = 'brdf'

if not os.path.exists(saveDir):
    os.makedirs(saveDir)

page = requests.get(url).text
brdfList = sorted([x.split('>')[-1] for x in page.split('.binary</a></td><td align="right">')][:-1])

for i, brdfname in enumerate(brdfList):
	if i < len(brdfList) - 1 and brdfname == brdfList[i+1].replace('2', ''):
		subfix = '1'
	else:
		subfix = ''
	print 'Downloading %s%s'%(brdfname, subfix)
	brdfFile = urllib.URLopener()
	brdfFile.retrieve('%s/%s.binary'%(url, brdfname), '%s/%s%s.binary'%(saveDir, brdfname, subfix))