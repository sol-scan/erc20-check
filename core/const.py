from enum import Enum, unique

@unique
class E(Enum):
    def __new__(cls, sign: str, is_required: bool, is_view:bool, value:int):
        obj = object.__new__(cls)
        obj.sign = sign
        obj.is_required = is_required
        obj.is_view = is_view
        obj._value_ = value
        return obj
    totalSupply = "totalSupply()", True, True, 1
    balanceOf = "balanceOf(address)", True, True, 2
    allowance = "allowance(address,address)", True, True, 3
    transfer = "transfer(address,uint256)", True, False, 4
    approve = "approve(address,uint256)", True, False, 5
    transferFrom = "transferFrom(address,address,uint256)", True, False, 6
    burn = "burn(uint256)", False, False, 7
    increaseAllowance = "increaseAllowance(address,uint256)", False, False, 8
    decreaseAllowance = "decreaseAllowance(address,uint256)", False, False, 9


READ_FLAG = False
WRITE_FLAG = True