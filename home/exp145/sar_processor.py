#!/usr/bin/python3

import os
import subprocess
import glob
import configparser
import logging
import time
import datetime
import json

__author__ = 'Tom Mladenov, Tom.Mladenov@esa.int; Tom.Mladenov@ieee.org'

EXP_ID = 145

# global path variables
BASE_PATH = '/home/exp{}'.format(EXP_ID)
TEST_PATH = BASE_PATH + '/test'
TOGROUND_PATH = BASE_PATH + '/toGround'
TOGROUNDLP_PATH = BASE_PATH + '/toGroundLP'
LIB_PATH = BASE_PATH + '/libs'
EXP_LOG_PATH = BASE_PATH + '/tmp/log'
EXP_IQ_PATH = BASE_PATH + '/tmp/iq'
EXP_WF_PATH = BASE_PATH + '/tmp/wf'
EXP_META_PATH = BASE_PATH + '/tmp/meta'

TMP_PATH = '/tmp'

# file path variables
BEACON_DETECTOR     = BASE_PATH + '/bin/armhf/tensorflow/lite/c/image_classifier
BEACON_DEMODULATOR  = BASE_PATH + '/exec/beacon_demodulator'
WF_RENDER           = BASE_PATH + '/exec/renderfall'
GLOBAL_CONFIG       = BASE_PATH + '/config/global.ini'

# read global configuration ini
global_config = configparser.ConfigParser()
global_config.read(GLOBAL_CONFIG)

# general
TEST_MODE_ACTIVE                    = global_config.getboolean('general', 'test_mode_active')
ML_ENABLED                          = global_config.getboolean('general', 'ml_enabled')
RUNTIME                             = global_config.getint('general'    , 'runtime_seconds')

# capture configuration
CAPTURE_CONFIG                      = global_config.get('capture_config', 'capture_configuration')
CAPTURE_TESTFILE                    = global_config.get('capture_config', 'capture_testfile')

# preprocessor configuration
PREPROCESS_CONFIG                   = global_config.get('preprocess_config', 'preprocess_configuration')

# process configiruation
PROCESS_CONFIG                      = global_config.get('process_config', 'process_configuration')
PROCESS_CONFIG_ML                   = global_config.get('process_config', 'process_configuration_ml')

# wf render configuration
WF_WINDOW                           = global_config.get('wf_config'     , 'wf_window')
WF_LENGTH                           = global_config.getint('wf_config'  , 'wf_length')
WF_FORMAT                           = global_config.get('wf_config'     , 'wf_format')
WF_BINS                             = global_config.getint('wf_config'  , 'wf_bins')

# inference configuration
MODEL_FILE                          = global_config.get('model_config', 'model_file')
MODEL_META                          = global_config.get('model_config', 'model_meta')
MODEL_THRESHOLD                     = global_config.getfloat('model_config', 'model_threshold')

# test settings
TEST_SAMPRATE                       = global_config.getint('test_config', 'test_samprate')
TEST_CENTERFREQ                     = global_config.getfloat('test_config'   , 'test_centerfreq')
TEST_DECIMATION                     = global_config.getint('test_config', 'test_decimation')
TEST_FILES = sorted(glob.glob(TEST_PATH + '/*.cf32'))
current_testfile_index = 0

# readon secondary linked capture configuration ini
capturing_config = configparser.ConfigParser()
capturing_config.read(CAPTURE_CONFIG)

CENTER_FREQ         = int(capturing_config.getfloat('SEPP_SDR_RX', 'carrier_frequency_GHz')*1000000000)
SAMPLES             = capturing_config.getint('SEPP_SDR_RX', 'number_of_samples')
RFFE_CALIBRATION    = capturing_config.getboolean('SEPP_SDR_RX', 'rffe_calibration_en')
GAIN                = capturing_config.getint('SEPP_SDR_RX', 'gain_dB')
SAMPLING_RATE_CODE  = capturing_config.getint('SEPP_SDR_RX', 'sampling_rate_cfg')
LOOP_BW             = capturing_config.getint('SEPP_SDR_RX', 'lpf_bw_cfg')


# create a start time and name of the logfile
START_TIME = datetime.datetime.utcnow()
LOG_FILE = EXP_LOG_PATH + '/sar_processor_{D}.log'.format(D=START_TIME.strftime("%Y%m%d_%H%M%S"))

if SAMPLING_RATE_CODE == 0:
    SAMPLING_RATE = 750000
elif SAMPLING_RATE_CODE == 1:
    SAMPLING_RATE = 1000000
elif SAMPLING_RATE_CODE == 2:
    SAMPLING_RATE = 1250000
elif SAMPLING_RATE_CODE == 3:
    SAMPLING_RATE = 1500000


