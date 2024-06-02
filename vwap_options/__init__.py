from toolkit.logger import Logger
from toolkit.fileutils import Fileutils
from toolkit.utilities import Utilities

DATA = "../data/"
logging = Logger(10, DATA + "log.txt")
UTIL = Utilities()
FILS = Fileutils()
F_POS = DATA + "positions.csv"
CNFG = FILS.get_lst_fm_yml("../../vwap-options.yml")["config"]
YAML = FILS.get_lst_fm_yml("../data/settings.yml")
CMMN = YAML["common"]
COND = YAML["conditions"]
SYMBOL = CMMN["base"]
CHECK_SECS = CMMN["check_secs"]
START = CMMN["start"]
STOP = CMMN["stop"]
print(COND)
