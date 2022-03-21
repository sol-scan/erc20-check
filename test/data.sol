pragma solidity ^0.8.0;

contract MyContract{
    uint a = 0;
    uint b = 0;

    mapping(address => uint256) balances;
    mapping(address => mapping(address => uint256)) allowance;

    function setA(uint input_a) public{
        a = input_a;
    }

    function setB() public{
        b = a;
    }

    function transfer(address dest, uint256 amount) external returns (bool) {
        return _transfer(msg.sender,dest,amount);
    }
    function _transfer(address src, address dst, uint amount) internal returns (bool) {
        balances[src] -= amount;
        balances[dst] += amount;
        return true;
    }

    function approve(address delegate, uint256 amount) external returns (bool) {
        // if (a > 0) {
        //     allowance[msg.sender][delegate] = amount;
        // } else {
        //     allowance[msg.sender][delegate] = amount;
        // }
        // allowance[msg.sender][delegate] -= amount;
        // amount-=100;
        return _approve(_msgSender(),_msgSender(),amount);
    }
    function _approve(address target, address delegate, uint amount) internal returns (bool) {
        allowance[_msgSender()][_msgSender()] = amount;
        return true;
    }
    function _msgSender() internal view virtual returns (address) {
        return msg.sender;
    }
    function f(uint b) external pure returns (uint) {
        uint a;
        if(a==0){
            a= 1;
        }else{
            a=2;
        }
        assembly {
            a := shr(b, 8)
            a := shr(b, 8)
        }
    }
    function at(address addr) public view returns (bytes memory code) {
        assembly {
            // retrieve the size of the code, this needs assembly
            let size := extcodesize(addr)
            // allocate output byte array - this could also be done without assembly
            // by using code = new bytes(size)
            code := mload(0x40)
            // new "memory end" including padding
            mstore(0x40, add(code, and(add(add(size, 0x20), 0x1f), not(0x1f))))
            // store length in memory
            mstore(code, size)
            // actually retrieve the code, this needs assembly
            extcodecopy(addr, add(code, 0x20), 0, size)
        }
        address aa = addr;
    }
}