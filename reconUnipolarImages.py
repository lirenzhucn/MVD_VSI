#!/usr/bin/env python

import argh
import numpy as np
import pyfits
import sys
from scipy.ndimage.interpolation import shift, rotate
import mvd_algorithms as mvd

params = {
    'offset': (-85, -12),  # shift offset
    'indices': range(0, 18),  # indices of data files
    'angularStep': 20.0,
    'outSize': (1700, 1600),
    'pattern': 'uni-fits-2/fish_angle%d_uni.fits',
    'psfFile': 'PSF_fish.fits',
    'outFile': 'finalImg.fits',
    'maxIter': 100,
    'mu': 0.001,  # SNR 200
}


@argh.arg('-i', '--init-image', type=str, help='input of initial image')
@argh.arg('-m', '--max-iter', type=int, help='max iteration number')
@argh.arg('-u', '--mu', type=int, help='regularization parameter')
@argh.arg('-o', '--out-file', type=str, help='output file')
def main(init_image=None, max_iter=params['maxIter'],
         mu=params['mu'], out_file=params['outFile']):
    if not out_file.endswith('.fits'):
        out_file = out_file + '.fits'
    psf0 = pyfits.getdata(params['psfFile'])
    imgList = []
    psfList = []
    print 'loading inputs...'
    progress = 0.0
    min_idx = params['indices'][0]
    for idx in params['indices']:
        fname = params['pattern'] % (idx)
        img = pyfits.getdata(fname, 0, header=False)
        img = shift(img, params['offset'])
        img = rotate(img, -(idx-min_idx)*params['angularStep'], reshape=False)
        psf = rotate(psf0, -(idx-min_idx)*params['angularStep'], reshape=False)
        psf = psf/np.sum(psf)
        imgList.append(img)
        psfList.append(psf)
        progress = progress + 1.0/len(params['indices'])
        sys.stdout.write('\r%.2f%%' % (progress*100.0))
        sys.stdout.flush()
    sys.stdout.write('\n')
    print 'finished loading and transforming data from files'
    initImg = np.zeros(imgList[0].shape)
    if init_image is None:
        print 'creating additive image as initial guess'
        for img in imgList:
            initImg = initImg + img
        initImg = initImg / float(len(params['indices']))
    else:
        initImg = pyfits.getdata(init_image, 0, header=False)
        initImg = initImg.astype('float64')
    print 'starting reconstruction...'
    # finalImg = mvd_wiener(initImg, imgList, psfList, max_iter, mu)
    finalImg = mvd.mvd_map_tikhonov(initImg, imgList, psfList, max_iter, mu**2)
    print 'done'
    hdu = pyfits.PrimaryHDU(finalImg)
    hdu.writeto(out_file, clobber=True)
    print 'saved'

if __name__ == '__main__':
    argh.dispatch_command(main)
