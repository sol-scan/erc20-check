# erc20-check

## 当前已实现：

1. 转账与授权逻辑检查
2. 拓展方法（burn、increaseAllowance、decreaseAllowance）检查
3. 对balances、allowance的写入操作只通过标准方法
4. 溢出检查
5. 外部调用检查
6. 自动下载链上已验证代码到本地
7. 假充值检查

## 正常运行依赖组件
1. python版本>=`3.10.1`
2. solidity静态扫描工具slither， `pip install slither`
3. 与目标sol文件匹配的solidity编译器，可以使用 `solc-select` 进行管理， `pip install solc-select`

## 运行
在项目根目录运行 `python main.py`  
程序运行基于配置文件 `config.ini` ，位于 `main.py` 同级目录，内容如下  
```ini
[download]
chain_id = 56 ; 目前支持ETH、BSC、XAVA，分别为1、56、43314
token_address = 0xb0d502e938ed5f4df2e681fe6e419ff29631d62b
token_name = STG

```

