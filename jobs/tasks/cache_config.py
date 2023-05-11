import json
import os
from datetime import datetime, timedelta


class Config:
    """
    This class exists for keeping the config in a simpler-to-use form and up to date

    Must have set `file` [`str`]: Config file path
    """

    def __init__(self, file: str):
        self.file = file

        self.build()
        self.setdefaults()
        self.loadconfig()

    def build(self):
        """
        This is meant to be called when setting up the config.
        Runs a series of checks and builds the config file if it
        doesn't currently exist.
        """

        # If the file exists, return
        if os.path.isfile(self.file) and os.path.getsize(self.file) != 0:
            print("Config file exists, moving on")
            return

        # If the file doesn't exist, check if the directory exists
        # If not, make the directory
        if not os.path.exists(os.path.dirname(self.file)):
            os.makedirs(os.path.dirname(self.file))

        # Ask the user for some configuration variables and
        # dump them into a new config file:
        # - TOKEN has to be set for the bot to be used
        # - guild can be set if the commands should only be synced
        #     to one server; leave None to sync them globally
        # - owner has to be set for certain commands (such as /update) to work
        _data = {
            "token": input("Your Discord app's auth token: "),
            "guild": None,
            "owner": int(input("Your own Discord ID: ")),
        }

        with open(self.file, "w+") as confile:
            json.dump(_data, confile, indent=4)

        _data.clear()

        print("Config file initialized")

    def setdefaults(self):
        """
        A separate method from self.build() for availability later on, for instance if something goes wrong.
        """
        # Load configurations from file
        with open(self.file, "r") as confile:
            config = json.load(confile)

        # Check again if any rows are missing and insert defaults if so
        _defaults = {
            "rattimes": [11, 3],
            "huomentacooldown": 12,
            "ultrararechance": 200,
            "rarechance": 50,
            "lotterychannel": None,
            "basicincome": 10,
            "bet": 20,
            "voicechannel": None,
        }

        # If one of these values does not exist in the config, insert them
        _changes = False
        for key, value in _defaults.items():
            if key not in config:
                config.update({key: value})
                _changes = True

        _defaults.clear()

        # If changes are made, update config file
        if _changes:
            with open(self.file, "w+") as confile:
                json.dump(config, confile, indent=4)
            print("Config file updated with defaults")

    def loadconfig(self):
        """
        Loads the config
        """
        with open(self.file, "r") as confile:
            for key, value in json.load(confile).items():
                self.__setattr__(key, value)
        print("Config loaded")

    def updateconfig(self, key: str, value):
        """
        Update the config

        ### Args
        Key (`str`): This will be used as the key in the JSON dictionary and the argument name when calling the config

        Value: The value to store or change
        """
        if self.__getattribute__(key) == value:
            print("The attribute you're trying to edit already has this value.")
            return
        self.__setattr__(key, value)

        with open(self.file, "r") as confile:
            config = json.load(confile)
        config.update({key: value})
        with open(self.file, "w+") as confile:
            json.dump(config, confile, indent=4)

    async def refreshconfig(self):
        """
        Non-blocking method for automatically refreshing the config in case changes have been made in the file
        """
        with open(self.file, "r") as confile:
            for key, value in json.load(confile).items():
                if self.__getattribute__(key) != value:
                    self.__setattr__(key, value)

    async def backup(self):
        """
        Create a backup of the config file
        """

        # Define variables for backup directory, timestamp and filename
        _directory = os.path.dirname(self.file) + "/backup"
        if not os.path.exists(_directory):
            os.makedirs(_directory)
        _timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        _newfilename = f"{_directory}/cfg_{_timestamp}.json"

        # Write backup file
        with open(self.file, "r") as confile:
            with open(_newfilename, "w+") as backupfile:
                json.dump(json.load(confile), backupfile)

        # Remove backups that are over three days old
        for file in os.listdir(_directory):
            if datetime.now() - datetime.fromtimestamp(
                os.path.getmtime(f"{_directory}/{file}")
            ) > timedelta(days=3):
                os.remove(f"{_directory}/{file}")


# Initialize the config
config = Config("cfg/cfg.json")
