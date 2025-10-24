// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./MockERC20.sol";

contract PYUSDm is MockERC20 {
    constructor(address initialOwner)
        MockERC20("Mock PYUSD", "PYUSDm", initialOwner)
    {}
}