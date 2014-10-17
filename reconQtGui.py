#!/usr/bin/env python

from PyQt4 import QtGui, QtCore
from ui_mvdConfigDialog import Ui_MVDConfigDialog
import os.path
import json

DEFAULT_PARAMS = {
    'offset': (0, 0),  # shift offset
    'angularStep': 20.0,
    'indicesString': r'0:18',  # indices of data files
    'inputDir': r'./uni_fits',
    'pattern': r'fish_angle{a}_uni.fits',
    'psfFile': r'./PSF_fish.fits',
    'outFile': r'finalImg.fits',
    'maxIter': 100,
    'mu': 0.001,  # SNR 200
    'method': 'Fusion',
    'showImage': False
}


class MVDConfigDialog(QtGui.QDialog):

    METHODS = ['Fusion', 'Lucy-Richardson', 'MVD-Wiener', 'MVD-MAPGG']

    def __init__(self, defaults=None, parent=None):
        super(MVDConfigDialog, self).__init__(parent)
        self.ui = Ui_MVDConfigDialog()
        self.ui.setupUi(self)
        self.params = defaults
        self.setupMethods()
        self.setupParams()
        # connect signal/slots
        self.ui.mBtnOK.clicked.connect(self.accept)
        self.ui.mBtnCancel.clicked.connect(self.reject)
        self.ui.mBtnChooseInput.clicked.connect(self.onChooseInputDirectory)
        self.ui.mBtnChoosePSF.clicked.connect(self.onChoosePSFFile)
        # flag if the dialog was closed by OK or Cancel
        self.canceled = True

    def setupMethods(self):
        for method in self.METHODS:
            self.ui.mCbMethod.addItem(method)

    def setupParams(self):
        if self.params is not None:
            self.ui.mSpX0.setValue(self.params['offset'][0])
            self.ui.mSpY0.setValue(self.params['offset'][1])
            self.ui.mSpAngleStep.setValue(self.params['angularStep'])
            self.ui.mEdAngleRange.setText(self.params['indicesString'])
            self.ui.mEdInputDirectory.setText(self.params['inputDir'])
            self.ui.mEdInputFilePattern.setText(self.params['pattern'])
            self.ui.mEdPSFFile.setText(self.params['psfFile'])
            self.ui.mEdOutputFile.setText(self.params['outFile'])
            self.ui.mSpMaxIter.setValue(self.params['maxIter'])
            self.ui.mEdMu.setText('%.4f' % self.params['mu'])
            if self.params['method'] in self.METHODS:
                idx = self.METHODS.index(self.params['method'])
                self.ui.mCbMethod.setCurrentIndex(idx)
            else:
                self.ui.mCbMethod.setCurrentIndex(0)
            if self.params['showImage']:
                self.ui.mCkShowImage.setChecked(True)
            else:
                self.ui.mCkShowImage.setChecked(False)

    @QtCore.pyqtSlot()
    def onChooseInputDirectory(self):
        path = str(self.ui.mEdInputDirectory.text())
        path = QtGui.QFileDialog.\
            getExistingDirectory(self, "Input Directory", path)
        if not path.isNull():
            self.ui.mEdInputDirectory.setText(path)

    @QtCore.pyqtSlot()
    def onChoosePSFFile(self):
        path = str(self.ui.mEdPSFFile.text())
        path = QtGui.QFileDialog.\
            getOpenFileName(self, "Open PSF File", path,
                            "Images (*.fits *.tiff *.tif)")
        if not path.isNull():
            self.ui.mEdPSFFile.setText(path)

    @QtCore.pyqtSlot()
    def accept(self):
        self.updateParams()
        self.canceled = False
        super(MVDConfigDialog, self).accept()

    def isCanceled(self):
        return self.canceled

    def updateParams(self):
        if self.params is None:
            self.params = {}
        self.params['offset'] = (self.ui.mSpX0.value(), self.ui.mSpY0.value())
        self.params['angularStep'] = self.ui.mSpAngleStep.value()
        self.params['indicesString'] = str(self.ui.mEdAngleRange.text())
        self.params['inputDir'] = str(self.ui.mEdInputDirectory.text())
        self.params['pattern'] = str(self.ui.mEdInputFilePattern.text())
        self.params['psfFile'] = str(self.ui.mEdPSFFile.text())
        self.params['outFile'] = str(self.ui.mEdOutputFile.text())
        self.params['maxIter'] = self.ui.mSpMaxIter.value()
        self.params['mu'] = float(self.ui.mEdMu.text())
        idx = self.ui.mCbMethod.currentIndex()
        self.params['method'] = self.METHODS[idx]
        self.params['showImage'] = self.ui.mCkShowImage.isChecked()

    @staticmethod
    def getOptions(argv=[]):
        TEMP_PARAMS_JSON = os.path.expanduser('~/.tmp/tmpReconQtGui.json')
        app = QtGui.QApplication(argv)
        params = DEFAULT_PARAMS
        if os.path.isfile(TEMP_PARAMS_JSON):
            with open(TEMP_PARAMS_JSON) as f:
                params = json.load(f)
        configDialog = MVDConfigDialog(params)
        configDialog.show()
        app.exec_()
        if configDialog.isCanceled():
            return None
        # update the temp file
        with open(TEMP_PARAMS_JSON, 'w') as f:
            json.dump(configDialog.params, f)
        return configDialog.params


