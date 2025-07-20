# src/libisaac/core.py
#
# This is the main util file of libisaac

import platform
import os, sys, re
import configparser
from pathlib import Path
import xml.etree.ElementTree as ET

import userpaths


class mod_manager:
    def __init__(self, config_directory: str | None = None):
        """
        Initializes the mod_manager with a configuration directory.

        ## Args:
            (opt) mods_directory (str, Path): The path to the mods folder. If none is given, the library will
            try read it from the config file.
            (opt) config_directory (str, Path): The directory to (create and) use for metadata and configuration.
                If not provided, the system's default config directory provided by userpaths will be used.
                - Windows: %APPDATA%
                - Unix: ~/.config
        """
        # List of self variables
        # config_directory  - points to ".../.config/libisaac"
        # config_file       - points to "$config_directory/libisaac.ini"
        # config            - ConfigParser object with all settings loaded
        # root_directory    - points to "/The Binding of Isaac Rebirth"
        # mods_directory    - points to "$root_directory/mods" or override by config
        # _mods             - the main databroker for mod information
        if config_directory is not str:
            self.config_directory: str = userpaths.get_appdata() + '/libisaac'
        else:
            self.config_directory = config_directory

        self.config_file: Path = Path(self.config_directory + "/libisaac.ini")

        if not os.path.exists(self.config_directory): 
            os.makedirs(self.config_directory)

        self._mods = {}


    # To be used in case of external data manipulation
    def get_mods(self) -> dict:
        return self._mods


    def update_mods(self, mods_object: dict):
        self._mods = mods_object


    def _gen_config(self):
        # Generate a ini file to hold all config settings
        self.config = configparser.ConfigParser(allow_no_value=True)
        self.config['DEFAULT'] = {
            'backups_to_keep': '1'
            }
        self.config['PATHS'] = {
            'backup_dir': './backup ;The value of ./backup gets interpreted as the base game directory',
            'root_dir': '',
            'mods_dir': ''
            }
        with open(self.config_file.absolute(), 'w') as configfile:
            self.config.write(configfile)


    def read_config(self):
        # Read a config file (usually autogenereated one)
        # If a config file exists load it, otherwise generate it.
        if os.path.exists(self.config_file):
            self.config = configparser.ConfigParser()
            self.config.read(self.config_file)
        else:
            self._gen_config()

        # Read game dir - MUST BE DONE OUTSIDE OF THIS LIB
        self.root_directory = self.config['PATHS']['root_dir']
        
        if self.config['PATHS']['mods_dir'] != '':
            self.mods_directory = self.config['PATHS']['mods_dir']
        else:
            # DLCs prior to repentance stored mods outside of the base game dir.
            if "afterbirth" in self.root_directory.lower():
                self.mods_directory = self.root_directory
            else:
                self.mods_directory = self.root_directory + '/mods'


    def read_mods(self, mods_directory: str | Path | None = None) -> None:
        """
        Reads the mods folder and returns (and saves) metadata regarding the mods.

        ## Args:
            (opt) mods_folder_path (str | Path | None): Path to the mods folder, if none is provided
            it will read the one stored from the config file.

        ### Note:
            If a mod does not have a steam ID, -1 will be returned.
        """
        mod_sort_number = re.compile(r'^[0-9]+\s')

        if mods_directory != None:
            self.mods_directory = mods_directory

        # Sometimes (depending on OS and User system config) uneeded folders are created in the
        # root folder of mods. These need to be excluded from being managed. [eg, .DS_Store, .git, .directory]
        mod_dir = [f for f in os.listdir(self.mods_directory) if not f.startswith('.')]

        for mod in mod_dir:
            mod_path = os.path.join(self.mods_directory, mod)
            index = -1  # reset marker for each mod
            try:
                metadata_path = os.path.join(mod_path, 'metadata.xml')
                tree = ET.parse(metadata_path)
                root = tree.getroot()

                name_element = root.find('name')
                if name_element is not None and name_element.text:
                    index = mod_sort_number.findall(name_element.text)[0].strip()

            except (FileNotFoundError, ET.ParseError, IndexError):
                pass
            
            try:
                mod_folder_name, mod_id = mod.rsplit("_", 1)
            except ValueError:
                mod_folder_name = mod
                mod_id = -1

            # See "docs/mod_object" for usable fields
            self._mods.update({mod_folder_name: {
                'id': mod_id,
                'path': mod_path,
                'index': index,
                'disabled': os.path.exists(os.path.join(mod_path, 'disable.it'))
            }})

        import pprint
        pprint.pprint(self._mods, sort_dicts=False, width=160)


# DEBUG STUFF, TEMPORARY
# EXAMPLE ON HOW THIS WORKS COMING SOON
def main():
    md = mod_manager()

    if platform.system() == "Linux":
        md.read_mods(
            Path.expanduser(
                Path("~/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth/mods/")
            )
        )
    else:
        md.read_config()
        md.read_mods()

if __name__ == '__main__':
    # import cProfile
    # import pstats
    # prof_file = 'profile_output.prof'

    # Profile and save to file
    # profiler = cProfile.Profile()
    # profiler.enable()
    main()
    # profiler.disable()
    # profiler.dump_stats(prof_file)

    # # Load and print stats
    # stats = pstats.Stats(profiler, stream=sys.stdout)
    # stats.strip_dirs()
    # stats.sort_stats('cumulative')  # or 'time', 'calls', etc.
    # stats.print_stats()  # Remove argument to print everything