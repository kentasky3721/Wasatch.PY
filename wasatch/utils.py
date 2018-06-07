################################################################################
#                                                                              #
#                                   utils.py                                   #
#                                                                              #
################################################################################

import logging
import numpy
import json
import os
import re

log = logging.getLogger(__name__)

def generate_wavelengths(pixels, c0, c1, c2, c3):
    wavelengths = []
    for x in range(pixels):
        wavelength = c0           \
                   + c1 * x       \
                   + c2 * x * x   \
                   + c3 * x * x * x
        wavelengths.append(wavelength)
    return wavelengths            

def generate_wavenumbers(excitation, wavelengths):
    wavenumbers = []
    if not wavelengths or excitation < 1:
        return wavenumbers

    base = 1e7 / float(excitation)
    for i in range(len(wavelengths)):
        if wavelengths[i] != 0:
            wavenumbers.append(base - 1e7 / wavelengths[i])
        else:
            wavenumbers.append(0)
    return wavenumbers

# http://stackoverflow.com/questions/14313510/how-to-calculate-moving-average-using-numpy
# NOTE: this trims the ends of the array!  len(a) > len(moving_average(a, n))
def moving_average(a, n):
    ret = numpy.cumsum(a, dtype=float)
    ret[n:] = ret[n:] - ret[:-n]
    return ret[n - 1:] / n 

def apply_boxcar(a, half_width):
    if a is None:
        return None
    if half_width < 1:
        return a
    
    # "horizontally stack" a series of lists, then flatten them sequentially
    return numpy.hstack((a[0:half_width], 
                         moving_average(a, half_width * 2 + 1), 
                         a[-half_width:])).ravel()

def dump(foo, indent=0):
    spc  = '  ' * indent
    spc1 = '  ' * (indent + 1)
    s = ""

    if isinstance(foo, dict):
        s += spc + '{\n'
        for key,val in foo.iteritems():
            if isinstance(val, (dict, list, tuple)):
                s += spc1 + str(key) + '=>\n'
                s += dump(val, indent+2)
            else:
                s += spc1 + str(key) + '=> ' + str(val)
        s += spc + '}\n'

    elif isinstance(foo, list):
        s += spc + '[\n'
        for item in foo:
            s += dump(item, indent+1)
        s += spc + ']\n'

    elif isinstance(foo, tuple):
        s += spc + '(\n'
        for item in foo:
            s += dump(item, indent+1)
        s += spc + ')\n'

    else: 
        s += spc + str(foo)

    return s

def update_obj_from_dict(dest_obj, src_dict):
    for k in sorted(dest_obj.__dict__.keys()):
        if k in src_dict:
            log.debug("%s -> %s", k, src_dict[k])
            setattr(dest_obj, k, src_dict[k])

def load_json(pathname):
    try:
        with open(pathname) as infile:
            return json.load(infile)
    except:
        log.error("unable to load %s", pathname, exc_info=1)

def get_pathnames_from_directory(rootdir, pattern=None, recursive=False):
    pathnames = []
    log.debug("searching %s matching %s with recursive %s", rootdir, pattern, recursive)
    if recursive:
        for (directory, dirnames, filenames) in walk(rootdir):
            for filename in filenames:
                pathname = os.path.join(directory, filename)
                if pattern:
                    if re.search(pattern, filename):
                        pathnames.append(pathname)
                    else:
                        log.debug("%s does not match %s", pathname, pattern)
                else:
                    pathnames.append(pathname)
    else:
        for filename in os.listdir(rootdir):
            pathname = os.path.join(rootdir, filename)
            if os.path.isfile(pathname):
                if pattern:
                    if re.search(pattern, filename):
                        pathnames.append(pathname)
                    else:
                        log.debug("%s does not match %s", pathname, pattern)
                else:
                    pathnames.append(pathname)
    log.debug("returning %s", pathnames)
    return pathnames