import pyfits
import numpy as np
import scipy.ndimage as spnd
from mvd_algorithms import mvd_lr, mvd_wiener, mvd_map_tikhonov
import matplotlib.pyplot as plt


def processIndices(indexString):
    '''This function takes an index string as input and produce the index list.
    Supported symbols include : and ,
    '''
    l = []
    phrases = indexString.split(',')
    for phrase in phrases:
        if ':' in phrase:
            words = phrase.split(':')
            if not all([w.strip().isdigit() for w in words]):
                return []
            if len(words) == 2:
                l = l + range(int(words[0]), int(words[1])+1)
            elif len(words) == 3:
                l = l + range(int(words[0]), int(words[2])+1, int(words[1]))
            else:
                return []
        else:
            if phrase.strip().isdigit():
                l.append(int(phrase))
            else:
                return []
    return l


def generateFileName(inputDir, pattern, idx):
    return os.path.join(inputDir, pattern.replace(r'{a}', str(idx)))


def mvdFusion(params):
    psf0 = pyfits.getdata(params['psfFile'])
    # generate actual indices
    params['indices'] = processIndices(params['indicesString'])
    imgList = []
    psfList = []
    print 'loading inputs...'
    progress = 0.0
    min_idx = params['indices'][0]
    for idx in params['indices']:
        # fname = params['pattern'] % (idx)
        fname = generateFileName(params['inputDir'], params['pattern'], idx)
        img = pyfits.getdata(fname, 0, header=False)
        img = spnd.interpolation.shift(img, params['offset'])
        angle = (idx-min_idx)*params['angularStep']
        img = spnd.interpolation.rotate(img, -angle, reshape=False)
        psf = spnd.interpolation.rotate(psf0, -angle, reshape=False)
        psf = psf/np.sum(psf)
        imgList.append(img)
        psfList.append(psf)
        progress = progress + 1.0/len(params['indices'])
        sys.stdout.write('\r%.2f%%' % (progress*100.0))
        sys.stdout.flush()
    sys.stdout.write('\n')
    print 'finished loading and transforming data from files'
    # create initial image
    initImg = np.zeros(imgList[0].shape)
    print 'creating additive image as initial guess'
    for img in imgList:
        initImg = initImg + img
    initImg = initImg / float(len(params['indices']))
    # do actual work
    print 'reconstructing with %s method...' % (params['method'])
    if params['method'] == 'Lucy-Richardson':
        finalImg = mvd_lr(initImg, imgList, psfList, params['maxIter'])
    elif params['method'] == 'MVD-Wiener':
        finalImg = mvd_wiener(initImg, imgList, psfList,
                              params['maxIter'], params['mu'])
    elif params['method'] == 'MVD-MAPGG':
        finalImg = mvd_map_tikhonov(initImg, imgList, psfList,
                                    params['maxIter'], params['mu']**2)
    else:  # including 'Fusion'
        finalImg = initImg
    print 'done.'
    return finalImg


def main():
    params = MVDConfigDialog.getOptions(sys.argv)
    if params is None:
        print 'Canceled.'
        return
    finalImg = mvdFusion(params)
    if not params['outFile'].endswith('.fits'):
        params['outFile'] = params['outFile'] + '.fits'
    outFile = os.path.join(params['inputDir'], params['outFile'])
    print 'saving to %s...' % (outFile)
    hdu = pyfits.PrimaryHDU(finalImg)
    hdu.writeto(outFile, clobber=True)
    print 'saved.'
    if params['showImage']:
        plt.imshow(finalImg, cmap='hot', vmin=0.0, vmax=0.5*np.amax(finalImg))
        plt.show()


import sys

if __name__ == '__main__':
    main()
