#
# csv2json ds ChRIS plugin app
#
# (c) 2022 Fetal-Neonatal Neuroimaging & Developmental Science Center
#                   Boston Children's Hospital
#
#              http://childrenshospital.org/FNNDSC/
#                        dev@babyMRI.org
#

from chrisapp.base import ChrisApp
import csv
import json
import os
import glob

Gstr_title = r"""
                 _____ _                 
                / __  (_)                
  ___ _____   __`' / /'_ ___  ___  _ __  
 / __/ __\ \ / /  / / | / __|/ _ \| '_ \ 
| (__\__ \\ V / ./ /__| \__ \ (_) | | | |
 \___|___/ \_/  \_____/ |___/\___/|_| |_|
                     _/ |                
                    |__/                 
"""

Gstr_synopsis = """

    NAME

       csv2json

    SYNOPSIS

        docker run --rm fnndsc/pl-csv2json csv2json                     \\
            [-f| --inputFileFilter <inputFileFilter>]                   \\
            [-o| --outputFileStem <outputFileStem>]                     \\
            [-h] [--help]                                               \\
            [--json]                                                    \\
            [--man]                                                     \\
            [--meta]                                                    \\
            [--savejson <DIR>]                                          \\
            [-v <level>] [--verbosity <level>]                          \\
            [--version]                                                 \\
            <inputDir>                                                  \\
            <outputDir> 

    BRIEF EXAMPLE

        * Bare bones execution

            docker run --rm -u $(id -u)                             \
                -v $(pwd)/in:/incoming -v $(pwd)/out:/outgoing      \
                fnndsc/pl-csv2json csv2json                        \
                /incoming /outgoing

    DESCRIPTION

        `csv2json` ...

    ARGS
        [-f| --inputFileFilter <inputFileFilter>]
        A glob pattern string, default is "**/*.csv", representing the input
        file pattern to analyze.
        
        [-o| --outputFileStem <outputFileStem>]
        The name of the output JSON file to be created (without the extension).
        
        [-h] [--help]
        If specified, show help message and exit.
        
        [--json]
        If specified, show json representation of app and exit.
        
        [--man]
        If specified, print (this) man page and exit.

        [--meta]
        If specified, print plugin meta data and exit.
        
        [--savejson <DIR>] 
        If specified, save json representation file to DIR and exit. 
        
        [-v <level>] [--verbosity <level>]
        Verbosity level for app. Not used currently.
        
        [--version]
        If specified, print version number and exit. 
"""