# probably a numpy shortcut for this
def find_local_maxima(a, x_axis, center, tolerance=0):
    log.debug("find_local_maxima: center %.2f (tolerance %.2f)", center, tolerance)
    # generate subset of array within tolerance of center
    x = []
    y = []
    indices = []
    for i in range(len(x_axis)):
        x_value = x_axis[i]
        if center - tolerance <= x_value <= center + tolerance:
            indices.append(i)
            x.append(x_value)
            y.append(a[i])

    log.debug("  range x: %s", x)
    log.debug("  range y: %s", y)
    
    if not x:
        raise("no points within %s of %s" % (tolerance, center))

    # find maxima within subset
    best_x_index = indices[0]
    best_x_value = x_axis[0]
    best_y_value = y[0]
    for i in range(len(x)):
        if best_y_value < y[i]:
            best_x_index = indices[i]
            best_x_value = x_axis[best_x_index]
            best_y_value = y[i]

    # no point with linear interpolation, as it would only go "down"
    # (could do Gaussian / polynomial fit)

    log.debug("  best_x_index: %d", best_x_index)
    log.debug("  best_x_value: %.2f", best_x_value)
    log.debug("  best_y_value: %.2f", best_y_value)

    return (best_y_value, best_x_value, best_x_index)

def find_peak_feet_indices(spectrum, x_axis, x_index, boxcar_half_width=0):
    if boxcar_half_width:
        smoothed = apply_boxcar(spectrum, boxcar_half_width)
    else:
        smoothed = spectrum

    left_index = x_index
    for i in range(x_index - (boxcar_half_width + 1), -1, -1):
        if i == 0 or smoothed[i] > smoothed[left_index]:
            break
        left_index = i

    right_index = x_index
    for i in range(x_index + (boxcar_half_width + 1), len(spectrum)):
        if i + 1 == len(spectrum) or smoothed[i] > smoothed[right_index]:
            break
        right_index = i

    return (left_index, right_index)

def area_under_peak(spectrum, x_axis, x_index, boxcar_half_width=0):
    # find left and right "feet" of the peak
    (left_index, right_index) = find_peak_feet_indices(
        spectrum, x_axis, x_index, boxcar_half_width)

    # generate baseline-subtracted subspectrum of just the peak, considering
    #    the baseline to be a straight line between the two feet
    slope = float(spectrum[right_index] - spectrum[left_index]) / \
                   (x_axis[right_index] - x_axis[left_index])
    subspectrum = []
    subaxis = []
    for i in range (left_index, right_index + 1):
        baseline = spectrum[left_index] + slope * (x_axis[i] - x_axis[left_index])
        subspectrum.append(spectrum[i] - baseline)
        subaxis.append(x_axis[i])

    # 4. integrate subspectrum
    area = numpy.trapz(subspectrum, subaxis)
    return area

def peak_height_above_background(spectrum, x_axis, x_index, boxcar_half_width=0):
    # find left and right "feet" of the peak
    (left_index, right_index) = find_peak_feet_indices(
        spectrum, x_axis, x_index, boxcar_half_width)

    width_wn = x_axis[right_index] - x_axis[left_index]
    width_px = right_index - left_index + 1

    # generate baseline-subtracted subspectrum of just the peak, considering
    #    the baseline to be a straight line between the two feet
    slope = float(spectrum[right_index] - spectrum[left_index]) / width_wn
    baseline = spectrum[left_index] + slope * (x_axis[x_index] - x_axis[left_index])
    height = spectrum[x_index] - baseline

    log.debug("peak_height_above_background: peak at x_index %d (boxcar %d)", x_index, boxcar_half_width)
    log.debug("peak_height_above_background:   abs height: %.2f", spectrum[x_index])
    log.debug("peak_height_above_background:   peak width: (%d px, %.2f cm-1)", width_px, width_wn)
    log.debug("peak_height_above_background:   feet: (%d, %d)", left_index, right_index)
    log.debug("peak_height_above_background:   feet height: (%.2f, %.2f)", spectrum[left_index], spectrum[right_index])
    log.debug("peak_height_above_background:   slope: %.2f", slope)
    log.debug("peak_height_above_background:   peak baseline: %.2f", baseline)
    log.debug("peak_height_above_background:   relative height: %.2f", height)

    return (height, width_wn, width_px)
