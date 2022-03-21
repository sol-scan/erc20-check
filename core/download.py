from enum import Enum,unique
import json
import os
import requests

@unique
class Chain(Enum):
    def __new__(cls, url:str, index:int):
        obj = object.__new__(cls)
        obj.url = url
        obj._value_ = index
        return obj
    Eth = "http://api.etherscan.io/api", 0
    Bsc = "http://api.bscscan.com/api", 1

def download_sourceCode(chain:Chain,addr:str,contract_name:str):
    dir_path = './sols/'+contract_name+'_'+addr.lower()[-8:]
    if os.path.exists(dir_path):
        return
    os.makedirs(dir_path)

    ret = requests.get(chain.url,{
        "module":"contract",
        "action":"getsourcecode",
        "address":addr,
        "apiKey":""
    })
    raw_json = ret.json()
    raw_contract_info = raw_json['result'][0]
    if raw_contract_info['SourceCode'].startswith('{'):
        mul_contract_info = json.loads(raw_contract_info['SourceCode'])
        for file_name, contract_info in mul_contract_info.items():
            with open(dir_path+'/'+file_name,'w') as fp:
                fp.write(contract_info['content'] + "\n\n")
    else:
        with open(dir_path+'/'+raw_contract_info['ContractName']+'.sol','w') as fp:
            fp.write(raw_contract_info['SourceCode'] + "\n\n")
