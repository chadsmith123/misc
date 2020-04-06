#!/usr/bin/env python
''' Splits and indexes a bam file by chromosome '''
import sys
import os
import subprocess as sb
import multiprocessing
import argparse
import pysam

def main(bam_file):
    bam_file = os.path.abspath(bam_file)
    bam = pysam.AlignmentFile(bam_file, 'rb')
    
    out_d = dict()
    bams_out = list()
    print('Splitting bams...')
    for rec in bam:
        rec_d = rec.to_dict()
        chrom = rec_d['ref_name']
        if chrom not in out_d.keys():
            fname = bam_file.replace('bam', chrom + '.bam')
            out_d[chrom] = pysam.AlignmentFile(fname, 'wb', template=bam)
            bams_out.append(fname)
        out_d[chrom].write(rec)
    
    for v in out_d.values():
        v.close()
    
    threads = str(multiprocessing.cpu_count())
    for bam_file in bams_out:
        print('Indexing ' + bam_file)
        cmd = ['samtools', 'index', '-@', threads, bam_file]
        sb.check_call(cmd)

if __name__ == '__main__':
    PARSER = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    PARSER.add_argument('bam_file')
    
    if len(sys.argv) == 1:
        PARSER.print_help()
        sys.exit()

    ARGS = PARSER.parse_args()

    main(**vars(ARGS))

