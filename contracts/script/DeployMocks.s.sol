// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/WETHm.sol";
import "../src/USDCm.sol";

contract DeployMocks is Script {
    function run() external {
        address deployer = msg.sender;
        //address maker = vm.envAddress("MAKER");
        //address taker = vm.envAddress("TAKER");

        vm.startBroadcast();

        // Pass deployer as initialOwner for both tokens
        WETHm weth = new WETHm(deployer);
        USDCm usdc = new USDCm(deployer);

        console.log("WETHm deployed at:", address(weth));
        console.log("USDCm deployed at:", address(usdc));

        // Mint tokens to test addresses
        //weth.mint(maker, 100 ether);
        //usdc.mint(taker, 200000 ether); // simulate liquidity

        //console.log("Minted 100 WETHm to maker:", maker);
        //console.log("Minted 200k USDCm to taker:", taker);

        vm.stopBroadcast();
    }
}