from typing import List, Mapping, Tuple
from slither.core.declarations import Contract, Function
from slither.core.declarations.solidity_variables import SolidityVariableComposed
from slither.slithir.operations import InternalCall,Index,Binary,BinaryType,SolidityCall

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
        self._func_only_op_state(
            self.funcs[TRANSFER],
            READ_FLAG,
            [
                self.states[BALANCE_OF]
            ]
        )
        self._func_only_op_state(
            self.funcs[APPROVE],
            READ_FLAG,
            []
        )
        self._func_only_op_state(
            self.funcs[TRANSFER_FROM],
            READ_FLAG,
            [
                self.states[BALANCE_OF],
                self.states[ALLOWANCE]
            ]
        )

        self._check_mapping_detail(
            self.funcs[TRANSFER],
            self.states[BALANCE_OF],
            False,
            [
                [SolidityVariableComposed("msg.sender")],
                [self.funcs[TRANSFER].parameters[1]]
            ]
        )
        self._check_mapping_detail(
            self.funcs[TRANSFER],
            self.states[BALANCE_OF],
            True,
            [
                [SolidityVariableComposed("msg.sender")],
                [self.funcs[TRANSFER].parameters[1]]
            ]
        )

    def check_extend_func(self):
        if BURN in [f.name for f in self.funcs_write_state[BALANCE_OF]]:
            func_burn = self.c.get_function_from_signature("burn(uint256)")
            assert func_burn
            self._func_only_op_state(
                func_burn,
                READ_FLAG,
                [
                    self.states[BALANCE_OF],
                    self.states[TOTAL_SUPPLY]
                ]
            )

        if INCREASE_ALLOWANCE in [f.name for f in self.funcs_write_state[ALLOWANCE]]:
            func_incr_allowance = self.c.get_function_from_signature("increaseAllowance(address,uint256)")
            assert func_incr_allowance
            self._func_only_op_state(
                func_incr_allowance,
                READ_FLAG,
                [
                    self.states[ALLOWANCE]
                ]
            )
                
        if DECREASE_ALLOWANCE in [f.name for f in self.funcs_write_state[ALLOWANCE]]:
            func_decr_allowance = self.c.get_function_from_signature("decreaseAllowance(address,uint256)")
            assert func_decr_allowance
            self._func_only_op_state(
                func_decr_allowance,
                READ_FLAG,
                [
                    self.states[ALLOWANCE]
                ]
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
                        print(" {} : {} 存在溢出风险".format(f.name,n.expression))
                        break
    def check_sstore(self):
        funcs = []
        for f in self.c.functions_entry_points:
            funcs.extend(self._func_to_reachable_funcs(f))
        funcs = list(set(funcs))
        for f in funcs:
            self._func_has_asm_sstore(f)
            self._func_has_asm_sload(f)


