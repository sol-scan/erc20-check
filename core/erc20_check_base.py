from typing import List, Mapping, Tuple
from slither.core.declarations import Contract, Function, SolidityVariableComposed
from slither.core.variables.state_variable import StateVariable
from slither.core.variables.local_variable import LocalVariable
from slither.core.cfg.node import NodeType,Node
from slither.slithir.operations import InternalCall,Index,Binary,BinaryType,SolidityCall
from slither.slithir.variables import TemporaryVariable

from .const import *

class Erc20CheckBase:
    def __init__(self, c: Contract):
        self.c: Contract = c
        self.funcs: Mapping[str, Function] = {}
        self.states: Mapping[str, StateVariable] = {}
        self.funcs_write_state: Mapping[str, List[Function]] = {}
        # 根据调用情况查询某一可达到的方法列表
        self.funcs_to_reachable_funcs: Mapping[str, List[Function]] = {}
        # self.func_to_reachable_paths: Mapping[str,Mapping[str,List[Function]]] = {}

        self.funcs[TOTAL_SUPPLY] = c.get_function_from_signature(
            'totalSupply()')
        self.funcs[BALANCE_OF] = c.get_function_from_signature(
            'balanceOf(address)')
        self.funcs[ALLOWANCE] = c.get_function_from_signature(
            'allowance(address,address)')
        self.funcs[TRANSFER] = c.get_function_from_signature(
            'transfer(address,uint256)')
        self.funcs[APPROVE] = c.get_function_from_signature(
            'approve(address,uint256)')
        self.funcs[TRANSFER_FROM] = c.get_function_from_signature(
            'transferFrom(address,address,uint256)')
        for k in [TOTAL_SUPPLY, BALANCE_OF, ALLOWANCE, TRANSFER, APPROVE, TRANSFER_FROM]:
            assert self.funcs[k] and self.funcs[k] in c.functions_entry_points

        for k in [TOTAL_SUPPLY, BALANCE_OF, ALLOWANCE]:
            assert len(self.funcs[k].state_variables_read) == 1 and self.funcs[k].view
            self.states[k] = self.funcs[k].state_variables_read[0]

        self.funcs_write_state[BALANCE_OF] = self.__get_funcs_write_the_state(
            self.states[BALANCE_OF])
        self.funcs_write_state[ALLOWANCE] = self.__get_funcs_write_the_state(
            self.states[ALLOWANCE])

    # 迭代获取方法可达到的方法列表
    def __func_to_reachable_funcs(self,f:Function)->List[Function]:
        if  f.full_name not in self.funcs_to_reachable_funcs:
            res = [f]
            all_internal_calls = f.all_internal_calls()
            all_solidity_calls = f.all_solidity_calls()
            internal_calls = [
                call for call in all_internal_calls if call not in all_solidity_calls]
            modifies = f.modifiers
            for ff in internal_calls + modifies:
                res.extend(self.__func_to_reachable_funcs(ff))
            self.funcs_to_reachable_funcs[f.full_name] = list(set(res))
        return self.funcs_to_reachable_funcs[f.full_name]

    # 获取哪些可外部访问的方法对指定state进行了写操作
    def __get_funcs_write_the_state(self, s: StateVariable) -> List[Function]:
        fs = []
        for f in self.c.functions_entry_points:
            if not f.is_constructor:
                for ff in self.__func_to_reachable_funcs(f):
                    if s in ff.state_variables_written:
                        fs.append(f)
                        break
        return fs

    # 判断某方法是否只读取了指定的state
    def _func_only_op_state(self, f: Function, is_write:bool, obj_indexs: List) -> bool:
        indexs = []
        for ff in self.__func_to_reachable_funcs(f):
            indexs.extend(ff.state_variables_written if is_write else ff.state_variables_read)
        indexs = list(set(indexs))

        for index in indexs:
            if index not in obj_indexs:
                print(" {} 对 {} 有意料之外的{}".format(
                    f.name,
                    index.name,
                    "写入" if is_write else "读取"
                ))
        for index in obj_indexs:
            if index not in indexs:
                print(" {} 对 {} 没有应该有的{}".format(
                    f.name,
                    index.name,
                    "写入" if is_write else "读取"
                ))

    def _func_has_asm_sload(self,f:Function) -> bool:
        for node in f.nodes:
            for ir in node.irs:
                if isinstance(ir, SolidityCall) and ir.function.name == "sload":
                    print(" {} 使用了 asm 的 sload ，功能未知".format(f.name,))
                    return True
        return False
    def _func_has_asm_sstore(self,f:Function) -> bool:
        for node in f.nodes:
            for ir in node.irs:
                if isinstance(ir, SolidityCall) and ir.function.name == "sstore":
                    print(" {} 使用了 asm 的 sstore ，功能未知".format(f.name,))
                    return True
        return False

    # 对写指定state的方法进行分类
    def _check_close(self, key: str, standard_fnames, extend_fnames) -> Tuple[List[str], List[str]]:
        extends = []
        others = []
        for f in self.funcs_write_state[key]:
            if f.name in standard_fnames:
                pass
            elif f.name in extend_fnames:
                extends.append(f.name)
            else:
                others.append(f.name)
        # if len(extends) > 0:
        #     print("拓展方法 {} 对 {} 进行了写操作".format(
        #         ",".join(extends), self.states[key].name))
        if len(others) > 0:
            print("未知方法 {} 对 {} 进行了写操作".format(
                ",".join(others), self.states[key].name))
        return extends, others

    def _check_mapping_detail(self,f:Function,s:StateVariable,is_write:bool,obj_indexss):
        depth = str(s.type).count("mapping")
        indexss = self.__get_mapping_indexs_op_by_func(f,s,is_write,depth)
        for indexs in indexss:
            if not self.__list_in_lists(indexs,obj_indexss):
                print(" {} 对 {} 有意料之外的{}：->{}".format(
                    f.name,
                    s.name,
                    "写入" if is_write else "读取",
                    '->'.join([index.name for index in indexs])
                ))
        for indexs in obj_indexss:
            if not self.__list_in_lists(indexs,indexss):
                print(" {} 对 {} 没有应该有的{}：->{}".format(
                    f.name,
                    s.name,
                    "写入" if is_write else "读取",
                    '->'.join([index.name for index in indexs])
                ))
    def __list_in_lists(self,l,ls)->bool:
        for l_ in ls:
            if len(l) == len(l_):
                match = True
                for i in range(len(l)):
                    if l[i] != l_[i]:
                        match = False
                        break
                if match:
                    return True
        return False
    
        
    # 获取方法对mapping变量读写的细节
    def __get_mapping_indexs_op_by_func(self,f:Function,s:StateVariable,is_write:bool,depth:int)->List[List]:
        # depth = str(s.type).count("mapping")
        indexss = []
        for n in f.nodes:
            for i in range(len(n.irs)):
                ir = n.irs[i]
                if isinstance(ir, Index) and ir.variable_left == s:
                    indexs = []
                    # 假设第一个索引可能为调用，后面都不是
                    indexs.append(self.__get_v_maybe_msgSender_func(n,i,ir.variable_right))
                    for j in range(1,depth):
                        indexs.append(n.irs[i+j].variable_right)
                    indexss.append(indexs)
                if isinstance(ir,InternalCall) :
                    ic_rets = self.__get_mapping_indexs_op_by_func(ir.function,s,is_write,depth)
                    # 替换调用中的参数依赖
                    for m in range(len(ic_rets)):
                        for mm in range(depth):
                            for l in range(len(ir.arguments)):
                                if ic_rets[m][mm] == ir.function.parameters[l]:
                                    ic_rets[m][mm] = self.__get_v_maybe_msgSender_func(n,i,ir.arguments[l]) 
                    indexss.extend(ic_rets)
        return indexss
    
    def __get_v_maybe_msgSender_func(self,n:Node,i:int,v):
        # _msgSender() 的问题，简化处理，直接返回msg.sender
        if isinstance(v, TemporaryVariable):
            # 逆向寻找临时变量的值
            for j in range(i-1,-1,-1):
                ir_before = n.irs[j]
                if v == ir_before.lvalue \
                        and isinstance(ir_before,InternalCall) and self.__is_return_msg_sender(ir_before.function):
                    return SolidityVariableComposed("msg.sender")
        return v
    def __is_return_msg_sender(self,f:Function)->bool:
        return_nodes = []
        for n in f.nodes:
            if n.type == NodeType.RETURN:
                return_nodes.append(n)
        return len(return_nodes) == 1 and str(return_nodes[0].expression)=="msg.sender"
