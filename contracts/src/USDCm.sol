// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./MockERC20.sol";

contract USDCm is MockERC20 {
    constructor(address initialOwner)
        MockERC20("Mock USDC", "USDCm", initialOwner)
    {}
}