class Csv2json(ChrisApp):
    """
    An app to convert CSV generated from pl-lld_inference to a JSON representation
    """
    PACKAGE                 = __package__
    TITLE                   = 'An app to convert CSV generated from pl-lld_inference to a JSON representation'
    CATEGORY                = ''
    TYPE                    = 'ds'
    ICON                    = ''   # url of an icon image
    MIN_NUMBER_OF_WORKERS   = 1    # Override with the minimum number of workers as int
    MAX_NUMBER_OF_WORKERS   = 1    # Override with the maximum number of workers as int
    MIN_CPU_LIMIT           = 2000 # Override with millicore value as int (1000 millicores == 1 CPU core)
    MIN_MEMORY_LIMIT        = 8000  # Override with memory MegaByte (MB) limit as int
    MIN_GPU_LIMIT           = 0    # Override with the minimum number of GPUs as int
    MAX_GPU_LIMIT           = 0    # Override with the maximum number of GPUs as int

    # Use this dictionary structure to provide key-value output descriptive information
    # that may be useful for the next downstream plugin. For example:
    #
    # {
    #   "finalOutputFile":  "final/file.out",
    #   "viewer":           "genericTextViewer",
    # }
    #
    # The above dictionary is saved when plugin is called with a ``--saveoutputmeta``
    # flag. Note also that all file paths are relative to the system specified
    # output directory.
    OUTPUT_META_DICT = {}

    def define_parameters(self):
        """
        Define the CLI arguments accepted by this plugin app.
        Use self.add_argument to specify a new app argument.
        """
        
        self.add_argument(  '--inputFileFilter','-f',
                            dest         = 'inputFileFilter',
                            type         = str,
                            optional     = True,
                            help         = 'Input file filter',
                            default      = '**/*.csv')
        self.add_argument(  '--tagFileFilter','-t',
                            dest         = 'tagFileFilter',
                            type         = str,
                            optional     = True,
                            help         = 'dicom tag file filter',
                            default      = '**/*.txt')
                            
        self.add_argument(  '--outputFileStem','-o',
                            dest         = 'outputFileStem',
                            type         = str,
                            optional     = True,
                            help         = 'Output JSON file stem (no extension)',
                            default      = 'csv2jsonoutput')

    def run(self, options):
        """
        Define the code to be run by this plugin app.
        """
        print(Gstr_title)
        print('Version: %s' % self.get_version())
        
        
        # Output the space of CLI
        d_options = vars(options)
        for k,v in d_options.items():
            print("%20s: %-40s" % (k, v))
        print("")
        tags_data = {}
        
        txtstr_glob = '%s/%s' % (options.inputdir,options.tagFileFilter)

        l_txtdatapath = glob.glob(txtstr_glob, recursive=True)
        
        for txtdatapath in l_txtdatapath:
            dim = ""
            id = ""
            f = open(txtdatapath)
            lines = f.readlines()
            for line in lines:
                line = line.replace('\n','')
                line = line.replace("'","")
                if line.find("Field of View Dimension") != -1:
                    dim = line.split(':')[1]
                if line.find("Instance Number") != -1:
                    id = line.split(':')[1]
                    id = id.replace(" ","")
            f.close()
            tags_data[id] = dim
        
        
        str_glob = '%s/%s' % (options.inputdir,options.inputFileFilter)

        l_datapath = glob.glob(str_glob, recursive=True)
        
        
        if len(l_datapath) > 0:

            csvFilePath =l_datapath[0]
            
            print(f"Reading file from {csvFilePath}")
        
            jsonFilePath = os.path.join(options.outputdir,options.outputFileStem + ".json")
            # Call the make_json function
            self.make_json(csvFilePath, jsonFilePath,tags_data)
            
            print(f"Saving file at {jsonFilePath}")
        else:
            print(f"No file matching the filter {options.inputFileFilter} exists in the input directory")

    def show_man_page(self):
        """
        Print the app's man page.
        """
        print(Gstr_synopsis)
        
    def make_json(self,csvFilePath, jsonFilePath, tags_data):
        # create a dictionary
        data = {}
     
        # Open a csv reader called DictReader
        with open(csvFilePath, encoding='utf-8') as csvf:
            csvReader = csv.reader(csvf)
         
            # Convert each row into a dictionary
            # and add it to data
            for rows in csvReader:
             
                # let the first column
                # be the primary key
                key = rows[0]
            
                # Convert values from string to
                # float as these are x-y coordinates
                for i in range(1,len(rows)):
                    rows[i] = float(rows[i])
            
                # All landmark points
                leftFemurHead ={'leftFemurHead': {'x':rows[1],'y':rows[2]}}
                rightFemurHead ={'rightFemurHead': {'x':rows[3],'y':rows[4]}}
                leftKnee ={'leftKnee': {'x':rows[5],'y':rows[6]}}
                rightKnee ={'rightKnee': {'x':rows[7],'y':rows[8]}}
                leftAnkle ={'leftAnkle': {'x':rows[9],'y':rows[10]}}
                rightAnkle ={'rightAnkle': {'x':rows[11],'y':rows[12]}}
            
                # All connecting lines
                leftTopLeg = {'leftTopLeg':{'start':'leftFemurHead', 'end':'leftKnee'}}
                leftBottomLeg = {'leftBottomLeg':{'start':'leftKnee', 'end':'leftAnkle'}}
                rightTopLeg = {'rightTopLeg':{'start':'rightFemurHead', 'end':'rightKnee'}}
                rightBottomLeg = {'rightBottomLeg':{'start':'rightKnee', 'end':'rightAnkle'}}
                
                height = 0
                width = 0
                for tagKey in tags_data.keys():
                    if tagKey in key:      
                        dimension = tags_data[tagKey]
                        dimension = dimension.replace('[','')
                        dimension = dimension.replace(']','')
                        dimension = dimension.replace(' ','')

                        height = dimension.split(',')[0]
                        width = dimension.split(',')[1]
                        
                # All items of the JSON
                value = {'landmarks' : [leftFemurHead,leftKnee,leftAnkle,rightFemurHead,rightKnee,rightAnkle],
                     'drawXLine':[leftTopLeg,leftBottomLeg,rightTopLeg,rightBottomLeg],
                     'measureXDist':['leftTopLeg','leftBottomLeg','rightTopLeg','rightBottomLeg'],
                     'origHeight':int(height),
                     'origWidth': int(width),
                     'unit' : 'mm'}
                        
                data[key] = value
 
        # Open a json writer, and use the json.dumps()
        # function to dump data
        with open(jsonFilePath, 'w', encoding='utf-8') as jsonf:
            jsonf.write(json.dumps(data, indent=4))

