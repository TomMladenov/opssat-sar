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
TOGROUND_PATH = BASE_PATH + '/toGround'
TOGROUNDLP_PATH = BASE_PATH + '/toGroundLP'
LIB_PATH = BASE_PATH + '/libs'
TMP_PATH = '/tmp'
EXP_LOG_PATH = BASE_PATH + '/tmp/log'
EXP_IQ_PATH = BASE_PATH + '/tmp/iq'
EXP_META_PATH = BASE_PATH + '/tmp/meta'

# file path variables
BURST_DETECTOR = BASE_PATH + '/bin/epirb_burst_detector'
GLOBAL_CONFIG = BASE_PATH + '/config/global.ini'

# read global configuration ini
global_config = configparser.ConfigParser()
global_config.read(GLOBAL_CONFIG)

CAPTURE_CONFIG                      = global_config.get('capture_config', 'capture_configuration')
FLOWGRAPH_CONFIG                    = global_config.get('flowgraph_config', 'flowgraph_configuration')
RUNTIME                             = global_config.getint('general', 'runtime_seconds')
KEEP_DECODER_LOG_IF_NOBEACONS       = global_config.getboolean('general', 'keep_decoder_log_if_no_beacons')
KEEP_DOWNSAMPLED_IQ_IF_BEACONS      = global_config.getboolean('general', 'keep_downsampled_iq_if_beacons')
KEEP_DOWNSAMPLED_IQ_IF_NO_BEACONS   = global_config.getboolean('general', 'keep_downsampled_iq_if_no_beacons')

# test settings
TEST_MODE_ACTIVE                    = global_config.getboolean('testing', 'test_mode_active')
TEST_FILE                           = global_config.get('testing', 'test_file')
TEST_SAMPRATE                       = global_config.getint('testing', 'test_samprate')
TEST_FLOWGRAPH                      = global_config.get('testing', 'test_flowgraph')
TEST_CENTERFREQ                     = global_config.getint('testing', 'test_centerfreq')


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

# if test mode is active, override some of the global parameters
if TEST_MODE_ACTIVE:
    SAMPLING_RATE       = TEST_SAMPRATE
    FLOWGRAPH_CONFIG    = TEST_FLOWGRAPH
    CENTER_FREQ         = TEST_CENTERFREQ

with open(FLOWGRAPH_CONFIG) as json_file:
    flowgraph_data = json.load(json_file)

DECIMATION = flowgraph_data["lpf"]["lpf_decimation"]


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
            logger.error("Failed to capture iq-file, acquisition took {} seconds".format(delta))
            return False, ""
        else:
            logger.info("Captured iq-file [{}], acquisition took {} seconds".format(captured_files[0], delta))
            new_filename = '{}/sdr_iq_{}_{}_{}_{}_{}.cs16'.format(TMP_PATH, t2.strftime("%Y%m%d_%H%M%S"), CENTER_FREQ, SAMPLING_RATE, LOOP_BW, GAIN)
            move_output = subprocess.check_output(['mv', '-v', captured_files[0], new_filename]).decode('utf-8')
            logger.info(move_output)

            return True, new_filename
    else:
        logger.warning("Running in testmode, returning testfile [{}]".format(TEST_FILE))
        return True, TEST_FILE


