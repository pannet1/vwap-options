from toolkit.logger import Logger
from toolkit.fileutils import Fileutils

DATA = "../data/"
logging = Logger(10, DATA + "file.log")
FILS = Fileutils()
YAML = FILS.get_lst_fm_yml("../../vwap-options.yml")
CNFG = YAML["config"]
CMMN = YAML["common"]
SYMBOL = YAML["common"]["base"]
