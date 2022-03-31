from typing import List, Mapping
from slither.core.declarations import Contract, Function, SolidityVariableComposed
from slither.core.variables.state_variable import StateVariable
from slither.core.cfg.node import NodeType,Node
from slither.slithir.operations import InternalCall,Index,SolidityCall,Return
from slither.slithir.variables import TemporaryVariable,Constant

from .const import *

class Erc20CheckBase:
    def __init__(self, c: Contract):
        self.c: Contract = c
        self.func: Mapping[E,Function] = {}
        for e in E._member_map_.values():
            f:Function = self.c.get_function_from_signature(e.sign)
            if e.is_required:
                assert f
            if f:
                self.func[e] = f
                assert self.func[e] in c.functions_entry_points
                if e.is_view:
                    assert self.func[e].view

        assert len(self.func[E.totalSupply].state_variables_read) == 1
        self.totalSupply: StateVariable = self.func[E.totalSupply].state_variables_read[0]

        assert len(self.func[E.balanceOf].state_variables_read) == 1
        self.balance: StateVariable = self.func[E.balanceOf].state_variables_read[0]

        assert len(self.func[E.allowance].state_variables_read) == 1
        self.allowance: StateVariable = self.func[E.allowance].state_variables_read[0]

        # 根据调用情况查询某一可达到的方法列表
        self.func_to_reachable_funcs: Mapping[str, List[Function]] = {}

        self.funcs_write_balance:List[Function] = self.__get_funcs_write_the_state(self.balance)
        self.funcs_write_allowance:List[Function] = self.__get_funcs_write_the_state(self.allowance)


    # 获取哪些可外部访问的方法对指定state进行了写操作
    def __get_funcs_write_the_state(self, s: StateVariable) -> List[Function]:
        fs = []
        for f in self.c.functions_entry_points:
            if not f.is_constructor:
                for ff in self._func_to_reachable_funcs(f):
                    if s in ff.state_variables_written:
                        fs.append(f)
                        break
        return fs
    
    # 迭代获取方法可达到的方法列表
    def _func_to_reachable_funcs(self,f:Function)->List[Function]:
        if  f.full_name not in self.func_to_reachable_funcs:
            res = [f]
            all_internal_calls = f.all_internal_calls()
            all_solidity_calls = f.all_solidity_calls()
            internal_calls = [
                call for call in all_internal_calls if call not in all_solidity_calls]
            modifiers = f.modifiers
            
            for ff in internal_calls + modifiers:
                if ff.contract_declarer.kind == "library":
                    # 在调用父合约的方法时，父合约中本来的LibraryCall调用也出现在了internal_calls
                    continue
                res.extend(self._func_to_reachable_funcs(ff))
            self.func_to_reachable_funcs[f.full_name] = list(set(res))
        return self.func_to_reachable_funcs[f.full_name]

    # 判断某方法是否只读取或写入了指定的state
    def _func_only_op_state(self, f: Function, is_write:bool, obj_indexs: List) -> bool:
        indexs = []
        for ff in self._func_to_reachable_funcs(f):
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

    def _check_mapping_detail(self,f:Function,s:StateVariable,is_write:bool,obj_indexss):
        # obj_indexss中的内容只需要为字符串("msg.sender")或者参数位置
        for i in range(len(obj_indexss)):
            for j in range(len(obj_indexss[i])):
                v = obj_indexss[i][j]
                obj_indexss[i][j] = SolidityVariableComposed(v) if isinstance(v,str) else f.parameters[v]

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
                    indexs = [self.__get_v_maybe_msgSender_func(n,i,ir.variable_right)]
                    # 递推获取索引
                    m_v, next_start_i = ir.lvalue, i+1
                    for _ in range(1,depth):
                        m_k, m_v, next_start_i = self.__get_mapping_index_v(n,next_start_i,m_v)
                        indexs.append(m_k)
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
    # 根据 node、起始i、mapping、获取mapping的索引
    def __get_mapping_index_v(self, n:Node, start_i:int, m_v):
        for i in range(start_i, len(n.irs)):
            ir = n.irs[i]
            if isinstance(ir, Index) and ir.variable_left == m_v:
                return self.__get_v_maybe_msgSender_func(n,i,ir.variable_right),ir.lvalue,i+1
        assert False
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

    def _check_fake_recharge(self, f:Function):
        intercall_irs = []
        for n in f.nodes:
            for ir in n.irs:
                if isinstance(ir, InternalCall):
                    intercall_irs.append(ir)
                if isinstance(ir, Return):
                    ret_value = ir.values[0]
                    if type(ret_value) == Constant:                    
                        if ret_value == False:
                            print("存在假充值风险")
                    else:
                        for intercall_ir in intercall_irs:
                            the_ir:InternalCall = intercall_ir
                            if the_ir.lvalue == ret_value:
                                self._check_fake_recharge(the_ir.function)
