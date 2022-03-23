from typing import List, Mapping, Tuple
from slither.core.declarations import Contract, Function
from slither.core.declarations.solidity_variables import SolidityVariableComposed
from slither.slithir.operations import InternalCall,Index,Binary,BinaryType,HighLevelCall,LowLevelCall
from slither.slithir.variables.variable import Variable

from .erc20_check_base import Erc20CheckBase
from .const import *

class Erc20Check(Erc20CheckBase):
    def __init__(self, c: Contract):
        super().__init__(c)


    def check_close(self):
        self._check_close(
            BALANCE_OF,
            [TRANSFER, TRANSFER_FROM],
            [BURN]
        )
        self._check_close(
            ALLOWANCE,
            [APPROVE, TRANSFER_FROM],
            [INCREASE_ALLOWANCE, DECREASE_ALLOWANCE]
        )
    
    def check_standard_func(self):
        lst = [
            [TRANSFER, READ_FLAG, [BALANCE_OF]],
            [TRANSFER, WRITE_FLAG, [BALANCE_OF]],
            [APPROVE, READ_FLAG, []],
            [APPROVE, WRITE_FLAG, [ALLOWANCE]],
            [TRANSFER_FROM, READ_FLAG, [BALANCE_OF, ALLOWANCE]],
            [TRANSFER_FROM, WRITE_FLAG, [BALANCE_OF, ALLOWANCE]]            
        ]
        lst2 = [
            [TRANSFER, BALANCE_OF, READ_FLAG, [['msg.sender'], [0]]],
            [TRANSFER, BALANCE_OF, WRITE_FLAG, [['msg.sender'], [0]]],
            [APPROVE, ALLOWANCE, WRITE_FLAG, [['msg.sender', 0]]],
            [TRANSFER_FROM, BALANCE_OF, READ_FLAG, [[0], [1]]],
            [TRANSFER_FROM, BALANCE_OF, WRITE_FLAG, [[0], [1]]],
            [TRANSFER_FROM, ALLOWANCE, READ_FLAG, [[0, 'msg.sender']]],
            [TRANSFER_FROM, ALLOWANCE, WRITE_FLAG, [[0, 'msg.sender']]],
        ]

        if BURN in [f.name for f in self.funcs_write_state[BALANCE_OF]]:
            func_burn = self.c.get_function_from_signature("burn(uint256)")
            assert func_burn
            self.funcs[BURN] = func_burn
            lst.extend([
                [BURN, READ_FLAG, [BALANCE_OF, TOTAL_SUPPLY]],
                [BURN, WRITE_FLAG, [BALANCE_OF, TOTAL_SUPPLY]]
            ])
            lst2.extend([
                [BURN, BALANCE_OF,READ_FLAG,[['msg.sender']]],
                [BURN, BALANCE_OF,WRITE_FLAG,[['msg.sender']]]
            ])
            
        if INCREASE_ALLOWANCE in [f.name for f in self.funcs_write_state[ALLOWANCE]]:
            func_incr_allowance = self.c.get_function_from_signature("increaseAllowance(address,uint256)")
            assert func_incr_allowance
            self.funcs[INCREASE_ALLOWANCE] = func_incr_allowance
            lst.extend([
                [INCREASE_ALLOWANCE, READ_FLAG, [ALLOWANCE]],
                [INCREASE_ALLOWANCE, WRITE_FLAG, [ALLOWANCE]]
            ])
            lst2.extend([
                [INCREASE_ALLOWANCE, ALLOWANCE, READ_FLAG, [['msg.sender', 0]]],
                [INCREASE_ALLOWANCE, ALLOWANCE, WRITE_FLAG, [['msg.sender', 0]]]
            ])
        
        if DECREASE_ALLOWANCE in [f.name for f in self.funcs_write_state[ALLOWANCE]]:
            func_decr_allowance = self.c.get_function_from_signature("decreaseAllowance(address,uint256)")
            assert func_decr_allowance
            self.funcs[DECREASE_ALLOWANCE] = func_decr_allowance
            lst.extend([
                [DECREASE_ALLOWANCE, READ_FLAG, [ALLOWANCE]],
                [DECREASE_ALLOWANCE, WRITE_FLAG, [ALLOWANCE]]
            ])
            lst2.extend([
                [DECREASE_ALLOWANCE, ALLOWANCE, READ_FLAG, [['msg.sender', 0]]],
                [DECREASE_ALLOWANCE, ALLOWANCE, WRITE_FLAG, [['msg.sender', 0]]]
            ])

        for l in lst:
            self._func_only_op_state(
                self.funcs[l[0]],
                l[1],
                [self.states[item] for item in l[2]]
            )

        for l in lst2:
            check_domain = []
            for item in l[3]:
                check_domain.append(
                    [SolidityVariableComposed(v) if isinstance(v,str) else self.funcs[l[0]].parameters[v] for v in item]
                )
            self._check_mapping_detail(
                self.funcs[l[0]],
                self.states[l[1]],
                l[2],
                check_domain
            )


    
    def test_check_mapping_detail(self):
        self._check_mapping_detail(
            self.funcs[ALLOWANCE],
            self.states[ALLOWANCE],
            False,
            [
                [self.funcs[ALLOWANCE].parameters[0],self.funcs[ALLOWANCE].parameters[1]]
            ]
        )

    # 溢出检查
    # 1、编译器版本高于0.8.0
    # 2、使用库，这样的话，合约中并没有算术运算
    def check_overflow(self):
        if self.c.compilation_unit.solc_version >= "0.8.0":
            return
        
        funcs = []
        for f in set(self.funcs_write_state[BALANCE_OF] + self.funcs_write_state[ALLOWANCE]):
            funcs.extend(self._func_to_reachable_funcs(f))
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
                        if isinstance(ir.variable_left,Variable) and isinstance(ir.variable_right,Variable):
                            print(" {} : {} 存在溢出风险".format(f.name,n.expression))
                            break

    # 对可写balance和allowance的入口方法进行外部调用检查
    def check_call_other_contract(self):
        funcs = []
        for f in set(self.funcs_write_state[BALANCE_OF] + self.funcs_write_state[ALLOWANCE]):
            funcs.extend(self._func_to_reachable_funcs(f))
        funcs:List[Function] = list(set(funcs))
        for f in funcs:
            for node in f.nodes:
                for ir in node.irs:
                    if isinstance(ir, LowLevelCall | HighLevelCall):
                        print(" {} 方法中的 {} 存在外部调用风险".format(f.name,node.expression))

    def check_sstore(self):
        funcs = []
        for f in self.c.functions_entry_points:
            funcs.extend(self._func_to_reachable_funcs(f))
        funcs = list(set(funcs))
        for f in funcs:
            self._func_has_asm_sstore(f)
            self._func_has_asm_sload(f)


