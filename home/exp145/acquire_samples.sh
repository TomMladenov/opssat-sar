#!/bin/busybox sh

timestamp_trigger=$(date +"%Y%m%d_%H%M%S")

LOGFILE=exp145_sdr_$timestamp_trigger.log
CONFIG_FILE=config/sdr_rx_cfg_sar.ini
ARTEFACT=exp145_artifacts_$timestamp_trigger.tar
TOGROUND=toGround

read_ini_file() {
    local obj=$1
    local key=$2
    local file=$3
    awk '/^\[.*\]$/{obj=$0}/=/{print obj $0}' $file \
        | grep '^\['$obj'\]'$key'=' \
        | sed 's/.*=//'
}

execute_and_log()
{
    echo "$($1)" | awk '{print strftime("[%d-%m-%Y %H:%M:%S]"), $0}' >> $LOGFILE
}

# perform 1 run
execute_and_log "opkg status sepp-api"
execute_and_log "opkg status sepp-sdr"
execute_and_log "sdr_receive_nsamples $CONFIG_FILE"

freq=$(read_ini_file SEPP_SDR_RX carrier_frequency_GHz $CONFIG_FILE)
sr=$(read_ini_file SEPP_SDR_RX sampling_rate_cfg $CONFIG_FILE)
gain=$(read_ini_file SEPP_SDR_RX gain_dB $CONFIG_FILE)

filename=sdr_iq_"$timestamp_trigger"_sr"$sr"_f"$freq"_g"$gain".cs16
echo $filename

# collect and cleanup
for f in *.iqdat; do
    mv -- "$f" $filename
done
tar -cvf $ARTEFACT *.iqdat *.log
mv $ARTEFACT $TOGROUND
rm *.log
rm *.iqdat

exit 0
