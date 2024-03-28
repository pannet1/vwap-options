from toolkit.logger import Logger
from toolkit.fileutils import Fileutils
from toolkit.utilities import Utilities

DATA = "../data/"
logging = Logger(10)
UTIL = Utilities()
FILS = Fileutils()
F_POS = DATA + "position.csv"
YAML = FILS.get_lst_fm_yml("../../vwap-options.yml")
CNFG = YAML["config"]
CMMN = YAML["common"]
SYMBOL = YAML["common"]["base"]
