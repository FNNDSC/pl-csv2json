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
import pydicom as dicom
import  time
from    loguru                  import logger
LOG             = logger.debug

logger_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> │ "
    "<level>{level: <5}</level> │ "
    "<yellow>{name: >28}</yellow>::"
    "<cyan>{function: <30}</cyan> @"
    "<cyan>{line: <4}</cyan> ║ "
    "<level>{message}</level>"
)
logger.remove()
logger.opt(colors = True)
logger.add(sys.stderr, format=logger_format)

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
            [-t|--tagFileFilter <tagFileFilter>]                        \\
            [-o| --outputFileStem <outputFileStem>]                     \\
            [-a|--addTags <commaSeparatedTagNames>]                     \\
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

            docker run --rm -u $(id -u)                                 \\
                -v $(pwd)/in:/incoming -v $(pwd)/out:/outgoing          \\
                fnndsc/pl-csv2json csv2json                             \\
                /incoming /outgoing

    DESCRIPTION

        `csv2json` ...

    ARGS

        [-f| --inputFileFilter <inputFileFilter>]
        A glob pattern string, default is "**/*.csv", representing the input
        file pattern to analyze.

        [-t|--tagFileFilter <tagFileFilter>]
        A glob pattern string, default is "**/*.dcm", representing the input
        dicom file pattern to analyze.

        [-o| --outputFileStem <outputFileStem>]
        The name of the output JSON file to be created (without the extension).

        [-a|--addTags <commaSeparatedTags>]
        A comma separated string conatining the list of tags to add in the info section
        of the output JSON. The default included tag is 'PatientID'.

        [-h] [--help]
        If specified, show help message and exit.

        [--json]
        If specified, show json representation of app and exit.

        [--man]
        If specified, LOG (this) man page and exit.

        [--meta]
        If specified, LOG plugin meta data and exit.

        [--savejson <DIR>]
        If specified, save json representation file to DIR and exit.

        [-v <level>] [--verbosity <level>]
        Verbosity level for app. Not used currently.

        [--version]
        If specified, LOG version number and exit.
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
                            default      = '**/*.dcm')

        self.add_argument(  '--outputFileStem','-o',
                            dest         = 'outputFileStem',
                            type         = str,
                            optional     = True,
                            help         = 'Output JSON file stem (no extension)',
                            default      = 'csv2jsonoutput')

        self.add_argument(  '--addTags','-a',
                            dest         = 'addTags',
                            type         = str,
                            optional     = True,
                            help         = 'comma seprated tags to be included as info',
                            default      = 'PatientID')

    def preamble_show(self, options) -> None:
        """
        Just show some preamble "noise" in the output terminal
        """

        LOG(Gstr_title)
        LOG('Version: %s' % self.get_version())

        LOG("plugin arguments...")
        for k,v in options.__dict__.items():
             LOG("%25s:  [%s]" % (k, v))
        LOG("")

        LOG("base environment...")
        for k,v in os.environ.items():
             LOG("%25s:  [%s]" % (k, v))
        LOG("")

    def run(self, options):
        """
        Define the code to be run by this plugin app.
        """
        st: float = time.time()
        self.preamble_show(options)

        dcm_str_glob = '%s/%s' % (options.inputdir,options.tagFileFilter)
        l_dcm_datapath = glob.glob(dcm_str_glob, recursive=True)


        str_glob = '%s/%s' % (options.inputdir,options.inputFileFilter)
        l_datapath = glob.glob(str_glob, recursive=True)

        tags = options.addTags.split(',')


        if len(l_datapath) > 0:

            csvFilePath =l_datapath[0]

            LOG(f"Reading CSV file from {csvFilePath}")

            jsonFilePath = os.path.join(options.outputdir,options.outputFileStem + ".json")
            # Call the make_json function
            self.make_json(csvFilePath, jsonFilePath, l_dcm_datapath,tags)

            LOG(f"Saving JSON file to {jsonFilePath}")
        else:
            LOG(f"No file matching the filter {options.inputFileFilter} exists in the input directory")

        et: float = time.time()
        LOG("Execution time: %f seconds." % (et -st))

    def show_man_page(self):
        """
        LOG the app's man page.
        """
        LOG(Gstr_synopsis)

    def make_json(self,csvFilePath, jsonFilePath, dcm_file_list,tags):
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
                leftFemur = {'Left femur':{'start':'leftFemurHead', 'end':'leftKnee'}}
                leftTibia = {'Left tibia':{'start':'leftKnee', 'end':'leftAnkle'}}
                rightFemur = {'Right femur':{'start':'rightFemurHead', 'end':'rightKnee'}}
                rightTibia = {'Right tibia':{'start':'rightKnee', 'end':'rightAnkle'}}

                dcm_image = {}
                for dcm_file_path in dcm_file_list:
                    if key in dcm_file_path:
                        dcm_image = dicom.dcmread(dcm_file_path)
                info = {}
                for tag in tags:
                    try:
                        info[tag.strip()] = str(dcm_image[tag.strip()].value)
                    except KeyError:
                        LOG(f"\nWARNING: {tag} does not exist for {key}.")


                height = 0
                width = 0

                try:
                    dimension = dcm_image.FieldOfViewDimensions
                    height = dimension[0]
                    width = dimension[1]
                except:
                    LOG(f"\nWARNING: Original dimension does not exist for {key}.")



                # All items of the JSON
                value = {'landmarks' : [leftFemurHead,leftKnee,leftAnkle,rightFemurHead,rightKnee,rightAnkle],
                     'drawXLine':[leftFemur,leftTibia,rightFemur,rightTibia],
                     'measureXDist':['Left femur','Left tibia','Right femur','Right tibia'],
                     'origHeight':int(height),
                     'origWidth': int(width),
                     'unit' : 'mm',
                     'info' : info}

                data[key] = value

        # Open a json writer, and use the json.dumps()
        # function to dump data
        with open(jsonFilePath, 'w', encoding='utf-8') as jsonf:
            jsonf.write(json.dumps(data, indent=4))

