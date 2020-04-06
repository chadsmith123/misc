#!/usr/bin/env python3
""" Log status and log outputter from PBS jobs on Helix 
    Assumes that if there is no Exit Status in standard out that job is RUNNING
"""
import re
import sys
import os
from glob import glob
import subprocess as sb
import argparse

def main(log_dir, jobs, head, tail, cat, log, clust):
    if os.path.exists(jobs):
        job_l = []
        with open(jobs, 'rt') as fh:
            for line in fh:
                job_l.append(line.strip('\n'))
    else:
        if '-' in jobs:
             start, end = int(jobs.split('-')[0]), int(jobs.split('-')[1]) + 1
             job_l = range(start, end) 
        elif ',' in jobs:
             job_l = jobs.split(',')
        else:
             job_l = [jobs]
    
    if not os.path.exists(log_dir):
        sys.exit(f'{log_dir} does not exist. Exiting...')

    for ii in job_l:
        if clust == 'sumner':
            stdout_glob = f'{log_dir}/*{ii}*.out'
            stderr_glob = f'{log_dir}/*{ii}*.err'
            stdout_status = ('State: ', 'COMPLETED (exit code 0)')
        if clust == 'helix':
            stdout_glob = f'{log_dir}/*o{ii}'
            stderr_glob = f'{log_dir}/*e{ii}'
            stdout_status = ('Exit Status: ', '0\n')
            f = glob(stdout_glob)
        if len(f) > 1:
            print(f'ERROR: {stdout_glob} returns more than one file.')
            break
        if not f:
            print(f'{stdout_glob} not found')
            break
        log_file = f[0]
        with open(log_file, 'rt') as fh:
            log_id = os.path.basename(log_file)
            hit = []
            exit_status = False
            for line in fh:
                if stdout_status[0] in line:
                    exit_status = True
                    hit = re.search(''.join(stdout_status), line)
                    #hit = re.search('Exit Status: 0\n', line)
                    if hit:
                        print('PASS', log_file)
                    else:
                        print(line.strip('\n'), log_file)
            if not exit_status:
                print("RUNNING", log_file)
    
        if cat or tail or head:
            if log == 'stderr':
                log_glob = stderr_glob
            if log == 'stdout':
                log_glob = stdout_glob
            f = glob(log_glob)
            log_file = f[0]
            if not f:
                print(f'{log_glob} not found')
                #print(f'{log_dir}/*{log_id}{ii} not found')
                break

        if cat:
            with open(log_file, 'rt') as fh:
                for line in fh:
                    print(line.strip('\n'))
            print('\n') 

        if head:
            sb.run(['head', '-n', head, log_file], check=True) 
            print('\n') 

        if tail:
            sb.run(['tail', '-n', tail, log_file], check=True) 
            print('\n') 

if __name__ == '__main__':
    PARSER = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,\
                                     description='Job log status checker')
    PARSER.add_argument('jobs', help='Range (11111-11112) or comma separated list of job ids')
    PARSER.add_argument('log_dir', help='Path to log directory')
    PARSER.add_argument('--cat', action='store_true', help='Output entire log')
    PARSER.add_argument('--head', help='Number of lines to output at beginning of log')
    PARSER.add_argument('--tail', help='Number of lines to output at end of log')
    PARSER.add_argument('--log', default='stdout', choices=['stderr', 'stdout'])
    PARSER.add_argument('--clust', default='helix', choices=['helix', 'sumner'])

    if len(sys.argv) == 1:
        PARSER.print_help()
        sys.exit()

    ARGS = PARSER.parse_args()

    main(**vars(ARGS))

