import os
import os.path as path
import string
import argparse
import glob
import re
from time import time

def grep(path, regex):
    regObj = re.compile(regex)
    res = {}
    r = re.compile('.*\.m+$')
    for root, dirs, fnames in os.walk(path):
        sources = [f for f in fnames if r.match(f)]
        for fname in sources:
            f = open(os.path.join(root,fname),'r')
            founds=regObj.findall(f.read())
            if founds:
                for found in founds:
                    if found.rstrip() in res:
                        res[found.rstrip()].append(fname)
                    else:
                        res[found.rstrip()]=[fname] 
    return res

def basename(filename):
    base = filename
    if filename.find('@2x') > 0:
        base = filename[:filename.find('@2x')]
    elif filename.find('~') > 0:
        base = filename[:filename.find('~')]
    elif filename.find('.') > 0:
        base = filename[:filename.find('.')]
    return base

def file_type(filename):
    isRetina = False
    isIpad = False
    if filename.find('@2x') > 0:
        isRetina = True
    if filename.find('~ipad') > 0:
        isIpad = True
    
    if isRetina:
        if isIpad:
            return 'ipad2x'
        else:
            return 'iphone2x'
    else:
        if isIpad:
            return 'ipad'
    return 'iphone'
    
def mungedName(basename):
    parts = re.split('[-_]', basename)
    capitalized = [word.capitalize() for word in parts]
    return string.join(capitalized, '')
    
class ImageGroup:
    iphone = None
    iphone2x = None
    ipad = None
    ipad2x = None
    extras = []
    refs = []
    
    def __init__(self, file_name):
        setattr(self, file_type(file_name), file_name)
                
    def add_file(self, file_name):
        type = file_type(file_name)
        
        if getattr(self, type) is not None:
            self.extras.append(file_name)
        else:
            setattr(self, type, file_name)
    
    def warnings(self, iPhone=True, iPad=True, retina=True, duplicates=True):
        definition = ''
        if iPhone and self.iphone is None:
            definition += '#warning image formatted for iPhone %s not found\n' % filename
        if iPhone and retina and self.iphone2x is None:
            definition += '#warning image formatted for retina iPhone %s not found\n' % filename
        if iPad and self.ipad is None:
            definition += '#warning image formatted for iPad %s not found\n' % filename
        if iPad and retina and self.ipad2x is None:
            definition += '#warning image formatted for retina iPad %s not found\n' % filename
        if duplicates:
            for file in self.extras:
                definition += '#warning duplicate image %s found in project. Verify proper capitalization.\n' % file
        return definition
        
    def output(self, filename, prefix):
        return args.format % {'prefix':prefix, 'identifier':mungedName(filename), 'filename':filename}
        
        
DEFAULT_FORMAT = '#define %(prefix)s%(identifier)s (UIImage*)^{\
 UIImage *image = [UIImage imageNamed:@"%(filename)s"];\
 NSCAssert(image, @"Image %(filename)s not found");\
 return image;\
 }()\n'

depart= time()
### cmd folder outputFile
parser = argparse.ArgumentParser(description='Create a header file with contants for each image file in the given folder.')
parser.add_argument('-s', '--source', type=str, default='./', help='A folder which contains images.')
parser.add_argument('-d', '--destination', type=str, default='./images.h', help='The filename to write to.')
parser.add_argument('--prefix', type=str, default='img', help='The prefix added at the begining of each image\'s filename.')
parser.add_argument('--format', type=str, default=DEFAULT_FORMAT, help='The format string specifying how the file should be written')
parser.add_argument('--warn-retina', dest='retina', type=bool, default=True, help='Warn for missing retina images.')
parser.add_argument('--warn-ipad', dest='ipad', type=bool, default=False, help='Warn for missing iPad (~ipad) images.')
parser.add_argument('--warn-iphone', dest='iphone', type=bool, default=False, help='Warn for missing iPhone (~iphone) images')
parser.add_argument('--warn-duplicates', dest='duplicates', type=bool, default=True, help='Warn for duplicate images.')

args = parser.parse_args()
original_output = ''
output = '// Created using the image.py script written by Patrick Hughes. He\'s a pretty cool guy.\n'
output +='//\n// DO NOT EDIT THIS FILE. \n//\n'
output +='// This file is automatically generated. Any changes may be overwritten the next time images.py is invoked.\n\n'

basedir = path.split(args.source)[-1]
file_path = path.join(path.expanduser('.'), args.destination)
if path.exists(file_path):
    with open(file_path, 'r') as file:
        original_output += file.read()
        file.close()
#source = path.join(path.expanduser(args.source), '*.png')
#iterator = glob.iglob(source)
used = grep('.','img[\w]+')
refs=used.keys()
r= re.compile('.*\.(png|jpg)$')
for dirname, dirnames, filenames in os.walk(path.expanduser(args.source)): #'/Users/cyril/Documents/developpement/iPad.hg/PagesJaunes/image'):
    all_files = {}
    sources = [f for f in filenames if r.match(f)]
    for filename in sources:
        #(leading, filename) = path.split(fullpath)
        key = basename(filename)
        if key in all_files:
            current_file = all_files[key]
            current_file.add_file(filename)
        else:
            current_file = ImageGroup(filename)
            all_files[key] = current_file

    relative= "".join([basedir, dirname.split(basedir)[-1]])
    output += '//\n// %(dirname)s \n//\n' %{'dirname':relative}
    for key in all_files:
        image_group = all_files[key]
        image_group.refs=used.keys
        warnings = image_group.warnings(iPhone=args.iphone, iPad=args.ipad, retina=args.retina, duplicates=args.duplicates)
        output += warnings
        output += image_group.output(key, args.prefix )
        ref=args.prefix+mungedName(key)
        try:
            i =refs.index(ref)
            del refs[i]
        except ValueError:
            pass
       
        if ref in used:
            output += "//"+", ".join(used[ref])
            output += '\n\n'
for file in refs:
    output += '#warning missing image %(file)s. referenced in %(refs)s\n' % {'file':file, 'refs':", ".join(list(set(used[file])))}

### Florian Bruger ensures the file isn't updated needlessly.
if original_output == output:
    pass
else:

    with open(file_path, 'w') as file:
        file.write(output)
        file.close()