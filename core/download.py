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
    dir_path = './sols/'+ '_'.join([contract_name, chain.name.lower(), addr[-8:].lower()])
    if os.path.exists(dir_path):
        if len(os.listdir(dir_path)) > 0:
            return
    else:
        os.makedirs(dir_path)

    ret = requests.get(chain.url,{
        "module":"contract",
        "action":"getsourcecode",
        "address":addr,
        "apiKey":""
    })
    raw_json = ret.json()
    raw_contract_info = raw_json['result'][0]
    raw_source_info:str = raw_contract_info['SourceCode']
    if raw_source_info.startswith('{'):
        if raw_source_info.startswith('{{'):
            raw_source_info = raw_source_info[1:-1]
        mul_source_info = json.loads(raw_source_info)
        if 'sources' in mul_source_info:
            mul_source_info = mul_source_info['sources']
        for file_name, source_info in mul_source_info.items():
            full_file_name = dir_path+'/'+file_name
            temp_dir_path,temp_file_name = os.path.split(full_file_name)
            if not os.path.exists(temp_dir_path):
                os.makedirs(temp_dir_path)
            with open(full_file_name,'w') as fp:
                fp.write(source_info['content'] + "\n\n")
    else:
        with open(dir_path+'/'+raw_contract_info['ContractName']+'.sol','w') as fp:
            fp.write(raw_source_info + "\n\n")