def acquire_samples(config_file):

    if not TEST_MODE_ACTIVE:
        command = 'cd {}; sdr_receive_nsamples {}'.format(TMP_PATH, config_file)
        logger.info("Capturing new iq-file from SDR, run command [{}]".format(command))
        t1 = datetime.datetime.utcnow()
        os.system(command)
        t2 = datetime.datetime.utcnow()
        delta = round((t2 - t1).total_seconds(), 2)

        captured_files = glob.glob('{}/*.iqdat'.format(TMP_PATH))
        if len(captured_files) == 0:
            message = "Failed to capture iq-file, acquisition took {} seconds".format(delta)
            logger.error(message)
            raise Exception(message)
        else:
            logger.info("Captured iq-file [{}], acquisition took {} seconds".format(captured_files[0], delta))
            new_filename = '{}/sdr_iq_{}_{}_{}_{}_{}.cs16'.format(TMP_PATH, t2.strftime("%Y%m%d_%H%M%S"), CENTER_FREQ, SAMPLING_RATE, LOOP_BW, GAIN)
            move_output = get_output(['mv', '-v', captured_files[0], new_filename])
            logger.info("Renaming file: " + move_output)
            return new_filename
    else:
        logger.info("Running in testmode, acquisition returning .cs16 testfile [{}]".format(CAPTURE_TESTFILE))
        return CAPTURE_TESTFILE


def preprocess_samples(flowgraph_configuration, input_filename, override_output_filename=None):
    if override_output_filename == None:
        output_filename = input_filename.split('.')[0] + '_{}sps.cf32'.format(int(SAMPLING_RATE/DECIMATION))
        # do preprocessing

    else:
        output_filename = override_output_filename

    logger.info("Finished preprocessing [{}] in {}s, output file: {}".format(input_filename, 1, output_filename))
    return output_filename


def render_waterfall(input_filename):
    png_filename = input_filename.replace('.cf32', '.png') # intermediate file, will be deleted later
    output_filename = EXP_WF_PATH + '/' + input_filename.replace('.cf32', '.jpg').split('/')[-1]
    
    command = '{} -n {} -v -f {} -l {} -w {} -o {} {} && pngtopnm -quiet {} | ppmtojpeg -quiet > {}'.format(   
                                                                                                    WF_RENDER,\
                                                                                                    WF_BINS,\
                                                                                                    WF_FORMAT,\
                                                                                                    WF_LENGTH,\
                                                                                                    WF_WINDOW,\
                                                                                                    png_filename,\
                                                                                                    input_filename,\
                                                                                                    png_filename,\
                                                                                                    output_filename
                                                                                                )

    logger.info("Running command: ${}".format(command))                                                                                            
    ps = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=os.environ)
    output = ps.communicate()[0]
    for line in output.decode('utf-8').split("\n"):
        logger.info(line)

    logger.info(get_output(['rm', '-v', png_filename]))

    if os.path.exists(output_filename):
        logger.info("Written .JPEG spectrogram: {}".format(output_filename))
    else:
        logger.error("Error during .JPEG spectrogram generation")
        raise Exception("Error during .JPEG spectrogram generation")

    return output_filename

def run_inference(input_filename):
    logger.info("Running inference on input file [{}], using model file [{}]".format(input_filename, MODEL_FILE))
    return [-5384.0]

def process_samples(input_filename, samprate, decimation, center_freq, flowgraph_configuration, prediction=None):

    logger.info("Processing file [{f}] using predictions: [{p}]".format(f=input_filename, p=prediction))
    
    skip = 0
    offset = 0.0 if prediction == None else prediction

    libload =   '{LIB_PATH}/libgnuradio-epirb-1.so.0.0.0\
                :{LIB_PATH}/libboost_system.so.1.62.0\
                :{LIB_PATH}/libboost_program_options.so.1.62.0\
                :{LIB_PATH}/libjsoncpp.so.1'.format(LIB_PATH=LIB_PATH)

    # preload some libraries that are project specific
    os.environ['LD_PRELOAD'] = libload

    t1 = datetime.datetime.utcnow()
    command = [BURST_DETECTOR,\
                '--filename', input_filename,\
                '--samprate', str(samprate),\
                '--flowgraph-config', flowgraph_configuration,\
                '--decimation', str(decimation),\
                '--offset', str(offset),\
                '--center-freq', str(center_freq),\
                '--skip', str(skip)]
    logger.info("Running command: {}".format(command))
    output = subprocess.check_output(command, env=os.environ).decode('utf-8')
    t2 = datetime.datetime.utcnow()

    for line in output.split("\n"):
        logger.info(line)

    delta = round((t2 - t1).total_seconds(), 2)
    nr_beacons = output.count('{\"beacon\":{\"freq_hz\"')

    logger.info("Finished processing file [{}] in {}s, decoded {} beacons".format(input_filename, delta, nr_beacons))

def get_output(cmd):
    return subprocess.check_output(cmd).decode('utf-8').rstrip('\n')

