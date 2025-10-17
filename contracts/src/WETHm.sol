// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./MockERC20.sol";

contract WETHm is MockERC20 {
    constructor(address initialOwner)
        MockERC20("Mock WETH", "WETHm", initialOwner)
    {}
}