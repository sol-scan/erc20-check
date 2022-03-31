from typing import List, Mapping, Tuple
from slither.core.declarations import Contract, Function, FunctionContract
from slither.core.declarations.solidity_variables import SolidityVariableComposed
from slither.slithir.operations import InternalCall,Index,Binary,BinaryType,HighLevelCall,LowLevelCall
from slither.slithir.variables.variable import Variable

from .erc20_check_base import Erc20CheckBase
from .const import *

class Erc20Check(Erc20CheckBase):
    def __init__(self, c: Contract):
        super().__init__(c)


    def check_close(self):
        allow_funcs = [self.func[e] for e in [E.transfer, E.transferFrom, E.burn] if e in self.func]
        for f in self.funcs_write_balance:
            if f not in allow_funcs:
                print("未知方法 {} 对 {} 进行了写操作".format(f.name, self.balance.name))
        
        allow_funcs = [self.func[e] for e in [E.approve, E.transferFrom, E.increaseAllowance, E.decreaseAllowance] if e in self.func]
        for f in self.funcs_write_allowance:
            if f not in allow_funcs:
                print("未知方法 {} 对 {} 进行了写操作".format(f.name, self.allowance.name))


    def check_standard_func(self):
        self._func_only_op_state(self.func[E.transfer], READ_FLAG, [self.balance])
        self._func_only_op_state(self.func[E.transfer], WRITE_FLAG, [self.balance])
        self._func_only_op_state(self.func[E.approve], READ_FLAG, [])
        self._func_only_op_state(self.func[E.approve], WRITE_FLAG, [self.allowance])
        self._func_only_op_state(self.func[E.transferFrom], READ_FLAG, [self.balance, self.allowance])
        self._func_only_op_state(self.func[E.transferFrom], WRITE_FLAG, [self.balance, self.allowance])

        self._check_mapping_detail(self.func[E.transfer], self.balance, READ_FLAG, [['msg.sender'], [0]])
        self._check_mapping_detail(self.func[E.transfer], self.balance, WRITE_FLAG, [['msg.sender'], [0]])
        self._check_mapping_detail(self.func[E.approve], self.allowance, WRITE_FLAG, [['msg.sender', 0]])
        self._check_mapping_detail(self.func[E.transferFrom], self.balance, READ_FLAG, [[0], [1]])
        self._check_mapping_detail(self.func[E.transferFrom], self.balance, WRITE_FLAG, [[0], [1]])
        self._check_mapping_detail(self.func[E.transferFrom], self.allowance, READ_FLAG, [[0, 'msg.sender']])
        self._check_mapping_detail(self.func[E.transferFrom], self.allowance, WRITE_FLAG, [[0, 'msg.sender']])

        if E.burn in self.func:
            self._func_only_op_state(self.func[E.burn], READ_FLAG, [self.balance, self.totalSupply])
            self._func_only_op_state(self.func[E.burn], WRITE_FLAG, [self.balance, self.totalSupply])
            self._check_mapping_detail(self.func[E.burn], self.balance, READ_FLAG, [['msg.sender']])
            self._check_mapping_detail(self.func[E.burn], self.balance, WRITE_FLAG, [['msg.sender']])

        if E.increaseAllowance in self.func:
            self._func_only_op_state(self.func[E.increaseAllowance], READ_FLAG, [self.allowance])
            self._func_only_op_state(self.func[E.increaseAllowance], WRITE_FLAG, [self.allowance])
            self._check_mapping_detail(self.func[E.increaseAllowance], self.allowance, READ_FLAG, [['msg.sender', 0]])
            self._check_mapping_detail(self.func[E.increaseAllowance], self.allowance, WRITE_FLAG, [['msg.sender', 0]])
            
        if E.decreaseAllowance in self.func:
            self._func_only_op_state(self.func[E.decreaseAllowance], READ_FLAG, [self.allowance])
            self._func_only_op_state(self.func[E.decreaseAllowance], WRITE_FLAG, [self.allowance])
            self._check_mapping_detail(self.func[E.decreaseAllowance], self.allowance, READ_FLAG, [['msg.sender', 0]])
            self._check_mapping_detail(self.func[E.decreaseAllowance], self.allowance, WRITE_FLAG, [['msg.sender', 0]])

    
    # 溢出检查
    # 1、编译器版本高于0.8.0
    # 2、使用库，这样的话，合约中并没有算术运算（只检查标准方法）
    def check_overflow(self):
        if self.c.compilation_unit.solc_version >= "0.8.0":
            return
        
        funcs = []
        # for f in set(self.funcs_write_allowance + self.funcs_write_balance):
        #     funcs.extend(self._func_to_reachable_funcs(f))
        for func in self.func.values():
            funcs.extend(self._func_to_reachable_funcs(func))
        funcs = list(set(funcs))
        for f in funcs:
            for n in f.nodes:
                for ir in n.irs:
                    if isinstance(ir, Binary) and ir.type in[
                        BinaryType.ADDITION,
                        BinaryType.SUBTRACTION,
                        BinaryType.MULTIPLICATION,
                        BinaryType.POWER
                    ]:
                        # if isinstance(ir.variable_left,Variable) and isinstance(ir.variable_right,Variable):
                        print(" {} : {} : {} 存在溢出风险".format(f.contract_declarer.name,f.name,n.expression))
                        break

    # 对可写balance和allowance的入口方法进行外部调用检查
    def check_call_other_contract(self):
        funcs = []
        for f in set(self.funcs_write_allowance + self.funcs_write_balance):
            funcs.extend(self._func_to_reachable_funcs(f))
        funcs:List[Function] = list(set(funcs))
        for f in funcs:
            for node in f.nodes:
                for ir in node.irs:
                    if isinstance(ir, LowLevelCall | HighLevelCall):
                        if ir.function.contract_declarer.kind == "library":
                            # library不算外部调用
                            continue
                        print(" {} 方法中的 {} 存在外部调用风险".format(f.name,node.expression))

    # 若程序中带有sload和sstore的汇编指令，则其行为具有很大的不确定性
    def check_sstore(self):
        funcs = []
        for f in self.c.functions_entry_points:
            funcs.extend(self._func_to_reachable_funcs(f))
        funcs = list(set(funcs))
        for f in funcs:
            self._func_has_asm_sstore(f)
            self._func_has_asm_sload(f)

    # 假充值
    def check_fake_recharge(self):
        self._check_fake_recharge(self.func[E.transfer])


