__author__ = 'kalmar'
import os
import json

CONFIG_PATH = os.path.join(os.environ['HOME'], ".htconfig")


class Settings(object):
    terminal_command = '[CMD]'

    def updateFromFile(self):
        attributes = json.loads(open(CONFIG_PATH, "r").read())
        for key in attributes:
            setattr(self, key, attributes[key])

    def saveToFile(self):
        open(CONFIG_PATH, "w").write(json.dumps(self.__dict__))


settings = Settings()