// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/IDPm.sol";
import "../src/PYUSDm.sol";
import "../src/DarkPoolSettlement.sol";

contract DeployAll is Script {
    function run() external {
        vm.startBroadcast();

        address deployer = msg.sender;
        console.log("Deployer:", deployer);

        // Deploy mock tokens
        IDPm idkm = new IDPm(deployer);
        PYUSDm pyusdm = new PYUSDm(deployer);
        console.log("IDPm:", address(idkm));
        console.log("PYUSDm:", address(pyusdm));

        // Use deployer as enclaveSigner for local test
        DarkPoolSettlement settlement = new DarkPoolSettlement(deployer);
        console.log("DarkPoolSettlement:", address(settlement));

        vm.stopBroadcast();
    }
}