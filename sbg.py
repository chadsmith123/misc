import sys
import re
import pandas as pd
import requests
import time
import sevenbridges as sbg
from sevenbridges.http.error_handlers import rate_limit_sleeper, maintenance_sleeper
from collections import defaultdict

## OPTIONS
pd.set_option('max_colwidth', 100)
c = sbg.Config(profile='cgc')
api = sbg.Api(config=c, error_handlers=[rate_limit_sleeper, maintenance_sleeper])

## FUNCTIONS
def load_project(project_name):
    my_project = [p for p in api.projects.query(limit=100).all() \
                  if p.name == project_name]   

    if not my_project:    # exploit fact that empty list is False, {list, tuple, etc} is True
        print(f'{project_name} does not exist, please check spelling (especially trailing spaces)')
        raise KeyboardInterrupt
    if len(my_project) == 1:
        output = my_project[0]
    else:
        print(f'{project_name} matches more than one project name')
        output = my_project
    return output

def fileinfo(file):
    info = {'href':file.href,
            'id':file.id,
            'type':file.type,
            'name':file.name,
            'size':file.size,
            'parent':file.parent,
            'project':file.project,
            'created_on':file.created_on,
            'modified_on':file.modified_on,
            'origin':file.origin,
            'tags':file.tags,
            'metadata':file.metadata
           }
    return info

def filedf(file):
    metadata = file.metadata
    metadata['file'] = file.id
    metadata['filename'] = file.name
    metadata['parent'] = api.files.get(file.parent)
    metadata['parentname'] = api.files.get(file.parent).name
    metadata['tags'] = ','.join(file.tags)
    return metadata

def sls(source, pattern = None):
    ''' LS 
    .param source(sbg object)
    .param pattern(str):
    '''
    try:
        if source.type == 'folder':
            source = api.files.query(parent=source)
    except AttributeError:
        pass

    output = list()
    for ii in source.all():
        if pattern:
            if re.search(re.compile(pattern), ii.name):
               output.append((ii.name, ii))
        else:
           output.append((ii.name, ii))
    return output

def slf(source, pattern = None):
    output = list()

    try:
        if source.type == 'folder':
            source = api.files.query(parent=source)
    except AttributeError:
        pass
    for ii in source.all():
        if ii.is_folder():
            if pattern:
                if re.search(re.compile(pattern), ii.name):
                    output.append((ii.name, ii))
            else:
                output.append((ii.name, ii))
    return(output)

def srm(fileid):
    file = api.files.get(fileid)
    file.delete()

def filter_list(items:list, blacklist:list):
    items_filt = list()
    for ii in items:
        pattern = re.compile('|'.join(blacklist))
        if not re.search(pattern, ii[0]):
            items_filt.append(ii)
    return(items_filt)

def sdl(file_list: list, dest: str, blacklist: list = None, overwrite: bool = False):
    if blacklist:
        file_list = filter_list(file_list, blacklist)
    for ii in file_list:
        file = ii[1]
        dest_path = f'{dest}/{file.name}'
        try:
            file.download(dest_path, overwrite=overwrite)
        except:
            print(file.name, sys.exc_info()[0])
           # exceptions.append((ii, err)
    return file_list

def smv(file_list: list, dest, metafilt: dict  = None, blacklist: list = None, overwrite: bool = False): 
    ''' Move files 
    .param file_list(list): list of file objects
    .param dest(sbg object): destination folder
    '''
    output = list()
    if dest.type != 'folder':
        raise Exception(TypeError)
    if blacklist:
        file_list = filter_list(file_list, blacklist)

    # If file_list is a folder, make a new folder in dest and move files
    if all([ x.type == 'folder' for x in file_list]):
        for source_folder in file_list:
            try:
                new_folder = api.files.create_folder(name = source_folder.name, parent = dest)
                for file in api.files.query(parent = source_folder):
                    file.move_to_folder(parent = new_folder)
                    output.append(f'{source_folder.name}/{file.name}')
            except Exception as err:
                print(f'ERROR: {source_folder.name}, {err}')
                continue
        # API won't delete source_folder unless it is empty
        source_folder.delete()
    else:
        for file in file_list:
            try:
                if metafilt:
                    for key, value in metafilt.items():
                        if file.metadata.pop(key) is value:
                            file.move_to_folder(parent=dest)
                            output.append(file.name)
                else:
                    file.move_to_folder(parent=dest)
                    output.append(file.name)
            except Exception as err:
                print(f'ERROR: {file.name}, {err}')
                continue
    return output

