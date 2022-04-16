from configparser import ConfigParser
from enum import Enum, unique
import os

@unique
class Chain(Enum):
    def __new__(cls, url:str, code_url:str, index:int):
        obj = object.__new__(cls)
        if index == 1:
            key_file = './core/key.ini'
            if os.path.exists(key_file):
                key_conf = ConfigParser()
                key_conf.read(key_file,encoding='utf-8')
                url = url + key_conf.get('key','infura_key')
        obj.url = url        
        obj.code_url = code_url
        obj._value_ = index
        return obj
    Eth = "https://mainnet.infura.io/v3/", "http://api.etherscan.io/api", 1
    Bsc = "https://bsc-dataseed.binance.org/", "http://api.bscscan.com/api", 56
    XAVA = "", "http://api.snowtrace.io/api", 43114

@unique
class E(Enum):
    """
    the enum of functinos which is not view
    """
    def __new__(cls, sign: str, is_required: bool, value:int):
        obj = object.__new__(cls)
        obj.sign = sign
        obj.is_required = is_required
        obj._value_ = value
        return obj
    transfer = "transfer(address,uint256)", True, 4
    approve = "approve(address,uint256)", True, 5
    transferFrom = "transferFrom(address,address,uint256)", True, 6
    burn = "burn(uint256)", False, 7
    increaseAllowance = "increaseAllowance(address,uint256)", False, 8
    decreaseAllowance = "decreaseAllowance(address,uint256)", False, 9

@unique
class E_view(Enum):
    """
    the view object may have not function, but have relational public state
    """
    def __new__(cls, sign: str, value:int):
        obj = object.__new__(cls)
        obj.sign = sign
        obj._value_ = value
        return obj
    totalSupply = "totalSupply()", 1
    balanceOf = "balanceOf(address)", 2
    allowance = "allowance(address,address)", 3

READ_FLAG = False
WRITE_FLAG = True