def dump_artifacts_cleanup():
    logger.info("Moving all data for downlink...")
    copy_output_iq      = get_output(['cp', '-r', '-v', EXP_IQ_PATH,   TOGROUND_PATH])
    copy_output_wf      = get_output(['cp', '-r', '-v', EXP_WF_PATH,   TOGROUND_PATH])
    copy_output_meta    = get_output(['cp', '-r', '-v', EXP_META_PATH, TOGROUND_PATH])
    full_output = copy_output_iq + '\n' + copy_output_wf + '\n' + copy_output_meta
    for line in full_output.split("\n"):
        logger.info(line)
    
    logger.info("Moving logfile {}, output will terminate".format(LOG_FILE))
    subprocess.check_output(['cp', '-r', '-v', EXP_LOG_PATH,  TOGROUND_PATH])

    os.system('rm {}/*'.format(EXP_LOG_PATH))
    os.system('rm {}/*'.format(EXP_IQ_PATH))
    os.system('rm {}/*'.format(EXP_WF_PATH))
    os.system('rm {}/*'.format(EXP_META_PATH))


def log_info():
    opkg_output_api = subprocess.check_output(['opkg', 'status', 'sepp-api' ]).decode('utf-8')
    opkg_output_sdr = subprocess.check_output(['opkg', 'status', 'sepp-sdr' ]).decode('utf-8')
    opkg_output_exp = subprocess.check_output(['opkg', 'status', 'exp145'   ]).decode('utf-8')

    libload =   '{LIB_PATH}/libgnuradio-epirb-1.so.0.0.0\
                :{LIB_PATH}/libboost_system.so.1.62.0\
                :{LIB_PATH}/libboost_program_options.so.1.62.0\
                :{LIB_PATH}/libjsoncpp.so.1'.format(LIB_PATH=LIB_PATH)

    # preload some libraries that are project specific
    os.environ['LD_PRELOAD'] = libload
    lib_versions = subprocess.check_output([BURST_DETECTOR, '--version'], env=os.environ).decode('utf-8')

    full_output = opkg_output_api + opkg_output_sdr + opkg_output_exp + lib_versions
    for line in full_output.split("\n"):
        logger.info(line)

    logger.info("Dump global configuration...")
    for item in global_config.items():
        logger.info(item)


def setup():
    logger.info("Cleaning up {} directory".format(TMP_PATH))

    fileList = glob.glob(TMP_PATH + '/*.iqdat')
    for filePath in fileList:
        try:
            rm_output = get_output(['rm', '-v', TMP_PATH + '/*.iqdat'])
            logger.info(rm_output)
        except:
            logger.error("Error while deleting file {}".format(filePath))


def run_sar_processor():

    formatter = logging.Formatter('%(asctime)s %(levelname)s:%(funcName)25s() %(message)s')
    logging.Formatter.converter = time.gmtime

    global logger
    logger = setup_logger('sar_logger', LOG_FILE, formatter, level=logging.INFO)

    # start by logging some version information
    log_info()

    # cleanup /tmp from any previous *.iqdat files that were acquired but not processed
    setup()

    # start a capturing loop with time limit, fixed list in case of TEST_MODE_ACTIVE
    if TEST_MODE_ACTIVE:
        for testfile in TEST_FILES:
            filename_acquired_cs16      = acquire_samples(CAPTURE_CONFIG)
            filename_preprocessed_cf32  = preprocess_samples(PREPROCESS_CONFIG, filename_acquired_cs16, override_output_filename=testfile)

            if ML_ENABLED:
                filename_waterfall_jpg  = render_waterfall(filename_preprocessed_cf32)
                predictions             = run_inference(filename_waterfall_jpg)
                for p in predictions:
                    beacons     = process_samples(filename_preprocessed_cf32, TEST_SAMPRATE, TEST_DECIMATION, TEST_CENTERFREQ, PROCESS_CONFIG_ML, prediction=p)
                    
            else:
                beacons     = process_samples(filename_preprocessed_cf32, TEST_SAMPRATE, TEST_DECIMATION, TEST_CENTERFREQ, PROCESS_CONFIG, prediction=None)

    else:
        while (datetime.datetime.utcnow() - START_TIME).seconds < RUNTIME:
            filename_acquired_cs16      = acquire_samples(CAPTURE_CONFIG)
            filename_preprocessed_cf32  = preprocess_samples(PREPROCESS_CONFIG, filename_acquired_cs16)

            if ML_ENABLED:
                filename_waterfall_jpg      = render_waterfall(testfile)
                predictions                 = run_inference(filename_waterfall_jpg)
                for p in predictions:
                    beacons     = process_samples(filename_preprocessed_cf32, TEST_SAMPRATE, TEST_DECIMATION, TEST_CENTERFREQ, PROCESS_CONFIG_ML, prediction=p)
            else:
                beacons = process_samples(PROCESS_CONFIG, filename_preprocessed_cf32, prediction=None)
            time.sleep(5)

    # perform cleanup
    dump_artifacts_cleanup()

    # shutdown the logger and close all file handlers
    logging.shutdown()


def setup_logger(name, log_file, formatter, level=logging.INFO):
    """Setup the logger."""
    
    # Init handlers.
    fileHandler = logging.FileHandler(log_file)
    streamHandler = logging.StreamHandler()

    # Set formatters.
    fileHandler.setFormatter(formatter)
    streamHandler.setFormatter(formatter)

    # Init logger.
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(fileHandler)
    logger.addHandler(streamHandler)

    # Return the logger.
    return logger


if __name__ == '__main__':
    """Run the main program loop."""

    # run a sar processor
    run_sar_processor()