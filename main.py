from configparser import ConfigParser
import os
from slither import Slither
import sys
sys.path.append('.')
from core.const import Chain
from core.download import  download_sourceCode
from core.erc20_check import Erc20Check

if __name__ == "__main__":
    config = ConfigParser()
    config.read('./config.ini','utf-8')
    chain_id = config.getint('download','chain_id')
    for e in Chain._member_map_.values():
        if chain_id == e.value:
            chain = e
            break
    assert 'chain' in locals(), "暂不支持该链：" + str(chain_id)
    
    token_address = config.get('download','token_address')
    token_name = config.get('download','token_name')
    contract_dir, check_conf = download_sourceCode(chain, token_address, token_name)
    os.chdir(contract_dir)

    contract_path = check_conf.get('info','contract_path')
    slither = Slither(contract_path)
    for c in slither.contracts_derived:
        if c.kind!="contract":
            continue
        erc20_check = Erc20Check(c)
        erc20_check.check_close()
        erc20_check.check_standard_func()
        erc20_check.check_overflow()
        erc20_check.check_sstore()
        erc20_check.check_fake_recharge()
        erc20_check.check_call_other_contract()
    sys.exit()
