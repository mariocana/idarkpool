// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/WETHm.sol";
import "../src/USDCm.sol";
import "../src/DarkPoolSettlement.sol";

contract DeployAll is Script {
    function run() external {
        vm.startBroadcast();

        address deployer = msg.sender;
        console2.log("Deployer:", deployer);

        // Deploy mock tokens
        WETHm weth = new WETHm(deployer);
        USDCm usdc = new USDCm(deployer);
        console2.log("WETHm:", address(weth));
        console2.log("USDCm:", address(usdc));

        // Use deployer as enclaveSigner for local test
        DarkPoolSettlement settlement = new DarkPoolSettlement(deployer);
        console2.log("DarkPoolSettlement:", address(settlement));

        vm.stopBroadcast();
    }
}