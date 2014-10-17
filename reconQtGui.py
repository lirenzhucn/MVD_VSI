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
}


class MVDConfigDialog(QtGui.QDialog):

    def __init__(self, defaults=None, parent=None):
        super(MVDConfigDialog, self).__init__(parent)
        self.ui = Ui_MVDConfigDialog()
        self.ui.setupUi(self)
        self.params = defaults
        self.setupParams()
        # connect signal/slots
        self.ui.mBtnOK.clicked.connect(self.accept)
        self.ui.mBtnCancel.clicked.connect(self.reject)
        self.ui.mBtnChooseInput.clicked.connect(self.onChooseInputDirectory)
        self.ui.mBtnChoosePSF.clicked.connect(self.onChoosePSFFile)

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
        super(MVDConfigDialog, self).accept()

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
        # update the temp file
        with open(TEMP_PARAMS_JSON, 'w') as f:
            json.dump(configDialog.params, f)
        return configDialog.params


import sys

if __name__ == '__main__':
    params = MVDConfigDialog.getOptions(sys.argv)
    print json.dumps(params, indent=2)