def smv_task_files(source, dest):
    ''' Moves all files originating from a task in path to dest 
        NOTE: THE SCRIPT PAUSES EVERY SO OFTEN TO NOT OVERWHELM WITH API REQUESTS.
        NOTE ALSO: THAT THE SCRIPT STOPS SOMETIMES WITHOUT HAVING MOVED ALL FILES. NO ERROR IS THROWN, SO NOT SURE WHY. 
                   WHEN THIS HAPPENES JUST RESTART THE SCRIPT AND IT WILL KEEP WORKING. 

        .param source(sbg file object): source folder
        .param dest(sbg file object): destination folder
    '''
    output = defaultdict(list)
    # Retrieve source folder as a collection
    try:
        if source.type == 'folder':
            source = api.files.query(parent=source)
    except AttributeError:
        pass

    # Make a failed runs dir if it doesn't exist. If it does, load as a collection
    try:
        failed_run_dir = api.files.create_folder(
            name='Failed_Run_Data', parent=dest,
        )
        # Load as collection
        failed_run_dir = api.files.query(parent=dest, names=['Failed_Run_Data'])
    except:
        failed_run_dir = api.files.query(parent=dest, names=['Failed_Run_Data'])
    
    ### NEED TO ADD A LOOP TO CHECK IF THERE ARE MORE FILE AVAILABLE. EACH RUN ONLY CLEARS ~100 files. 
    
    files_to_move = list()
    print('Retrieving tasks from files...')
    for f in source.all():
    ## If you need to loop over items in a file, you will need to catch 'type = folder' and then have a sub-loop. 
    ## This will get complicated if you have very intricate file structure.
        if 'folder' in f.type:
            pass
            # folder = api.files.get(f.id)
            # file_list = folder.list_files()
            # print(file_list)
        
        if f.origin:
            if f.origin.task:
            ## If the file has an origin (task) [API created directories do not], 
            ## and if that origin has a valid task within the project [i.e., not an input file or uploaded data], 
            ## Then process the file. 
                try:
                    task = api.tasks.get(f.origin.task)
                    ## Get the task information from the file. 
                    #print('file name %s, file id %s, task origin %s, task status %s' % (f.name, f.id, f.origin, task.status))
                    output[task.status].append((f.name, f.id, f.origin))
                except Exception as err:
                    print(f'ERROR: {f.name}, {err}')
                    continue
      
                if 'COMPLETE' in task.status:
                    # If the task was successful: 
                    folder_name = task.name.replace(' - ', '_')
                    folder_name = re.sub('[^0-9a-zA-Z_-]+', '.', folder_name)
                    ## CGC only accepts alpha numerics and _ . - as valid charecters. 
                    ## These statements clean up task names to make them valid names for a folder
    
                    try: 
                        task_folder = api.files.create_folder(
                            name=folder_name, parent=dest
                        )
    
#                        moved_file = f.move_to_folder(
#                            parent=task_folder, name=f.name
#                        )
                        ## Try to make a folder within the 'Analysis' directory with the task name assoicated with the file.
                        ## Then move the file there.
                        ## If an excpetion is thrown, see below statmenet. 
    
                    except:
                        task_folder = api.files.query(parent=dest, names=[folder_name])[0]
                        #moved_file = f.move_to_folder(
                        #    parent=file[0].id, name=f.name
                        #)
                        ## If the folder already exists, the except statement will catch that.
                        ## First obtain the ID of the folder we are moving the file to within the parent 'Analysis' directory. 
                        ## Then move the file there. 
                    #print(files_to_move)
                    #print(f'complete:{f.name}')
                    files_to_move.append(
                        {'file': f.id,
                        'parent': task_folder.id,
                        'name': f.name})
    
                elif 'FAILED' in task.status or 'ABORTED' in task.status:
                    #print(task.status)
#                    moved_file = f.move_to_folder(
#                        parent=failed_run_dir[0].id, name=f.name
#                    )
                    files_to_move.append(
                        {'file': f.id,
                        'parent': failed_run_dir[0].id,
                        'name': f.name})
                else:
                    pass
        else:
            pass


    # Split files into n chunks for bulk move
    n = 100 # Max number of files allowed
    chunks = [files_to_move[i * n:(i + 1) * n] for i in range((len(files_to_move) + n - 1) // n )]  

    jobs = list()
    fails = list()
    print(f'Moving {len(files_to_move)} files.')
    for ii in chunks:
        try:
            jobs.append(api.async_jobs.file_bulk_move(files=ii))
            time.sleep(5)
        except:
            fails.extend(ii)
    
    if fails:
        print(f'{len(fails)} files failed. Attempting to move individually...')
        try:
            for ii in fails:
                 file = api.files.get(ii['file'])
                 parent = api.files.get(ii['parent'])
                 name = ii['name']
                 file.move_to_folder(parent=parent, name=name)
        except:
            print(f"{(ii['name'], ii['file'])} failed to move")

    # Get file copy job by id
    #copy_job = api.async_jobs.get_file_copy_job(id=files)

    # Parse job results to bulk format
    #job_results = job.get_result()
    #return job_results
    return jobs
    #return fails

def pos_to_ensembl(chrom, start, end):
    server = "https://rest.ensembl.org"
     
    chrom = chrom.strip('chr')
    #start = str(pos)
    #end = str(int(pos)+1)

    #ext = f"/overlap/region/human/1:2511603-2511604?feature=gene;feature=transcript;feature=cds;feature=exon"
    ext = f"/overlap/region/human/{chrom}:{start}-{end}?feature=gene"
    r = requests.get(server+ext, headers={ "Content-Type" : "application/json"})
     
    if not r.ok:
      r.raise_for_status()
      #sys.exit()
     
    #decoded = r.json()
    #print(repr(decoded))
    #y = json.loads(r.json())
    return r.json()
