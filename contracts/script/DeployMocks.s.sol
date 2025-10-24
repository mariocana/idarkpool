// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/IDPm.sol";
import "../src/PYUSDm.sol";

contract DeployMocks is Script {
    function run() external {
        address deployer = msg.sender;
        vm.startBroadcast();

        // Pass deployer as initialOwner for both tokens
        IDPm idkm = new IDPm(deployer);
        PYUSDm pyusdm = new PYUSDm(deployer);

        console.log("IDPm deployed at:", address(idkm));
        console.log("PYUSDm deployed at:", address(pyusdm));

        vm.stopBroadcast();
    }
}