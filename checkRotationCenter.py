import json
import argh
import numpy as np
from reconQtGui import mvdFusion
from scipy.misc import imsave
import os.path


@argh.arg('inJson', type=str, help='input JSON file')
@argh.arg('x0', type=int, help='x offset')
@argh.arg('y0', type=int, help='y offset')
@argh.arg('outImageFile', type=str,
          help='output file path, support {x0} and {y0} syntax')
def main(inJson, x0, y0, outImageFile):
    with open(inJson, 'r') as f:
        params = json.load(f)
    params['offset'] = (x0, y0)
    params['outFile'] =\
        outImageFile.replace('{x0}', str(x0)).replace('{y0}', str(y0))
    params['method'] = 'Fusion'
    finalImg = mvdFusion(params)
    finalImg = (finalImg - np.amin(finalImg)) /\
        (np.amax(finalImg) - np.amin(finalImg)) * 255.0
    finalImg = finalImg.astype(np.uint8)
    outFile = os.path.join(params['inputDir'], params['outFile'])
    print 'saving to %s ...' % (outFile,)
    imsave(outFile, finalImg)


if __name__ == '__main__':
    argh.dispatch_command(main)
