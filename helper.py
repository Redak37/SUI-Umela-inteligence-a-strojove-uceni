from . import config
import json
import sys


class Helper:
    '''Class for (re)writing statistics
    '''
    def __init__(self, read_only_w):
        '''
        Parameters
        ----------
        read_only_w : bool - "only read"
        '''
        self.stat_file = config.STATISTICS_FILE
        self.bak_file = config.BACKUP_STATISTICS
        self.filedata = None
        self.jsondata = ''
        self.read_only = read_only_w
        self.open_file_rw()

    def open_file_rw(self):
        '''Open or create file with statistics
        '''
        try:
            self.close_file()
            if self.read_only:
                filedata = open(self.stat_file, 'r')
            else:
                filedata = open(self.stat_file, 'r+')
            jsondata = json.loads(filedata.read())

        except (TimeoutError, MemoryError) as ex:
            return

        except (FileNotFoundError, FileExistsError, PermissionError, NotADirectoryError, ValueError) as ex:
            if not self.read_only:
                sys.stderr.write('Statistics file could not be loaded or statistics file broken. Creating a new one. Exception: {}'. format(ex))
                filedata = open(self.stat_file, 'a+')
                filedata.write("""
    {
      "number of games": 0,
      "overall": {
        "2": [],
        "3": [],
        "4": [],
        "5": [],
        "6": [],
        "7": [],
        "8": []
      },
      "last moves": [
      ]
    }
                """)
                filedata.close()
                filedata = open(self.stat_file, 'r+')
                jsondata = json.loads(filedata.read())

        self.filedata = filedata
        self.jsondata = jsondata

    def rewrite_file(self):
        '''Rewrite file with statistics
        '''
        self.filedata.seek(0)
        json.dump(self.jsondata, self.filedata, indent=2)
        self.filedata.truncate()
        self.close_file()
        self.open_file_rw()

    def close_file(self):
        '''Close file with statistics
        '''
        if self.filedata:
            self.filedata.close()
