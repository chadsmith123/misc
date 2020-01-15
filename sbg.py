import sevenbridges as sbg
from sevenbridges.http.error_handlers import rate_limit_sleeper, maintenance_sleeper
from requests import request
import re
import pandas as pd
from search import search_list

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
    else:
        if len(my_project) == 1:
            return my_project[0]
        else:
            print(f'{project_name} matches more than one project name')
            return my_project

def fileinfo(fileid):
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

def sls(query, pattern = None):
    for ii in query.all():
        if pattern:
            if re.search(re.compile(pattern), ii.name):
               print(f'{ii.name}\t{ii.id}')
        else:
           print(f'{ii.name}\t{ii.id}')

def slf(query, pattern = None):
    for ii in query.all():
        if ii.is_folder():
            if pattern:
                if re.search(re.compile(pattern), ii.name):
                    print(f'{ii.name}\t{ii.id}')
            else:
                print(f'{ii.name}\t{ii.id}')


