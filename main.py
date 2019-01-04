import argparse
import os
import glob
import subprocess
from urllib.request import urlopen
from bs4 import BeautifulSoup
from tqdm import tqdm

import cv2
import numpy as np

def page_length():
    with open('data/links.html') as fp:
        soup = BeautifulSoup(fp, 'html.parser')
    pg_len = []
    for a in soup.find_all('a'):
        o = a['href'].split('%')
        code = o[1].split('C')[-1]
        pg = o[2].split('C')[-1]
        ln = o[-1].split('C')[-1]
        pg_len.append((code, pg, ln))
    return pg_len


def download_all_volumes():
    for code, vol, ln in page_length():
        vol_dir = 'data/volumes/' + 'vol-{}'.format(vol)
        if not os.path.exists(vol_dir):
             os.makedirs(vol_dir)
        print('[INFO]  Volume-{} downloading....'.format(vol))
        for pg in tqdm(range(3, int(ln)+1)):
            url = 'https://www.tbrc.org/browser/ImageService?work=W22084&igroup={}&image={}&first=1&last={}&fetchimg=yes'.format(code, pg+2, ln)
            page_fn = vol_dir + '/page-{0:03d}.png'.format(pg)
            with open(page_fn, 'wb') as f:
                f.write(urlopen(url).read())
            yield page_fn


def page_name(fn):
    f_dir = fn.split("/")
    fn = f_dir[-1]
    vol_dir = os.path.join('output/volumes', f_dir[-2])
    if not os.path.exists(vol_dir):
            os.makedirs(vol_dir)
    fn_path = os.path.join(vol_dir, fn)
    return fn_path


def preprocess(fn):
    '''Reize the image, set correct page number and set dpi to 300
       Return: correct page number of Pecha'''

    def _remove_border(img):
        # Convert to gray scale and threshold
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret,thresh = cv2.threshold(gray,150,255,cv2.THRESH_BINARY_INV)

        ## opening
        # Detect Horizontal border line
        kernel = np.ones((1, 500), np.uint8)
        opening_h = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        kernel = np.ones((2, 200), np.uint8)  # note this is a horizontal kernel
        d_im = cv2.dilate(opening_h, kernel, iterations=5)
        e_im = cv2.erode(d_im, kernel, iterations=1)
        opening_h = e_im

        # Detect Vertical border line
        kernel = np.ones((100, 1), np.uint8)
        opening_v = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        kernel = np.ones((200, 2), np.uint8)  # note this is a horizontal kernel
        d_im = cv2.dilate(opening_v, kernel, iterations=3)
        e_im = cv2.erode(d_im, kernel, iterations=1)
        opening_v = e_im

        # Combine the hori and vert to form border box
        opening = opening_h + opening_v

        # Probabilistic Hough Line Transformation on border box
        ret,thresh2 = cv2.threshold(opening,127,255,cv2.THRESH_BINARY)
        gray = cv2.bilateralFilter(thresh2, 11, 17, 17)

        edged = cv2.Canny(gray, 10, 100)

        minLineLength = 5000
        maxLineGap = 100
        lines = cv2.HoughLinesP(edged.copy(),1,np.pi/180,100,minLineLength,maxLineGap)
        try:
            for line in lines:
                for x1,y1,x2,y2 in line:
                    cv2.line(img,(x1,y1),(x2,y2),(255,255,255), 10)
        except:
            pass

        return img

    def _resize(img):
        r = 600.0 / img.shape[0]
        dim = (int(img.shape[1] * r), 600)
        resized = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)
        return resized

    img = cv2.imread(fn)
    fn = page_name(fn)

    img = _resize(img)
    img = _remove_border(img)
    # img.save(fn, dpi=(300, 300))
    cv2.imwrite(fn, img)
    return fn

def pageseg(fn):
    cmd = 'ocropus_venv/bin/python pageseg.py --maxlines 9 --usegauss --maxcolseps 0 ' + fn
    # subprocess.check_output(cmd)
    subprocess.call(cmd, shell=True)

def process():
    for fn in download_all_volumes():
        fn = preprocess(fn)
        pageseg(fn)


if __name__ == "__main__":

    # ap = argparse.ArgumentParser(add_help=False)
    # ap.add_argument("--dir", type=str, help="path to volume")
    # ap.add_argument("--offset", type=int, help="page offset", default=2)
    # args = ap.parse_args()

    process()
