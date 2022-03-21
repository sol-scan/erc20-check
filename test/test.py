import sys
sys.path.append('.')
from core.erc20_check import Erc20Check
from slither import Slither

if __name__ == "__main__":
    
    slither = Slither('test/erc20.sol')
    for c in slither.contracts_derived:
        erc20_check = Erc20Check(c)
        erc20_check.check_close()
        erc20_check.check_standard_func()
        erc20_check.check_extend_func()
        erc20_check.check_overflow()
        # erc20_check.check_mapping_detail()
    sys.exit()