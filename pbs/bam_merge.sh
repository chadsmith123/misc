#!/usr/bin/env bash
if [ -z "$3" ]; then
    echo "USAGE: $0 <bam_file_list> <bam_outfile> <log_dir>"
    exit 1
fi

bam_files_file="$(cd "$(dirname "$1")"; pwd -P)/$(basename "$1")"
bam_outfile=$2
log_dir=$3

PBS_O_WORKDIR=`dirname $bam_files_file`

qsub bam_merge.pbs -V -v bam_files_file=${bam_files_file},bam_outfile=${bam_outfile},PBS_O_WORKDIR=${PBS_O_WORKDIR} -e $log_dir -o $log_dir
