// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./MockERC20.sol";

contract IDPm is MockERC20 {
    constructor(address initialOwner)
        MockERC20("iDarkPool Mock Token", "IDPm", initialOwner)
    {}
}