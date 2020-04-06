#!/bin/bash
#PBS -N split_fastq_2
#PBS -l nodes=1:ppn=1
#PBS -l walltime=10:00:00
#PBS -q batch
#PBS -M chad.smith@jax.org
set -x
cd $PBS_O_WORKDIR

lines=9000000 # Split into x lines. 9M=10GB for PacBio
prefix=${fastq%.fastq.gz}.split

zcat $fastq | split -d -l $lines - $prefix
gzip $prefix*
rename 's/.split(d+)/.$1.fq/' ${prefix}*

echo '#DONE'
# qsub ~/scripts/split_fastq.sh -V -v fastq=$fastq
