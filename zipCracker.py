# coding=utf-8
#
# Usage:
#
# python zipCracker.py -f target.zip
#
# python zipCracker.py -f target.zip -s 1 -e 6
# 
# python zipCracker.py -f target.zip -d password.txt
#

import sys, time, os
from zipfile import ZipFile, ZipExtFile
from argparse import ArgumentParser
import itertools

class SharedFile:
    def __init__(self, file):
        self._file = file
        self._pos = 53 # 41 header + 12 CRC

    def init(self):
    	self._pos = 53

    def read(self, n=-1):
        self._file.seek(self._pos)
        data = self._file.read(n)
        self._pos += n
        return data

    def close(self):
    	pass
        #self._file = None

def _GenerateCRCTable():
    poly = 0xedb88320
    table = [0] * 256
    for i in range(256):
        crc = i
        for j in range(8):
            if crc & 1:
                crc = ((crc >> 1) & 0x7FFFFFFF) ^ poly
            else:
                crc = ((crc >> 1) & 0x7FFFFFFF)
        table[i] = crc
    return table

crcInitTable = _GenerateCRCTable() # only once

class ZipDecrypter:
    def _crc32(self, ch, crc):
        """Compute the CRC32 primitive on one byte."""
        global crcInitTable
        return ((crc >> 8) & 0xffffff) ^ crcInitTable[(crc ^ ord(ch)) & 0xff]

    def __init__(self):
    	pass

    def init(self, pwd):
    	self.key0 = 305419896
        self.key1 = 591751049
        self.key2 = 878082192
        for p in pwd:
            self._UpdateKeys(p)

    def _UpdateKeys(self, c):
        self.key0 = self._crc32(c, self.key0)
        self.key1 = (self.key1 + (self.key0 & 255)) & 4294967295
        self.key1 = (self.key1 * 134775813 + 1) & 4294967295
        self.key2 = self._crc32(chr((self.key1 >> 24) & 255), self.key2)

    def __call__(self, c):
        """Decrypt a single character."""
        c = ord(c)
        k = self.key2 | 2
        c = c ^ (((k * (k^1)) >> 8) & 255)
        c = chr(c)
        self._UpdateKeys(c)
        return c

def _exit(string):
	global parser
	print ('\nExit : ' + string + '\n')
	parser.print_help()
	exit(0)

def _resultExit(count, passwd):
	print('Tried %d passwords and password is: %s' % (count, passwd))
	_timeEnd()
	exit(0)

def _zFile(zFile, fileName, password, info, checkByte, bytes, zef_file, zipDecrypter):
	zef_file.init()
	try:
		zipDecrypter.init(password)
		h = map(zipDecrypter, bytes[0:12])
		if ord(h[11]) != checkByte:
			# error password
			return False
		fileExt = ZipExtFile(zef_file, "r", info, zipDecrypter, True)
		fileExt.read1(1)
	except Exception as e:
		#print(e)
		return False
	return True

def _timeStart():
	global t1
	t1 = time.time()

def _timeEnd():
	global t1
	print('Used time is %d ms' % int((time.time() - t1) * 1000))

def main():
	global parser
	parser = ArgumentParser()
	parser.add_argument('-f', '--file', dest='zipFile', metavar='<filename>', required=True, type=str, help='path to zip file')
	parser.add_argument('-d', '--dictionary', dest='dictionary', metavar='<filename>', type=str, help='path to password dictionary file')
	parser.add_argument('-s', '--start-length', dest='minLength', metavar='N', default=1, type=int, help='minimum length for brute-force - defaults to 1 (only available in no dictionary file)')
	parser.add_argument('-e', '--end-length', dest='maxLength', metavar='N', default=6, type=int, help='maximum length for brute-force - defaults to 6 (only available in no dictionary file)')
	args = parser.parse_args()

	print('')

	_timeStart()

	zFile = ZipFile(args.zipFile)
	namelist = zFile.namelist()
	dictionary = args.dictionary
	minLength = args.minLength
	maxLength = args.maxLength

	zFileName = ''
	for name in namelist:
		if name[-1] != '/':
			zFileName = name
			break
	if zFileName == '':
		_exit('No valid file in zip ')
	info = zFile.getinfo(zFileName)
	if info.flag_bits & 0x8:
		checkByte = (info._raw_time >> 8) & 0xff
	else:
		checkByte = (info.CRC >> 24) & 0xff
	zFile.fp.seek(41)  # sizeFileHeader + fheader[_FH_FILENAME_LENGTH]  30 + 11
	bytesContent = zFile.fp.read(12)
	zef_file = SharedFile(zFile.fp)
	zipDecrypter = ZipDecrypter()
	
	count = 0
	if dictionary is not None:
		f = open(dictionary, 'r')
		content = f.readlines()
		f.close()
		print('%s passwords in dictionary file \n' % len(content))
		for passwd in content:
			count += 1
			if _zFile(zFile, zFileName, passwd.strip('\n\r'), info, checkByte, bytesContent, zef_file, zipDecrypter):
				_resultExit(count, passwd)
	else:
		#characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
		characters = "abcdefghijklmnopqrstuvwxyz"

		for length in range(minLength, maxLength + 1):
			print('Length of password : %s' % length)
			content = itertools.product(characters, repeat=length)
			for pw in content:
				passwd = ''.join(pw)
				count += 1
				if _zFile(zFile, zFileName, passwd, info, checkByte, bytesContent, zef_file, zipDecrypter):
					_resultExit(count, passwd)
	print('Tried %d passwords but no password found ...\n' % count)
	_timeEnd()

if __name__ == '__main__':
	main()