def process_samples(input_filename, samprate, center_freq, flowgraph_configuration):

    output_filename = input_filename.split('.')[0] + '_{}sps.cf32'.format(int(SAMPLING_RATE/DECIMATION))

    logger.info("Processing iq-file [{f}] at samplerate {sr} and writing downsampled output to [{of}]".format(f=input_filename, sr=samprate, of=output_filename))
    
    libload = '{LIB_PATH}/libgnuradio-epirb-1.so.0.0.0\
                :{LIB_PATH}/libboost_system.so.1.62.0\
                :{LIB_PATH}/libboost_program_options.so.1.62.0\
                :{LIB_PATH}/libjsoncpp.so.1'.format(LIB_PATH=LIB_PATH)

    # preload some libraries that are project specific
    os.environ['LD_PRELOAD'] = libload
    
    t1 = datetime.datetime.utcnow()
    output = subprocess.check_output([BURST_DETECTOR,\
                            '--filename', input_filename,\
                            '--samprate', str(samprate),\
                            '--output-filename', output_filename,\
                            '--flowgraph-config', flowgraph_configuration,\
                            '--center-freq', str(center_freq)], env=os.environ).decode('utf-8')
    t2 = datetime.datetime.utcnow()

    delta = round((t2 - t1).total_seconds(), 2)
    nr_beacons = output.count('{\"beacon\":{\"freq_hz\"')

    logger.info("Finished processing iq-file [{}] in {} seconds  ({} Sps), decoded {} beacons".format(input_filename, delta, float(SAMPLES/delta), nr_beacons))

    if nr_beacons == 0:
        if KEEP_DECODER_LOG_IF_NOBEACONS:
            for line in output.split("\n"):
                logger.info(line)
        else:
            logger.warning("No beacons decoded, supressed decoder output...".format(input_filename, delta, nr_beacons))

        # wipe output file if configured
        if KEEP_DOWNSAMPLED_IQ_IF_NO_BEACONS:
            logger.info("Keeping output file [{}], moving to {}".format(output_filename, EXP_IQ_PATH))
            move_output = subprocess.check_output(['mv', '-v', output_filename, EXP_IQ_PATH]).decode('utf-8')
            logger.info(move_output)
        else:
            logger.info("Removing output file [{}]".format(output_filename))
            output_file_cleanup = subprocess.check_output(['rm', '-v', output_filename]).decode('utf-8')
            logger.info(output_file_cleanup)   

    else:
        for line in output.split("\n"):
            logger.info(line)

        # wipe output file if configured
        if KEEP_DOWNSAMPLED_IQ_IF_BEACONS:
            logger.info("Keeping output file [{}], moving to {}".format(output_filename, EXP_IQ_PATH))
            move_output = subprocess.check_output(['mv', '-v', output_filename, EXP_IQ_PATH]).decode('utf-8')
            logger.info(move_output)
        else:
            logger.info("Removing output file [{}]".format(output_filename))
            output_file_cleanup = subprocess.check_output(['rm', '-v', output_filename]).decode('utf-8')
            logger.info(output_file_cleanup)

        # TODO : log metadata to /home/exp145/tmp/meta

    # when not in selftest mode, always remove the input iq-file because we no longer need it
    if not TEST_MODE_ACTIVE:
        logger.info("Removing input file [{}]".format(input_filename))
        input_file_cleanup = subprocess.check_output(['rm', '-v', input_filename]).decode('utf-8')
        logger.info(input_file_cleanup)



def dump_artifacts():
    logger.info("Experiment runtime exceeded, moving all data for downlink...")
    copy_output_log     = subprocess.check_output(['cp', '-r', '-v', EXP_LOG_PATH,  TOGROUND_PATH]).decode('utf-8')
    copy_output_iq      = subprocess.check_output(['cp', '-r', '-v', EXP_IQ_PATH,   TOGROUND_PATH]).decode('utf-8')
    copy_output_meta    = subprocess.check_output(['cp', '-r', '-v', EXP_META_PATH, TOGROUND_PATH]).decode('utf-8')
    full_output = copy_output_log + copy_output_iq + copy_output_meta
    for line in full_output.split("\n"):
        logger.info(line)

def cleanup():
    logger.info("Clearing experiment temporary folders...")
    os.system('rm {}/*'.format(EXP_LOG_PATH))
    os.system('rm {}/*'.format(EXP_IQ_PATH))
    os.system('rm {}/*'.format(EXP_META_PATH))

def log_info():
    opkg_output_api = subprocess.check_output(['opkg', 'status', 'sepp-api' ]).decode('utf-8')
    opkg_output_sdr = subprocess.check_output(['opkg', 'status', 'sepp-sdr' ]).decode('utf-8')
    opkg_output_exp = subprocess.check_output(['opkg', 'status', 'exp145'   ]).decode('utf-8')
    lib_versions = subprocess.check_output([BURST_DETECTOR, '--version']).decode('utf-8')
    full_output = opkg_output_api + opkg_output_sdr + opkg_output_exp + lib_versions
    for line in full_output.split("\n"):
        logger.info(line)


def run_sar_processor():

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    logging.Formatter.converter = time.gmtime

    global logger
    logger = setup_logger('sar_logger', LOG_FILE, formatter, level=logging.INFO)

    # start by logging some version information
    log_info()

    # start a capturing loop with time limit
    while (datetime.datetime.utcnow() - START_TIME).seconds < RUNTIME:
        success, filename = acquire_samples(CAPTURE_CONFIG)
        if success:
            process_samples(filename, SAMPLING_RATE, CENTER_FREQ, FLOWGRAPH_CONFIG)
        else:
            time.sleep(5)

    # perform cleanup
    dump_artifacts()
    cleanup()



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